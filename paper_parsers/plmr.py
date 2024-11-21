from abc import abstractmethod

import bs4

from misc import utils
from misc.utils import Paper
from .base import WebProceedingParser


class PLMRParser(WebProceedingParser):
    """Parser for conferences of the Proceedings of Machine Learning Research (PLMR)."""

    def __init__(self, *args, **kwargs):
        self.base_url = "https://proceedings.mlr.press"
        super().__init__(*args, **kwargs)

    @property
    @abstractmethod
    def year_mapping(self) -> dict:
        """Abstract property of year to ID mapping.

        Returns:
            Mapping of years to versions (IDs).
        """
        raise NotImplementedError

    @property
    def conference_url(self) -> str:
        """Returns: Url of the conference w.r.t. the requested year."""
        return f"{self.base_url}/{self.year_mapping[self.year]}"

    def _validate_year(self) -> None:
        """Check default year conditions from super and ensure that year is part of the year_mapping."""
        super()._validate_year()
        if self.year not in self.year_mapping.keys():
            raise ValueError(
                f"{self.year} is an invalid year. If you want to add the year check the version at "
                f"https://proceedings.mlr.press/ and add it to the respective year_mapping."
            )

    def _get_url_containers(self) -> list[bs4.element.Tag]:
        """Get containers from the conference url.

        Returns:
            List of url containers which contain the paper urls itself.
        """
        main_soup = utils.get_soup(self.conference_url)
        url_containers = list(main_soup.select("p.links"))
        return url_containers

    def _parse_paper_content(
        self, paper_content: str, paper_url: str = None
    ) -> Paper:
        """Parse paper content via bs4 into a paper object.

        Args:
            paper_content: Paper content to parse.
            paper_url: Url of the paper content to support parsing.

        Returns:
            Parsed content as a Paper item.

        """
        soup = bs4.BeautifulSoup(paper_content, "lxml")

        title = soup.find("h1").getText()
        authors = list(
            map(
                lambda x: x["content"],
                soup.find_all("meta", attrs={"name": "citation_author"}),
            )
        )
        abstract = soup.select("#abstract")[0].get_text(strip=True)
        url = soup.find("meta", attrs={"name": "citation_pdf_url"})["content"]

        return Paper(title, authors, abstract, url)


class AISTATSParser(PLMRParser):
    """Parser for the International Conference on Artificial Intelligence and Statistics (AISTATS)."""

    @property
    def year_mapping(self) -> dict:
        """Returns: Mapping of years to versions (IDs)."""
        return {
            2020: "v108",
            2021: "v130",
            2022: "v151",
            2023: "v206",
            2024: "v238",
        }

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "AISTATS"


class CORLParser(PLMRParser):
    """Parser for the Conference on Robot Learning (CORL)."""

    @property
    def year_mapping(self) -> dict:
        """Returns: Mapping of years to versions (IDs)."""
        return {
            2020: "v155",
            2021: "v164",
            2022: "v205",
            2023: "v229",
        }

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "CORL"


class ICMLParser(PLMRParser):
    """Parser for the International Conference on Machine Learning (ICML)."""

    @property
    def year_mapping(self) -> dict:
        """Returns: Mapping of years to versions (IDs)."""
        return {
            2020: "v119",
            2021: "v139",
            2022: "v162",
            2023: "v202",
            2024: "v235",
        }

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "ICML"
