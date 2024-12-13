import re

import bs4

from misc import utils
from misc.utils import Paper
from .base import WebProceedingParser


class BMVCParser(WebProceedingParser):
    """Parser for the Conference on British Machine Vision Conference (BMVC)."""

    def __init__(self, *args, **kwargs):
        self.year_mapping = {
            2022: "https://bmvc2022.mpi-inf.mpg.de",
            2023: "https://proceedings.bmvc2023.org",
        }
        super().__init__(*args, **kwargs)

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "BMVC"

    @property
    def conference_url(self) -> str:
        """Returns: Url of the conference w.r.t. the requested year."""
        return self.year_mapping[self.year]

    def _validate_year(self) -> None:
        """Check default year conditions from super and ensure that year is part of the year_mapping."""
        super()._validate_year()
        if self.year not in self.year_mapping.keys():
            raise ValueError(
                f"{self.year} is an invalid year. Years prior to 2022 are generally not supported as it requires"
                f"pdf parsing and currently supported years are {','.join(map(str, self.year_mapping.keys()))}."
            )

    def _get_url_containers(self) -> list[bs4.element.Tag]:
        """Get containers from the conference url.

        Returns:
            List of url containers which contain the paper urls itself.
        """
        main_soup = utils.get_soup(self.conference_url)
        url_containers = list(main_soup.find_all("tr", id="paper"))
        return url_containers

    def _parse_paper_content(self, paper_content: str, paper_url: str = None) -> Paper:
        """Parse paper content via bs4 into a paper object.

        Args:
            paper_content: Paper content to parse.
            paper_url: Url of the paper content to support parsing.

        Returns:
            Parsed content as a Paper item.

        """
        soup = bs4.BeautifulSoup(paper_content, "lxml")

        title = soup.find("title").get_text()
        abstract = soup.find("h2", id="abstract").find_next_sibling(
            string=True, strip=True
        )

        # get authors and url from citation section via regex
        citation_text = soup.find("pre", class_="highlight").get_text()
        authors_match = re.search(
            "author *= {(?P<authors>.*?)}", citation_text, re.DOTALL
        )
        authors_text = authors_match.group("authors")
        authors = authors_text.split(" and ")
        url_match = re.search("url *= {(?P<url>.*?)}", citation_text)
        url = url_match.group("url")

        return Paper(title, authors, abstract, url)
