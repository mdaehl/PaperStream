import json
import re

import requests

from misc import settings
from misc.utils import Paper
from .base import KeyedContentHandler


class ElsevierContentHandler(KeyedContentHandler):
    """ContentHandler to access Elsevier data. It does work with and without an API key, though the API version is recommended for stability reasons. The API limit is extremely high, hence, it should not be a limitation."""

    def __init__(self):
        self.api_url = "https://api.elsevier.com/content/article/pii"
        self.api_max_records = (
            200  # Fixed Number of the API, increasing it does not work
        )

        self.api_key = self._load_api_key("elsevier_api_key")

        if self.api_key:
            self.use_api = True
        else:
            self.use_api = False

    def _validate_api_key(self, api_key: str):
        """Validate if the API key is valid by requesting a random article.

        Args:
            api_key: API key to validate.

        Returns:
            Boolean value indicating if the API key is valid.

        """
        params = {"apikey": api_key}
        headers = {"Accept": "application/json"}
        random_pii = "016926079501640F"  # any valid pii will do
        request = requests.get(
            f"{self.api_url}/{random_pii}",
            params=params,
            headers=headers,
            proxies=settings.proxies,
            verify=settings.verify_ssl,
        )

        if request.status_code == 200:
            return True
        elif request.status_code == 401:
            raise ValueError("The Elsevier API key is invalid.")
        else:
            return False

    @staticmethod
    def get_pii_from_url(url: str) -> str:
        """Extract the Personally Identifiable Information (PII) from the URL.

        Args:
            url: Paper URL

        Returns:
            PII
        """
        match = re.search("pii/(?P<pii>.*)", url)
        pii = match.group("pii")
        return pii

    def _get_request_urls(self, paper_list: list[Paper]) -> list[str]:
        """Build request urls depending on if the API or direct page requests are used.

        Args:
            paper_list: List of papers

        Returns:
            URLs required for the requests

        """
        if self.use_api:
            piis = [self.get_pii_from_url(paper.url) for paper in paper_list]
            request_urls = [
                f"{self.api_url}/{pii}?apiKey={self.api_key}" for pii in piis
            ]
            return request_urls
        else:
            return []

    def _get_request_headers(self, paper_list: list[Paper]) -> list[dict]:
        """Build request headers to retrieve the publisher related paper information. Json as return format is desired.

        Args:
            paper_list: List of papers

        Returns:
            List of headers

        """
        if self.use_api:
            headers = {"Accept": "application/json"}
            return len(paper_list) * [headers]
        else:
            return []

    def get_paper_contents_from_request_content(
        self, content: str, content_ids: list[str] | None = None
    ) -> list[dict]:
        """Retrieve general paper contents using the json format. Afterward, get the individual paper information via extra processing as well.

        Args:
            content: Retrieved content to get the paper data from.
            content_ids: Optional list of content IDs for processing the content.

        Returns:
            List containing paper data as dictionaries.

        """
        json_content = json.loads(content)
        paper_data_list = [self.get_paper_data_from_content_item(json_content)]
        return paper_data_list

    @staticmethod
    def get_paper_data_from_content_item(content_item: dict) -> dict:
        """Retrieve single paper data from content selecting the json attributes.

        Args:
            content_item: Dictionary to retrieve relevant paper data from

        Returns:
            Paper data as dictionary

        """
        if content_item.get("error-response") is not None:
            raise ValueError(
                "The request to the Elsevier API was rejected. This usually occurs after a large amount "
                "of requests. If this problem persists or occurs frequently, please consider using reducing the "
                "number of simultaneously opened connections in utils.py. Lower the feed_completion_request_limit to 4 "
                "to make sure, that it does not fail."
            )

        data = content_item["full-text-retrieval-response"]["coredata"]
        title = data["dc:title"].strip()
        authors_item = data["dc:creator"]
        authors = list(map(lambda x: x["$"], authors_item))
        abstract = data["dc:description"].strip()
        abstract = re.sub(r"\s+", " ", abstract)
        return {"title": title, "abstract": abstract, "authors": authors}
