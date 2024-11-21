import bs4

from misc import utils
from misc.utils import Paper
from .base import WebProceedingParser


class NIPSParser(WebProceedingParser):
    """Parser for the Conference on Neural Information Processing Systems (NIPS)."""

    def __init__(self, *args, **kwargs):
        self.base_url = "https://papers.nips.cc"
        super().__init__(*args, **kwargs)

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "NIPS"

    @property
    def conference_url(self) -> str:
        """Returns: Url of the conference w.r.t. the requested year."""
        return f"{self.base_url}/paper_files/paper/{self.year}"

    def _validate_year(self) -> None:
        """Check default year conditions from super and ensure the year is not before the first conference was held in
        1987.
        """
        super()._validate_year()
        if self.year < 1987:
            raise ValueError(
                "The conferences NIPS is only available until 1987."
            )

    def _get_url_containers(self) -> list[bs4.element.Tag]:
        """Get containers (Tags) from the conference url which contain the paper urls.

        Returns:
            Url container item which contains the paper urls itself.

        """
        main_soup = utils.get_soup(self.conference_url)
        main_container = main_soup.find("ul", class_="paper-list")
        if main_container:
            url_containers = list(main_container.select("li"))
        else:
            url_containers = []
        return url_containers

    def _parse_paper_content(
        self, paper_content: str, paper_url: str = None
    ) -> Paper | None:
        """Parse paper content via bs4 into a paper object.

        Args:
            paper_content: Paper content to parse.
            paper_url: Url of the paper content to support parsing.

        Returns:
            Parsed content as a Paper item.

        """
        soup = bs4.BeautifulSoup(paper_content, "lxml")

        title = soup.find("title").getText()
        authors = soup.select("p >i")[0].text.split(",")
        authors = [author.strip() for author in authors]
        abstract = (
            soup.find("h4", text="Abstract")
            .find_next("p")
            .find_next("p")
            .getText()
        )
        abstract = abstract.replace(
            "  ", " "
        )  # sometimes there are double spaces
        url = soup.find("meta", attrs={"name": "citation_pdf_url"})["content"]

        return Paper(title, authors, abstract, url)

    def _get_paper_urls(self) -> list[str]:
        """Use super method to get paper urls and add base url to all.

        Returns:
            List containing the paper urls.

        """
        paper_urls = super()._get_paper_urls()
        # add base url to all links
        return [f"{self.base_url}/{paper_url}" for paper_url in paper_urls]
