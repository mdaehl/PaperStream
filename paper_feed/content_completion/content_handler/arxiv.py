import math
import re
from itertools import batched

import bs4

from misc.utils import Paper
from .base import ContentHandler


class ArxivContentHandler(ContentHandler):
    """ContentHandler to access Arxiv data."""

    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query?id_list"
        self.max_request_size = (
            100  # good trade off between size and speed but can be increased
        )

    def _get_request_urls(self, paper_list: list[Paper]) -> list[str]:
        """Build request urls, where multiple papers are grouped to reduce the number of requests.

        Args:
            paper_list: List of papers

        Returns:
            URLs required for the requests

        """
        # get arxiv ids from url
        arxiv_ids = list(map(lambda x: x.url.split("/")[-1], paper_list))

        # split request urls based on max_request size
        arxiv_id_splits = batched(arxiv_ids, self.max_request_size)

        request_urls = []
        for split in arxiv_id_splits:
            request_urls.append(
                f"{self.base_url}={','.join(split)}&max_results={self.max_request_size}"
            )
        return request_urls

    def _get_request_identifiers(
        self, paper_list: list[Paper]
    ) -> list[list[str | None]]:
        """Build request identifiers to be able to subsequently assign the individual papers of combined requests. The Arxiv API preserves the order of combined request, hence, no identifier needed but the shape is still w.r.t. the request size.

        Args:
            paper_list: List of papers

        Returns:
            Nested list of request identifiers

        """
        return [
            [None] for _ in range(math.ceil(len(paper_list) / self.max_request_size))
        ]

    def _get_request_headers(self, paper_list: list[Paper]) -> list[None]:
        """Build request headers to retrieve the publisher related paper information. No header is required but the shape depends on the request size.

        Args:
            paper_list: List of papers

        Returns:
            List of headers

        """
        return math.ceil(len(paper_list) / self.max_request_size) * [None]

    def get_paper_contents_from_request_content(
        self, content: str, content_ids: list[str] | None = None
    ) -> list[dict]:
        """Retrieve general paper contents from request content via bs4. Afterward get the individual paper information via extra processing as well.

        Args:
            content: Retrieved content to get the paper data from.
            content_ids: List of content IDs for processing the content. Just used for debugging.

        Returns:
            List containing paper data as dictionaries.

        """
        content = bs4.BeautifulSoup(content, features="xml")
        split_content = content.find_all("entry")
        paper_data_list = [
            self.get_paper_data_from_content_item(content_item)
            for content_item in split_content
        ]
        return paper_data_list

    @staticmethod
    def get_paper_data_from_content_item(
        content_item: bs4.element.Tag,
    ) -> dict:
        """Retrieve single paper data from content item via bs4.

        Args:
            content_item: bs4 Tag to retrieve relevant paper data from

        Returns:
            Paper data as dictionary

        """
        title = content_item.select("entry >title")[0].text
        abstract = content_item.find("summary").text
        abstract = abstract.replace("\n", " ").strip()
        authors = content_item.select("author >name")
        authors = list(map(lambda x: x.text, authors))

        # remove all extra whitespace items
        title = re.sub(r"\s+", " ", title)
        abstract = re.sub(r"\s+", " ", abstract)
        authors = list(map(lambda x: re.sub(r"\s+", " ", x), authors))

        return {"title": title, "abstract": abstract, "authors": authors}
