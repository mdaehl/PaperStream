import asyncio
import os
import warnings
from abc import abstractmethod, ABC
from typing import Any
from datetime import datetime

import bs4

from misc import utils, settings
from misc.export import AtomFileExporter, CSVFileExporter, JSONFileExporter
from misc.utils import Paper


class ProceedingParser(ABC):
    """Base ProceedingParser, which is used to parse conferences."""

    def __init__(self, year: int):
        """Args:
            year: Year of the proceeding to parse.
        """
        self.year = year
        self.papers = []

        self._validate_year()

    @property
    @abstractmethod
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding
        """
        raise NotImplementedError

    @abstractmethod
    def retrieve_papers(self) -> None:
        """Abstract method for retrieving all papers of the proceeding.
        """
        raise NotImplementedError

    @abstractmethod
    def _parse_paper_content(self, paper_content: Any, paper_url: str | None = None) -> Paper:
        """Abstract method for parsing paper content into a paper item.

        Args:
            paper_content: Paper content to parse.
            paper_url: Url of the paper content to support parsing.

        Returns:
            Parsed content as a Paper item.

        """
        raise NotImplementedError

    def _validate_year(self) -> None:
        """Check if the proceeding year is valid. The year cannot be in the future.
        """
        if self.year > datetime.now().year:
            raise ValueError("The year cannot be in the future.")

    @staticmethod
    def _get_async_request_contents(
        urls: list[str],
        headers_list: list[dict] | None = None,
        params_list: list[dict] | None = None,
    ) -> list[str]:
        """Perform asynchronous request based on the provided infos.

        Args:
            urls: urls to request
            headers_list: list of headers to use for the requests
            params_list: list params to use for the requests

        Returns:
            Contents of the requests

        """
        loop = asyncio.get_event_loop()
        paper_contents = loop.run_until_complete(
            utils.get_urls_content(urls, headers_list, params_list)
        )
        return paper_contents

    @property
    def default_output_file(self):
        """Returns: Default file name of the output file, when being exported.
        """
        return f"{settings.output_file_dir}/{self.proceeding_name}_{self.year}"

    def export_papers(
        self, output_file: str | None = None, file_type: str = "json"
    ) -> None:
        """Export papers stored in the parser to an output file of desired file type.

        Args:
            output_file: Optional name of the stored file with or without file extension.
            file_type: Type of file to store in papers in.

        """
        export_funcs = {
            "csv": self._export_to_csv,
            "json": self._export_to_json,
            "atom_feed": self._export_to_atom_feed,
        }
        if file_type not in export_funcs.keys():
            raise ValueError(
                f"The file type {file_type} is not supported. Please select from {', '.join(export_funcs.keys())}"
            )

        if len(self.papers) == 0:
            warnings.warn("No papers found, therefore no file was created.")
        else:
            if output_file is None:
                output_file = self.default_output_file
                os.makedirs("output_files", exist_ok=True)

            print(f"Exporting papers to {output_file}.{file_type}.")
            export_funcs[file_type](output_file)

    def _export_to_csv(self, output_file: str | None = None) -> None:
        """Helper function to trigger csv export.

        Args:
            output_file: Optional name of the output file with or without file extension.

        """
        CSVFileExporter(output_file).export_papers(self.papers)

    def _export_to_atom_feed(self, output_file: str | None = None) -> None:
        """Helper function to trigger atom feed export.

        Args:
            output_file: Optional name of the output file with or without file extension.

        """
        AtomFileExporter(output_file).export_papers(self.papers)

    def _export_to_json(self, output_file: str | None = None) -> None:
        """Helper function to trigger json export.

        Args:
            output_file: Optional name of the output file with or without file extension.

        """
        JSONFileExporter(output_file).export_papers(self.papers)


class APIProceedingParser(ProceedingParser):
    """Class of proceeding parser that is based on API requests.
    """

    @abstractmethod
    def request_contents(self) -> list[Any]:
        """Request all paper contents.

        Returns:
            List of contents.

        """
        raise NotImplementedError

    @staticmethod
    def process_contents(request_contents: list[dict]) -> list[dict]:
        """Process the raw request contents, if required. This base method does not perform any processing.

        Args:
            request_contents: List of raw paper contents from requests.

        Returns:
            Processed contents.

        """
        return request_contents

    def filter_contents(self, request_contents: list[dict]) -> list[dict]:
        """Base function for filtering contents. In this case simply the original contents are returned.

        Args:
            request_contents: Contents to filter.

        Returns:
            Filtered Contents.

        """
        return request_contents

    def retrieve_papers(self) -> None:
        """Core function to retrieve all papers of the proceeding. Initially request the paper contents via the API.
        Process and filter the contents if required/desired. Finally, parse the contents to get the paper items.

        """
        print("Getting paper contents.")
        contents = self.request_contents()
        print("Processing paper contents.")
        contents = self.process_contents(contents)
        print("Filtering paper contents.")
        contents = self.filter_contents(contents)
        print("Parsing paper contents.")
        self.papers = [
            self._parse_paper_content(paper_content)
            for paper_content in contents
        ]


class WebProceedingParser(ProceedingParser):
    """Class of proceeding parser that is based on web scraping.
    """

    def __init__(self, year: int):
        """Args:
            year: Year of the proceeding to parse.
        """
        super().__init__(year)
        self.requester = None

    def get_paper_urls(self) -> list[str]:
        """
        Retrieve the paper urls by first getting the url container and extracting the content.

        Returns: List containing the paper urls.

        """
        url_containers = self._get_url_containers()
        urls = list(map(lambda x: x.find("a")["href"], url_containers))
        return urls

    @abstractmethod
    def _get_url_containers(self) -> list[bs4.element.Tag]:
        """Get containers (Tags) from the webpage which contain the paper urls.

        Returns:
            Url container item which contains the paper urls itself.

        """
        raise NotImplementedError

    def retrieve_papers(self) -> None:
        """Core function to retrieve all papers of the proceeding. First get all paper urls and getting their contents
        via requests asynchronously. Finally, parse the contents to get the paper items.
        """
        print("Getting paper urls.")
        paper_urls = self.get_paper_urls()

        if len(paper_urls):
            print("Getting paper contents.")
            paper_contents = self._get_async_request_contents(paper_urls[:])
            print("Parsing paper contents.")
            papers = [
                self._parse_paper_content(paper_content, paper_url)
                for paper_content, paper_url in zip(paper_contents, paper_urls)
            ]
            self.papers = [paper for paper in papers if paper]
        else:
            raise ValueError(
                "No paper urls found. Please check if the conference is not yet held."
            )
