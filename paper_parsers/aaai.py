import asyncio
import itertools

import bs4

from misc import utils, settings
from misc.utils import Paper
from .base import WebProceedingParser


class AAAIParser(WebProceedingParser):
    def __init__(self, *args, **kwargs):
        self.base_url = "https://ojs.aaai.org/index.php/AAAI"
        self.year_mapping = {
            2020: {"start": 249, "end": 258},
            2021: {"start": 385, "end": 402},
            2022: {"start": 507, "end": 521},
            2023: {"start": 548, "end": 560},
            2024: {"start": 576, "end": 596},
        }
        super().__init__(*args, **kwargs)

    @property
    def proceeding_name(self) -> str:
        return "AAAI"

    def _validate_year(self) -> None:
        """Check default year conditions from super and ensure that year is part of the year_mapping.
        """
        super()._validate_year()
        if self.year not in self.year_mapping.keys():
            raise ValueError(
                f"{self.year} is an invalid year. By default conferences starting from 2020 are supported. "
                f"If you want to add other year find out the start and end view here "
                f"https://ojs.aaai.org/index.php/AAAI/issue/archive and add it to the year_mapping."
            )

    def _get_url_containers(self) -> list[bs4.element.Tag]:
        """Get containers from the base url w.r.t. the individual issues in the defined range of year_mapping.

        Returns:
            List of url containers which contain the paper urls itself.

        """
        start_idx = self.year_mapping[self.year]["start"]
        end_idx = self.year_mapping[self.year]["end"]
        conference_pages = [
            f"{self.base_url}/issue/view/{i}" for i in range(start_idx, end_idx)
        ]

        # get all page contents via asyncio
        loop = asyncio.get_event_loop()
        headers_list = len(conference_pages) * [settings.headers]
        page_contents = loop.run_until_complete(
            utils.get_urls_content(conference_pages, headers_list=headers_list)
        )
        # process each page content
        soup_contents = map(lambda x: bs4.BeautifulSoup(x, "lxml"), page_contents)
        url_containers = map(
            lambda x: x.find_all("div", class_="obj_article_summary"), soup_contents
        )
        # combine url containers of each page into a single list
        url_containers = list(itertools.chain.from_iterable(url_containers))

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

        title = soup.find("h1", class_="page_title").getText(strip=True)
        authors = soup.find_all("meta", attrs={"name": "citation_author"})
        authors = list(map(lambda x: x["content"], authors))

        # sometimes the abstract seems to be missing
        try:
            abstract = (
                soup.find("h2", string="Abstract")
                .find_next_sibling(string=True)
                .getText(strip=True)
            )
        except AttributeError:
            abstract = ""

        url = soup.find("a", class_="obj_galley_link")["href"]

        return Paper(title, authors, abstract, url)
