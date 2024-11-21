import warnings

import bs4

from misc import utils
from misc.utils import Paper
from .base import WebProceedingParser


class ECCVParser(WebProceedingParser):
    """Parser for the all conferences of the European Computer Vision Association (ECVA)."""

    def __init__(self, *args, **kwargs):
        self.base_url = "https://www.ecva.net"
        super().__init__(*args, **kwargs)

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "ECCV"

    @property
    def conference_url(self) -> str:
        """Returns: Url of the conference."""
        return f"{self.base_url}/papers.php"

    def _get_url_containers(self) -> list[bs4.element.Tag]:
        """Get containers from the conference url.

        Returns:
            List of url containers which contain the paper urls itself.
        """
        main_soup = utils.get_soup(self.conference_url)
        url_containers = list(main_soup.select("dt.ptitle"))
        return url_containers

    def _get_paper_urls(self) -> list[str]:
        """Use super method to get paper urls and add base url to all. Finally filter the urls to match the desired
        year.

        Returns:
            List containing the paper urls.

        """
        paper_urls = super()._get_paper_urls()
        # add base url to all links
        paper_urls = [
            f"{self.base_url}/{paper_url}" for paper_url in paper_urls
        ]
        paper_urls = self.filter_urls(paper_urls)
        return paper_urls

    def filter_urls(self, urls: list[str]) -> list[str]:
        """Filter the urls w.r.t. the year as all years are on one page.

        Args:
            urls: List of urls to filter.

        Returns:
            Filtered list of urls.
        """
        return [url for url in urls if f"ECCV_{self.year}" in url]

    def _parse_paper_content(
        self, paper_content: str, paper_url: str = None
    ) -> Paper | None:
        """Parse paper content via bs4 into a paper object.

        Args:
            paper_content: Paper content to parse.
            paper_url: Url of the paper content to support parsing.

        Returns:
            Parsed content as a Paper item or None if the paper url is faulty.

        """
        soup = bs4.BeautifulSoup(paper_content, "lxml")
        try:
            # relevant infos
            title = soup.select("#papertitle")[0].get_text(strip=True)
            authors = soup.select("#authors >b >i")[0].get_text().split(",")
            abstract = soup.select("#abstract")[0].get_text(strip=True)

            sub_url = [
                item.get("href")
                for item in soup.select("a")
                if "pdf" in item.get_text()
            ][0]
            sub_url = sub_url.replace("../", "")  # remove overhead
            url = f"{self.base_url}/{sub_url}"

            return Paper(title, authors, abstract, url)

        except IndexError:
            warnings.warn(
                f"The paper with the link {paper_url} could not be found."
            )
            return
