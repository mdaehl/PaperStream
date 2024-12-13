import os
from urllib import parse

import bs4
import requests

from misc import settings
from misc.export import AtomFileExporter
from misc.utils import Paper


class Feed:
    """Feed class which does handle all paper processing of a single Feed."""

    def __init__(
        self,
        source_file: str,
        target_file: str,
        online: bool,
        appending: bool = True,
    ):
        """Args:
        source_file: Source feed file
        target_file: Target feed file where the info should be saved.
        online: Whether the feed file is online or not.
        appending: Whether to append the content to an existing file or overwrite it.
        """
        self.source_file = source_file
        self.target_file = target_file
        self.online = online
        self.appending = appending

        self.feed_content = self._load_feed_content()  # content as BeautifulSoup

        if self.appending:
            self.existing_papers = self._get_existing_papers()
        else:
            self.existing_papers = []

        self.incomplete_feed_papers = self._parse_feed()
        self.n_new_papers = len(self.incomplete_feed_papers)

    @property
    def papers(self) -> list[Paper]:
        """Returns: List of all papers (existing and not yet parsed ones) in the feed file."""
        return self.existing_papers + self.incomplete_feed_papers

    @property
    def incomplete_paper_ids(self) -> list[str]:
        """Returns: List of paper IDs of incomplete papers."""
        return [paper.id for paper in self.incomplete_feed_papers]

    @property
    def existing_paper_ids(self):
        """Returns: List of paper IDs of existing papers."""
        return [paper.id for paper in self.existing_papers]

    @property
    def paper_ids(self) -> list:
        """Returns: List of paper IDs of all papers."""
        return [paper.id for paper in self.papers]

    def _load_feed_content(self) -> bs4.BeautifulSoup:
        """Load the feed from a local file or request the content if it is online and parse the content via bs4.

        Returns:
            File feed content.

        """
        if self.online:
            try:
                content = requests.get(
                    self.source_file,
                    proxies=settings.proxies,
                    verify=settings.verify_ssl,
                ).content.decode("utf-8")
            except requests.exceptions.InvalidSchema:
                raise ValueError(f"{self.source_file} is no valid URL.")
        else:
            with open(self.source_file, "r", encoding="utf-8") as file:
                content = file.read()
        return bs4.BeautifulSoup(content, "xml")

    def _get_existing_papers(self) -> list[Paper]:
        """Get the papers which are already in the existing feed file.

        Returns:
            List of papers which are already in the feed file.

        """
        existing_papers = []
        if os.path.isfile(self.target_file):
            with open(self.target_file, "r", encoding="utf-8") as file:
                file_content = file.read()
                file_soup_content = bs4.BeautifulSoup(file_content, "xml")

            titles = list(
                map(lambda x: x.text, file_soup_content.select("entry >title"))
            )
            all_authors = list(
                map(
                    lambda x: list(map(lambda y: y.text, x.select("author"))),
                    file_soup_content.select("entry"),
                )
            )
            abstracts = list(
                map(
                    lambda x: x.text,
                    file_soup_content.select("entry >summary"),
                )
            )
            links = list(map(lambda x: x.text, file_soup_content.select("entry >id")))

            for title, authors, abstract, url in zip(
                titles, all_authors, abstracts, links
            ):
                existing_papers.append(
                    Paper(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        url=url,
                    )
                )

        return existing_papers

    def _parse_feed(self) -> list[Paper]:
        """Parse the papers of the raw atom feed file. These papers are incomplete at this point and later completed.

        Returns:
            List of incomplete papers.

        """
        entry_bundle = self.feed_content.find_all("entry")
        existing_urls = set([paper.url for paper in self.existing_papers])

        feed_papers = []
        for bundle_data in entry_bundle:
            content = bundle_data.find("content")
            soup = bs4.BeautifulSoup(content.text, "lxml")

            bundle_papers = soup.find_all("a", {"class": "gse_alrt_title"})
            bundle_authors_str = soup.find_all(
                "div", attrs={"style": "color:#006621;line-height:18px"}
            )
            bundle_authors = list(
                map(
                    lambda x: x.text.split("-")[0].strip().split(","),
                    bundle_authors_str,
                )
            )
            bundle_authors = [
                [author.strip() for author in bundle_author]
                for bundle_author in bundle_authors
            ]

            for paper_entry, authors in zip(bundle_papers, bundle_authors):
                title = paper_entry.text

                scholar_url = paper_entry["href"]
                url = self._convert_url(scholar_url)

                if url in existing_urls:
                    continue

                url_domain = parse.urlparse(url).netloc
                domain = ".".join(url_domain.split(".")[-2:])

                current_paper = Paper(
                    title=title,
                    authors=authors,
                    abstract=None,
                    url=url,
                    source_domain=domain,
                )
                feed_papers.append(current_paper)

        return feed_papers

    @staticmethod
    def _convert_url(scholar_url: str) -> str:
        """Resolve the original url, removing the Google Scholar specifics, if present.

        Args:
            scholar_url: Google Scholar URL of the article.

        Returns:
            Original URL of the article.

        """
        try:
            return parse.parse_qs(parse.urlparse(scholar_url).query)["url"][0]
        except KeyError:
            return scholar_url

    def save_feed(self) -> None:
        """Save the papers in the feed to the atom file."""
        AtomFileExporter(self.target_file).export_papers(self.papers)

    def remove_papers_from_incomplete_feed(
        self,
        paper_ids: set[str],
        remove_status: dict | None = None,
    ) -> dict:
        """Use dictionary to track which IDs need to be removed and update their status after processing one batch of paper IDs. Hence, a paper which was kept in the first feed would be removed from subsequent feed if it has the same ID.

        Args:
            paper_ids: Set of all paper IDs
            remove_status: Status dictionary based on the paper IDs, indicating where a paper should be removed or not.

        Returns:
            Updated remove status, after iterating over the provided paper IDs.

        """
        if not remove_status:
            remove_status = {paper_id: False for paper_id in paper_ids}

        pos_delete = []
        for idx, paper in enumerate(self.incomplete_feed_papers):
            if paper.id in remove_status and remove_status[paper.id]:
                pos_delete.append(idx)
                self.n_new_papers -= 1
            else:
                remove_status[paper.id] = True

        pos_delete = set(pos_delete)  # just for speed up while looking up
        self.incomplete_feed_papers = [
            paper
            for idx, paper in enumerate(self.incomplete_feed_papers)
            if idx not in pos_delete
        ]
        return remove_status
