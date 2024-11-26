import json
import math
import re
from itertools import batched

import bs4
import requests

from misc import settings
from misc.utils import Paper
from .base import KeyedContentHandler


class IEEEContentHandler(KeyedContentHandler):
    """ContentHandler to access IEEE data. It does work with and without an API key, though the API version is recommended for stability reasons. The API limit is extremely high, hence, it should not be a limitation."""

    def __init__(self, force_content: bool = False):
        """Args:
        force_content: Whether to force content to be retrieved or not. Failed content is returned as None. By default, errors are raised.
        """
        self.force_content = force_content
        self.api_url = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
        self.api_max_records = (
            200  # Fixed Number of the API, increasing it does not work
        )

        self.api_key = self._load_api_key("ieee_api_key")
        if self.api_key:
            self.use_api = True
        else:
            self.use_api = False

        self.web_url = "https://ieeexplore.ieee.org/document"

    def _validate_api_key(self, api_key: str) -> bool:
        """Validate if the API key is valid by making a request to the main API page.

        Args:
            api_key: API key to validate.

        Returns:
            Boolean value indicating if the API key is valid.

        """
        params = {"apikey": api_key}
        request = requests.get(
            self.api_url,
            params=params,
            proxies=settings.proxies,
            verify=settings.verify_ssl,
        )

        if request.status_code == 200:
            return True
        elif request.status_code == 403:
            raise ValueError("The IEEE API key is invalid.")
        else:
            return False

    def _get_request_urls(self, paper_list: list[Paper]) -> list[str]:
        """Build request urls depending on if the API or direct page requests are used.

        Args:
            paper_list: List of papers

        Returns:
            URLs required for the requests

        """
        if self.use_api:
            return self._get_api_request_urls(paper_list)
        else:
            return self._get_webscrape_request_urls(paper_list)

    def _get_request_identifiers(
        self, paper_list: list[Paper]
    ) -> list[list[str]]:
        """Build request identifiers to be able to subsequently assign the individual papers of combined requests.
        If the API is used, article numbers are used to select the relevant papers. Otherwise, the super method is used, returning just Nones.

        Args:
            paper_list: List of papers

        Returns:
            Nested list of request identifiers.

        """
        if self.use_api:
            return self._get_article_numbers_list(paper_list)
        else:
            return super()._get_request_identifiers(paper_list)

    def _get_article_numbers_list(
        self, paper_list: list[Paper]
    ) -> list[list[str]]:
        """Retrieve article numbers from papers and group them w.r.t. the maximal request size.

        Args:
            paper_list: List of papers

        Returns:
            Nested list of article numbers, where each sublist groups articles based on the maximal records per request.

        """
        article_numbers = [
            self._get_article_number_from_url(paper.url)
            for paper in paper_list
        ]
        return list(
            map(
                lambda x: list(x),
                batched(article_numbers, self.api_max_records),
            )
        )

    @staticmethod
    def _get_article_number_from_url(url: str) -> str:
        """Extract the article number from the url via regex.

        Args:
            url: Paper url

        Returns:
            Article number

        """
        # regex pattern to capture the last number combination in the url using negative lookahead
        pattern = r"(\d+)(?!.*\d)"
        return re.search(pattern, url).group()

    def _get_api_request_urls(self, paper_list: list[Paper]) -> list[str]:
        """Build request urls for the API, where multiple papers are grouped to reduce the number of requests. Required parameters are also incorporated.

        Args:
            paper_list: List of papers

        Returns:
            URLs required for the requests

        """
        article_numbers_list = self._get_article_numbers_list(paper_list)

        params_list = [
            {
                "apikey": self.api_key,
                "article_number": " OR ".join(article_numbers),
                "max_records": self.api_max_records,
            }
            for article_numbers in article_numbers_list
        ]

        request_urls = [
            requests.Request("GET", self.api_url, params=params).prepare().url
            for params in params_list
        ]
        return request_urls

    def _get_webscrape_request_urls(
        self, paper_list: list[Paper]
    ) -> list[str]:
        """Build request urls for webscraping. Each url requests solely a single paper.

        Args:
            paper_list: List of papers

        Returns:
            URLs required for the requests

        """
        request_urls = []
        for paper in paper_list:
            paper_url = paper.url
            article_number = self._get_article_number_from_url(paper_url)
            request_urls.append(f"{self.web_url}/{article_number}")

        return request_urls

    def _get_request_headers(self, paper_list: list[Paper]) -> list[None]:
        """Build request headers to retrieve the publisher related paper information. For the API no header is required but the shape depends on the request size. Without the API, User-Agents are required.

        Args:
            paper_list: List of papers

        Returns:
            List of headers

        """
        if self.use_api:
            return math.ceil(len(paper_list) / self.api_max_records) * [None]
        else:
            return len(paper_list) * [settings.headers]

    def get_paper_contents_from_request_content(
        self, content: str, content_ids: list[str] | None = None
    ) -> list[dict]:
        """Retrieve general paper contents, where the API uses json format and webscraping bs4. Afterward, get the individual paper information via extra processing as well.

        Args:
            content: Retrieved content to get the paper data from.
            content_ids: List of content IDs for processing the content. Only required for API based requests.

        Returns:
            List containing paper data as dictionaries.

        """
        if self.use_api:
            json_content = json.loads(content)
            article_contents = json_content["articles"]
            article_contents = sorted(
                article_contents,
                key=lambda x: content_ids.index(x["article_number"]),
            )
            paper_data_list = [
                self._get_paper_data_from_api_content_item(content_item)
                for content_item in article_contents
            ]
        else:
            content = bs4.BeautifulSoup(content, features="xml")
            paper_data_list = [
                self._get_paper_data_from_web_content_item(content)
            ]

        return paper_data_list

    @staticmethod
    def _get_paper_data_from_api_content_item(content_item: dict) -> dict:
        """Retrieve single paper data from content selecting the json attributes.

        Args:
            content_item: Dictionary to retrieve relevant paper data from

        Returns:
            Paper data as dictionary

        """
        title = content_item["title"]
        authors = [
            author_content["full_name"]
            for author_content in content_item["authors"]["authors"]
        ]
        abstract = content_item.get(
            "abstract", ""
        )  # old publications sometimes do not have an abstract
        return {"title": title, "abstract": abstract, "authors": authors}

    def _get_paper_data_from_web_content_item(
        self,
        content_item: bs4.BeautifulSoup,
    ) -> dict:
        """Retrieve single paper data from content item via bs4.

        Args:
            content_item: bs4 Tag to retrieve relevant paper data from

        Returns:
            Paper data as dictionary

        """
        if content_item.title.text == "Request Rejected":
            if self.force_content:
                return {"title": None, "abstract": None, "authors": None}
            else:
                raise ValueError(
                    "The request to the IEEE API was rejected. This usually occurs after a large amount of "
                    "requests. However, connecting and disconnection from a WIFI/Lan connection seems to fix "
                    "this problem. If this problem persists or occurs frequently, please consider"
                    "reducing the number of simultaneously opened connections in utils.py."
                )
        title = content_item.find("meta", property="og:title")["content"]
        # remove any styling (<xxx>, <\xxx>) from title
        title = re.sub(r"<[^>]+>", "", title)

        abstract = content_item.find("meta", property="og:description")[
            "content"
        ]
        authors = content_item.find("meta", attrs={"name": "parsely-author"})[
            "content"
        ]
        authors = authors.split(";")
        return {"title": title, "abstract": abstract, "authors": authors}
