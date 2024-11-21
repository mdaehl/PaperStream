import warnings
from abc import ABC
from itertools import chain

import bs4

from misc import utils
from misc.utils import Paper
from .base import WebProceedingParser


class CVFParser(WebProceedingParser, ABC):
    """Parser for the all conferences of the Computer Vision Foundation (CVF)."""

    def __init__(self, *args, **kwargs):
        self.base_url = "https://openaccess.thecvf.com"
        super().__init__(*args, **kwargs)

    @property
    def conference_url(self) -> str:
        """Returns: Url of the conference w.r.t. the requested year."""
        return f"{self.base_url}/{self.proceeding_name}{self.year}"

    def _validate_year(self) -> None:
        """Check default year conditions from super and that it is after 2013."""
        super()._validate_year()
        if self.year < 2013:
            raise ValueError(
                "The CVF conferences are only available from 2013."
            )

    def _get_url_containers(self) -> list[bs4.element.Tag]:
        """Get containers from the conference url. Try to use all day page and individual days as backup.

        Returns:
            List of url containers which contain the paper urls itself.
        """
        # try all day site
        all_day_url = f"{self.conference_url}?day=all"
        all_day_soup = utils.get_soup(all_day_url)
        url_containers = all_day_soup.select("dt.ptitle")

        # use individual dates alternatively
        if len(url_containers) == 0:
            main_page_soup = utils.get_soup(self.conference_url)
            conference_days = [
                item["href"] for item in main_page_soup.select("dd >a")
            ]
            container_urls = [
                f"{self.base_url}/{conference_day}"
                for conference_day in conference_days
            ]
            conference_days_soups = map(utils.get_soup, container_urls)
            paper_title_urls_per_day = [
                soup.select("dt.ptitle") for soup in conference_days_soups
            ]

            # combine all days
            url_containers = list(
                chain.from_iterable(paper_title_urls_per_day)
            )

        return url_containers

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
            authors = [author.strip() for author in authors]
            abstract = soup.select("#abstract")[0].get_text(strip=True)
            url = soup.find("meta", attrs={"name": "citation_pdf_url"})[
                "content"
            ]

            return Paper(title, authors, abstract, url)

        except IndexError:
            warnings.warn(
                f"The paper with the link {paper_url} could not be found."
            )
            return

    def _get_paper_urls(self) -> list[str]:
        """Use super method to get paper urls and add base url to all.

        Returns:
            List containing the paper urls.

        """
        paper_urls = super()._get_paper_urls()
        # add base url to all links
        paper_urls = [
            f"{self.base_url}/{paper_urls}" for paper_urls in paper_urls
        ]
        return paper_urls


class CVPRParser(CVFParser):
    """Parser for the Conference on Computer Vision and Pattern Recognition (CVPR)."""

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "CVPR"


class ICCVParser(CVFParser):
    """Parser for the International Conference on Computer Vision (ICCV)."""

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "ICCV"

    def _validate_year(self) -> None:
        """Check default year conditions from super and that it is an even year, as it only held every second year."""
        super()._validate_year()
        if self.year % 2 == 0:
            raise ValueError("The ICCV is only held every second year.")


class WACVParser(CVFParser):
    """Parser for the Winter Conference on Applications of Computer Vision (WACV)."""

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "WACV"

    def _validate_year(self) -> None:
        """Check default year conditions from super and that it is after 2020."""
        super()._validate_year()
        if self.year < 2020:
            raise ValueError("The conference WACV is available from 2020.")
