import json
import math
from abc import abstractmethod, ABC
from itertools import chain

import requests
import yaml

from misc import settings
from misc.utils import Paper
from .base import APIProceedingParser


class IEEEParser(APIProceedingParser):
    """Parser for IEEE based publications."""

    def __init__(self, *args, **kwargs):
        self.api_url = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
        self.api_key = self.load_api_key()
        self.max_records = 200  # Fixed Number of the API, increasing it does not work
        super().__init__(*args, **kwargs)

    @property
    @abstractmethod
    def publication_title(self):
        """Returns: Name of the publication."""
        raise NotImplementedError

    def load_api_key(self) -> str:
        """Load the API key from the credentials file and check its validity.

        Returns:
            API key

        """
        with open(settings.credentials_file, "r") as f:
            content = yaml.safe_load(f)
        api_key = content.get("ieee_api_key")
        if api_key is None:
            raise ValueError("No API key provided.")

        if self.validate_api_key(api_key):
            return api_key
        else:
            raise ValueError("Invalid API key.")

    def validate_api_key(self, api_key: str) -> bool:
        """Validate the provided API key with a dummy request.

        Args:
            api_key: API key to test.

        Returns:
            Boolean whether the provided API key is valid or not.

        """
        params = {"apikey": api_key}
        request = requests.get(
            self.api_url,
            params=params,
            proxies=settings.proxies,
            verify=settings.verify_ssl,
        )

        if "Developer Over Rate" in request.text:
            raise ValueError(
                "You have exceeded the maximum number of API calls for today. The free limit is 200 calls."
            )

        if request.status_code == 200:
            return True
        else:
            return False

    def get_number_of_records(self) -> int:
        """Get the number of records for the respective proceeding via a request.

        Returns:
            Number of records.
        """
        params = {
            "publication_title": self.publication_title,
            "publication_year": self.year,
            "max_records": 1,
            "apikey": self.api_key,
        }
        content = requests.get(
            self.api_url,
            params=params,
            proxies=settings.proxies,
            verify=settings.verify_ssl,
        ).content.decode("utf-8")
        json_content = json.loads(content)
        n_records = json_content["total_records"]
        return int(n_records)

    def build_request_params(self) -> list[dict]:
        """IEEE does not allow to request all papers at once, instead paging through the number of records is required.
        The requests are split across the maximal number of papers per request to minimize the runtime/overhead and API
        calls. Therefore, the information w.r.t. the limited API calls is maximized.

        Returns:
            List containing the request parameters.

        """
        n_records = self.get_number_of_records()

        if n_records == 0:
            raise ValueError(
                f"No records found, please check if {self.proceeding_name} is already available for {self.year}."
            )

        n_requests = math.ceil(n_records / self.max_records)
        params_list = [
            {
                "publication_title": self.publication_title,
                "publication_year": self.year,
                "max_records": self.max_records,
                "start_record": n * self.max_records,
                "apikey": self.api_key,
            }
            for n in range(n_requests)
        ]
        return params_list

    def _request_contents(self) -> list[str]:
        """Build paper request information and subsequently request all paper contents.

        Returns:
            List of contents.

        """
        params_list = self.build_request_params()
        urls = [self.api_url] * len(params_list)
        return self._get_async_request_contents(urls, params_list=params_list)

    @staticmethod
    def _process_contents(request_contents: list[str]) -> list[dict]:
        """Postprocess the raw contents by extracting the required information.

        Args:
            request_contents: List of raw paper contents from requests.

        Returns:
            List of processed contents.

        """
        request_contents = [
            json.loads(request_content)["articles"]
            for request_content in request_contents
        ]
        request_contents = list(chain.from_iterable(request_contents))
        return request_contents

    def _parse_paper_content(
        self, paper_content: dict, paper_url: str | None = None
    ) -> Paper:
        """Parse paper content from content dictionary.

        Args:
            paper_content: Paper content to parse.
            paper_url: Url of the paper content to support parsing. Just used for debugging.

        Returns:
            Parsed content as a Paper item.

        """
        title = paper_content["title"]
        authors = [
            author_content["full_name"]
            for author_content in paper_content["authors"]["authors"]
        ]
        url = paper_content["pdf_url"]
        abstract = paper_content.get(
            "abstract", ""
        )  # old publications sometimes do not have an abstract

        return Paper(title, authors, abstract, url)


class JournalIEEEParser(IEEEParser, ABC):
    """Parser for IEEE based journals, to allow issue specific parsing."""

    def __init__(self, issue: int | None = None, *args, **kwargs):
        self.issue = issue
        super().__init__(*args, **kwargs)

    @property
    def default_output_file(self) -> str:
        """Returns: Default name from super or add the issue information, if a specific issue was selected."""
        if self.issue:
            return f"{self.proceeding_name}_{self.year}_{self.issue}"
        else:
            return super().default_output_file

    def _filter_contents(self, request_contents: list[dict]) -> list[dict]:
        """Filter contents w.r.t. the desired issue.

        Args:
            request_contents: List of paper contents to filter.

        Returns:
            List of filtered contents.

        """
        request_contents = self._filter_issues(request_contents)
        return request_contents

    def _filter_issues(self, request_contents: list[dict]) -> list[dict]:
        """Filter contents by a specific issue if an issue was provided during initialization.

        Args:
            request_contents: List of paper contents to filter.

        Returns:
            List of filtered contents.

        """
        if self.issue:
            request_contents = [
                request_content
                for request_content in request_contents
                if request_content["issue"] == str(self.issue)
            ]
        return request_contents


class TPAMIParser(JournalIEEEParser):
    """Parser for the Transactions on Pattern Analysis and Machine Intelligence (TPAMI) journal."""

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "TPAMI"

    @property
    def publication_title(self) -> str:
        """Returns: Name of the publication."""
        return "IEEE Transactions on Pattern Analysis and Machine Intelligence"

    def _validate_year(self) -> None:
        """Check default year conditions from super and ensure the year is not before the first journal was released in
        1979.
        """
        super()._validate_year()
        if self.year < 1979:
            raise ValueError("The first TPAMI journal was released in 1979.")


class IROSParser(IEEEParser):
    """Parser of the International Conference on Intelligent Robots and Systems (IROS)."""

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "IROS"

    @property
    def publication_title(self) -> str:
        """Returns: Name of the publication, which did slightly change throughout the years."""
        if self.year < 1992:  # old name was slightly different
            return "International Workshop on Intelligent Robots"
        elif self.year == 1997:  # there was a typo in 1997
            return "IEEE/RSJ International Conference on Intelligent Robot and Systems"
        else:
            return "IEEE/RSJ International Conference on Intelligent Robots and Systems"

    def _validate_year(self) -> None:
        """Check default year conditions from super and ensure the year is not before the first conference was held in
        1988.
        """
        super()._validate_year()
        if self.year < 1988:
            raise ValueError("The first IROS took place in 1988.")


class ICRAParser(IEEEParser):
    """Parser of the International Conference on Robotics & Automation (ICRA)."""

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "ICRA"

    @property
    def publication_title(self) -> str:
        """Returns: Name of the publication."""
        return "IEEE International Conference on Robotics and Automation"

    def _validate_year(self) -> None:
        """Check default year conditions from super and ensure the year is not before the first conference was held in
        1984.
        """
        super()._validate_year()
        if self.year < 1984:
            raise ValueError("The first ICRA took place in 1984.")
