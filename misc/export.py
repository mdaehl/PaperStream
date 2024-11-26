import abc
import csv
import json
import re
from abc import abstractmethod
from xml.sax.saxutils import escape

from misc.utils import Paper


class FileExporter(abc.ABC):
    """Base class exporter to export list of papers into a file."""

    def __init__(self, output_file: str):
        """Initialize a FileExporter object.

        Args:
        output_file: name/path of the output file without file extension.
        """
        self.output_file = output_file

    @abstractmethod
    def export_papers(self, paper_list: list[Paper]) -> None:
        """Export list of papers into a file.

        Args:
            paper_list: List of papers which should be exported.

        """
        raise NotImplementedError


class AtomFileExporter(FileExporter):
    """Exporter to export list of papers into an atom feed file."""

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape special characters in the text in order to support the xml format.

        Args:
            text: text to be escaped w.r.t. to xml format.
        """
        return escape(text, entities={"'": "&apos;", '"': "&quot;"})

    def _build_paper_entry(self, paper: Paper) -> str:
        """Build a paper entry in the atom format.

        Args:
            paper: Paper to build a feed entry for.

        Returns:
            Atom feed entry for the given paper.

        """
        authors_entry = ""
        for author in paper.authors:
            authors_entry += f"<author><name>{author}</name></author>"

        abstract = paper.abstract if paper.abstract is not None else ""

        return (
            f"<entry> "
            f"<id>{self._escape_xml(paper.url)}</id>"
            f"<title>{self._escape_xml(paper.title)}</title> "
            f"<summary>{self._escape_xml(abstract.strip())} </summary> "
            f"{authors_entry} "
            f'<link href="{self._escape_xml(paper.url)}" rel="alternate" type="text/html"/>  '
            f'<link title="pdf" href="{self._escape_xml(paper.url)}" rel="related" type="application/pdf"/>'
            f"</entry>"
        )

    def _build_atom_feed(self, paper_list: list[Paper]) -> str:
        """Build an atom feed string by combining the entries of each paper in the paper list into an atom template string.

        Args:
            paper_list: List of papers to use for building the atom feed string.

        Returns:
            Atom feed in string format.

        """
        entries = [self._build_paper_entry(paper) for paper in paper_list]
        entries = "\n".join(entries)

        atom_feed_string = (
            f'<?xml version="1.0" encoding="UTF-8"?> '
            f'<feed xmlns="http://www.w3.org/2005/Atom"> '
            f"{entries} "
            f"</feed>"
        )

        return atom_feed_string

    def export_papers(self, paper_list: list[Paper]) -> None:
        """Export list of papers into an atom feed file.

        Args:
            paper_list: List of papers which should be exported.

        """
        atom_feed_str = self._build_atom_feed(paper_list)

        # get rid of optional file extension
        self.output_file = re.sub(".xml", "", self.output_file)

        with open(f"{self.output_file}.xml", "w", encoding="utf-8") as f:
            f.write(atom_feed_str)


class CSVFileExporter(FileExporter):
    """Exporter to export list of papers into a csv file."""

    def export_papers(self, paper_list: list[Paper]) -> None:
        """Export list of papers into a csv file.

        Args:
            paper_list: List of papers which should be exported.

        """
        exported_fields = ["title", "authors", "abstract", "url"]

        # get rid of optional file extension
        self.output_file = re.sub(".csv", "", self.output_file)

        with open(
            f"{self.output_file}.csv", "w", newline="", encoding="utf-8"
        ) as f:
            data = [
                {k: v for k, v in vars(paper).items() if k in exported_fields}
                for paper in paper_list
            ]
            writer = csv.DictWriter(f, fieldnames=exported_fields)
            writer.writeheader()  # add columns names
            writer.writerows(data)


class JSONFileExporter(FileExporter):
    """Exporter to export list of papers into a json file."""

    def export_papers(self, paper_list: list[Paper]) -> None:
        """Export list of papers into a json file.

        Args:
            paper_list: List of papers which should be exported.

        """
        exported_fields = ["title", "authors", "abstract", "url"]

        # get rid of optional file extension
        self.output_file = re.sub(".json", "", self.output_file)

        with open(f"{self.output_file}.json", "w", encoding="utf-8") as f:
            data = [
                {k: v for k, v in vars(paper).items() if k in exported_fields}
                for paper in paper_list
            ]
            json.dump(data, f, indent=4)
