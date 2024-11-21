from abc import abstractmethod

import yaml

from misc import settings
from misc.utils import Paper


class ContentHandler:
    """ContentHandler to complete content information of papers"""
    @abstractmethod
    def _get_request_urls(self, paper_list: list[Paper]) -> list[str]:
        """
        Build urls to retrieve the publisher related paper information.

        Args:
            paper_list: List of papers

        Returns:
            URLs required for the requests

        """
        raise NotImplementedError

    def _get_request_headers(self, paper_list: list[Paper]) -> list[None]:
        """
        Build request headers to retrieve the publisher related paper information. By default, all headers are None.

        Args:
            paper_list: List of papers

        Returns:
            List of headers
        """
        return len(paper_list) * [None]

    @abstractmethod
    def _get_paper_data_from_request_content(
        self, content: str, content_ids: list[str] | None = None
    ) -> list[dict]:
        """Retrieve paper data from the request content.

        Args:
            content: Retrieved content to get the paper data from.
            content_ids: Optional list of content IDs for processing the content.

        Returns:
            List containing paper data as dictionaries.

        """
        raise NotImplementedError

    def get_request_identifiers(
        self, paper_list: list[Paper]
    ) -> list[list[str | None]]:
        """
        Build request identifiers to be able to subsequently assign the individual papers of combined requests.
        By default, it is just one paper per request, hence, a formatted list of Nones is returned.

        Args:
            paper_list: List of papers

        Returns:
            Nested list of request identifiers.

        """
        return [[None] for _ in range(len(paper_list))]

    def get_request_info(self, paper_list: list[Paper]) -> dict:
        """
        Get all information required for the requests.

        Args:
            paper_list: List of papers

        Returns:
            Dictionary containing urls, headers and identifiers of the papers used for requesting their content.

        """
        request_info = {
            "request_urls": self._get_request_urls(paper_list),
            "request_headers": self._get_request_headers(paper_list),
            "identifiers": self.get_request_identifiers(paper_list),
        }
        return request_info


class KeyedContentHandler(ContentHandler):
    """Extended ContentHandler that uses a key secured API."""
    @abstractmethod
    def _validate_api_key(self, api_key: str) -> bool:
        """Abstract method to validate if the API key is valid.

        Args:
            api_key: API key to validate.

        Returns:
            Boolean value indicating if the API key is valid.

        """
        raise NotImplementedError

    def _load_api_key(self, api_key_name: str) -> str | None:
        """
        Load API key from config yaml file if present. Otherwise, just return None.

        Args:
            api_key_name: Name of the key to look for in the yaml file.

        Returns:
            API key of the provided name if it exists, otherwise None.

        """
        with open(settings.credentials_file, "r") as f:
            content = yaml.safe_load(f)
        api_key = content.get(api_key_name)
        if self._validate_api_key(api_key):
            return api_key
        else:
            return None