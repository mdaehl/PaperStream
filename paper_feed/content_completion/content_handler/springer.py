import json
import math
import re
from abc import abstractmethod
from itertools import batched

import bs4
import requests

from misc import settings
from misc.utils import Paper
from .base import KeyedContentHandler


class SpringerBaseContentHandler(KeyedContentHandler):
    """Base class to handle Springer content."""

    def __init__(self):
        self.api_url = "https://api.springernature.com/meta/v2/json"
        self.api_key = self._load_api_key("springer_api_key")
        self.api_max_records = 25  # Fixed Number of the API for free account
        if self.api_key:
            self.use_api = True
        else:
            self.use_api = False

    def _validate_api_key(self, api_key: str) -> bool:
        """Validate if the API key is valid by requesting a random article.

        Args:
            api_key: API key to validate.

        Returns:
            Boolean value indicating if the API key is valid.

        """
        params = {"q": "doi:10.1038/227680a0", "api_key": api_key}
        request = requests.get(
            self.api_url,
            params=params,
            proxies=settings.proxies,
            verify=settings.verify_ssl,
        )

        if request.status_code == 200:
            return True
        elif request.status_code == 403:
            raise ValueError("The Springer/Nature API key is invalid.")
        else:
            return False

    def _get_request_identifiers(
        self, paper_list: list[Paper]
    ) -> list[list[str]]:
        """Build request identifiers to be able to subsequently assign the individual papers of combined requests. If the API is used, the DOIs are stored as identification info. Otherwise, the super method is used, as no identification for single paper requests is needed.

        Args:
            paper_list: List of papers

        Returns:
            Nested list of request identifiers.

        """
        if self.use_api:
            return self._get_paper_dois(paper_list)
        else:
            return super()._get_request_identifiers(paper_list)

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

    def _get_request_headers(self, paper_list: list[Paper]) -> list[None]:
        """Build request headers to retrieve the publisher related paper information. The API requires no headers but the webpage requires User-Agents.

        Args:
            paper_list: List of papers

        Returns:
            List of headers

        """
        if self.use_api:
            return math.ceil(len(paper_list) / self.api_max_records) * [None]
        else:
            return len(paper_list) * [settings.headers]

    @staticmethod
    def _get_webscrape_request_urls(paper_list: list[Paper]) -> list[str]:
        """Get urls for webscraping. Each url requests solely a single paper.

        Args:
            paper_list: List of papers

        Returns:
            URLs required for the requests

        """
        return [paper.url for paper in paper_list]

    def _get_api_request_urls(self, paper_list: list[Paper]) -> list[str]:
        """Build request urls for the API, where multiple papers are grouped to reduce the number of requests. Required parameters are also incorporated.

        Args:
            paper_list: List of papers

        Returns:
            URLs required for the requests

        """
        dois_list = self._get_paper_dois(paper_list)
        dois_list = [
            [f"doi:{doi}" for doi in doi_items] for doi_items in dois_list
        ]

        request_urls = []
        for dois in dois_list:
            params = {
                "q": f"({' OR '.join(dois)})",
                "api_key": self.api_key,
                "p": self.api_max_records,
            }
            request_urls.append(
                requests.Request("GET", self.api_url, params=params)
                .prepare()
                .url
            )

        return request_urls

    @staticmethod
    @abstractmethod
    def _get_paper_data_from_web_content_item(
        content_item: bs4.element.Tag,
    ) -> dict:
        """Abstract method to retrieve single paper data from content item via bs4.

        Args:
            content_item: bs4 Tag to retrieve relevant paper data from

        Returns:
            Paper data as dictionary
        """
        raise NotImplementedError

    @staticmethod
    def _get_paper_data_from_api_content_item(content_item: dict) -> dict:
        """Abstract method to retrieve single paper data from content selecting the json attributes.

        Args:
            content_item: Dictionary to retrieve relevant paper data from

        Returns:
            Paper data as dictionary

        """
        title = content_item["title"]
        abstract = content_item["abstract"]
        authors = content_item["creators"]
        authors = list(map(lambda x: x["creator"], authors))
        return {"title": title, "abstract": abstract, "authors": authors}

    @abstractmethod
    def _get_paper_dois(self, paper_list: list[Paper]) -> list[list[str]]:
        """Abstract method to get the paper DOIs per request from the URLs.

        Args:
            paper_list: List of papers

        Returns:
            Nested list containing the paper DOIs per request

        """
        raise NotImplementedError

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
            article_contents = json_content["records"]

            # If an article is missing for whatever reason we will it with a template. The information will then NOT be
            # updated when reassigning the content.
            missing_articles = set(content_ids) - set(
                [i["doi"] for i in article_contents]
            )
            if len(missing_articles) > 0:
                for missing_article in missing_articles:
                    article_contents.append(
                        {
                            "title": None,
                            "abstract": None,
                            "creators": [{"creator": None}],
                            "doi": missing_article,
                        }
                    )

            article_contents = sorted(
                article_contents, key=lambda x: content_ids.index(x["doi"])
            )

            paper_data_list = [
                self._get_paper_data_from_api_content_item(content_item)
                for content_item in article_contents
            ]
        else:
            content = bs4.BeautifulSoup(content, features="lxml")
            paper_data_list = [
                self._get_paper_data_from_web_content_item(content)
            ]

        return paper_data_list


class SpringerContentHandler(SpringerBaseContentHandler):
    """ContentHandler to access Springer data. It does work with and without an API key, though the API version is recommended for stability reasons. The API limit is extremely high, hence, it should not be a limitation."""

    def _get_paper_dois(self, paper_list: list[Paper]) -> list[list[str]]:
        """Get the paper DOIs per request from the URLs.

        Args:
            paper_list: List of papers

        Returns:
            Nested list containing the paper DOIs per request

        """
        paper_dois = []
        for paper in paper_list:
            paper_url = paper.url
            sub_doi = paper_url.split("/")[-1]
            sub_doi = sub_doi.split(
                "#"
            )[
                0
            ]  # sometimes paging information is in the url, which is not part of the DOI
            sub_doi = re.sub(
                ".pdf", "", sub_doi
            )  # free articles have a ".pdf" at the end
            doi_preface = paper_url.split("/")[-2]
            paper_dois.append(f"{doi_preface}/{sub_doi}")

        return list(
            map(lambda x: list(x), batched(paper_dois, self.api_max_records))
        )

    @staticmethod
    def _get_paper_data_from_web_content_item(
        content_item: bs4.BeautifulSoup,
    ) -> dict:
        """Retrieve single paper data from content item via bs4.

        Args:
            content_item: bs4 Tag to retrieve relevant paper data from

        Returns:
            Paper data as dictionary

        """
        # ignore books, as they usually arise from faulty scholar links which do not forward correctly
        url = content_item.find("meta", property="og:url")["content"]
        if "book" in url:
            title = abstract = authors = None
        else:
            title = content_item.find("meta", property="og:title")["content"]
            abstract = content_item.find("meta", property="og:description")["content"]
            authors = list(
                map(
                    lambda x: x["content"],
                    content_item.find_all(
                        "meta", attrs={"name": "citation_author"}
                    ),
                )
            )
        return {"title": title, "abstract": abstract, "authors": authors}


class NatureContentHandler(SpringerBaseContentHandler):
    """ContentHandler to access Nature data, which is based on Springer. It does work with and without an API key, though the API version is recommended for stability reasons. The API limit is extremely high, hence, it should not be a limitation."""

    def _get_paper_dois(self, paper_list: list[Paper]) -> list[list[str]]:
        """Get the paper DOIs per request from the URLs.

        Args:
            paper_list: List of papers

        Returns:
            Nested list containing the paper DOIs per request

        """
        paper_dois = []
        for paper in paper_list:
            paper_url = paper.url
            sub_doi = paper_url.split("/")[-1]
            sub_doi = sub_doi.split(
                "#"
            )[
                0
            ]  # sometimes paging information is in the url, which is not part of the DOI
            sub_doi = re.sub(
                ".pdf", "", sub_doi
            )  # free articles have a ".pdf" at the end
            doi_preface = "10.1038"  # fixed DOI of nature
            paper_dois.append(f"{doi_preface}/{sub_doi}")

        return list(
            map(lambda x: list(x), batched(paper_dois, self.api_max_records))
        )

    @staticmethod
    def _get_paper_data_from_web_content_item(
        content_item: bs4.BeautifulSoup,
    ) -> dict:
        """Retrieve single paper data from content item via bs4.

        Args:
            content_item: bs4 Tag to retrieve relevant paper data from

        Returns:
            Paper data as dictionary

        """
        title = content_item.find("meta", attrs={"name": "dc.title"})[
            "content"
        ]
        abstract = content_item.find("meta", attrs={"name": "description"})[
            "content"
        ]
        authors = list(
            map(
                lambda x: x["content"],
                content_item.find_all("meta", attrs={"name": "dc.creator"}),
            )
        )
        return {"title": title, "abstract": abstract, "authors": authors}
