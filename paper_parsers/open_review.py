from abc import abstractmethod

import openreview
from openreview.openreview import Note

from misc.utils import Paper
from .base import APIProceedingParser


class OpenReviewParser(APIProceedingParser):
    """Parser for proceeding OpenReview proceedings. The documentation is not always straightforward and there are two
    versions of APIs depending on the venue.
    """

    def __init__(self, *args, **kwargs):
        self.base_url = "https://openreview.net"
        self.client_v1 = openreview.Client(
            baseurl="https://api.openreview.net",
        )
        self.client_v2 = openreview.api.OpenReviewClient(
            baseurl="https://api2.openreview.net",
        )

        super().__init__(*args, **kwargs)

    @property
    @abstractmethod
    def venue_id(self) -> str:
        """Returns: ID of desired venue. Can be find in url (.../group?id=VENUE_ID)."""
        raise NotImplementedError


class ICLRParser(OpenReviewParser):
    """Parser for the International Conference on Learning Representations (ICLR)."""

    @property
    def proceeding_name(self) -> str:
        """Returns: Name of the proceeding."""
        return "ICLR"

    def _validate_year(self) -> None:
        """Check default year conditions from super and that it is after 2020."""
        if self.year < 2020:
            raise ValueError(
                f"The year {self.year} is invalid. ICLR uses different format and therefore we support "
                f"just the latest one starting in 2020."
            )

    @property
    def venue_id(self) -> str:
        """Returns: ID of venue w.r.t. the requested year."""
        return f"ICLR.cc/{self.year}/Conference"

    def _request_contents(self) -> list[Note]:
        """Request all paper contents, where the specific request depends on the year.

        Returns:
            List of contents.
        """
        if self.year > 2023:
            return self.request_new_contents()
        else:
            return self.request_old_contents()

    def request_old_contents(self) -> list[Note]:
        """Request paper contents of earlier years (before 2022).

        Returns:
            List of contents.

        """
        return self.client_v1.get_all_notes(
            invitation=f"ICLR.cc/{self.year}/Conference/-/Blind_Submission",
            details="directReplies,original",
        )

    def request_new_contents(self) -> list[Note]:
        """Request paper contents of later and current years (after 2022).

        Returns:
            List of contents.

        """
        return self.client_v2.get_all_notes(
            invitation=f"ICLR.cc/{self.year}/Conference/-/Submission",
            details="directReplies,original",
        )

    def _filter_contents(self, request_contents: list[Note]) -> list[Note]:
        """Filter contents from requests depending on the year. Only keep the accepted papers.

        Args:
            request_contents: Contents to filter.

        Returns:
            Filtered Contents.

        """
        if self.year > 2023:
            return self.filter_new_contents(request_contents)
        else:
            return self.filter_old_contents(request_contents)

    @staticmethod
    def filter_new_contents(request_contents: list[Note]) -> list[Note]:
        """Filter later and current years (after 2022) of contents to keep only accepted papers.

        Args:
            request_contents: Contents to filter.

        Returns:
            Filtered Contents.

        """
        proceeding_submissions_replies = [
            submission.details["directReplies"] for submission in request_contents
        ]

        filtered_submissions = []
        for paper_replies, submission in zip(
            proceeding_submissions_replies, request_contents
        ):
            decision = [
                paper_reply["content"]["decision"]
                for paper_reply in paper_replies
                if paper_reply["content"].get("decision")
            ]

            if len(decision):
                decision = decision[0]

                if "Accept" in decision["value"]:
                    filtered_submissions.append(submission)

        return filtered_submissions

    @staticmethod
    def filter_old_contents(request_contents: list[Note]) -> list[Note]:
        """Filter earlier years (before 2022) of contents to keep only accepted papers.

        Args:
            request_contents: Contents to filter.

        Returns:
            Filtered Contents.

        """
        proceeding_submissions_replies = [
            submission.details["directReplies"] for submission in request_contents
        ]

        filtered_submissions = []
        for paper_replies, submission in zip(
            proceeding_submissions_replies, request_contents
        ):
            decision = [
                paper_reply["content"]["decision"]
                for paper_reply in paper_replies
                if paper_reply["invitations"].endswith("Decision")
            ][0]
            if "Accept" in decision:
                filtered_submissions.append(submission)

        return filtered_submissions

    def _parse_paper_content(
        self, paper_content: Note, paper_url: str | None = None
    ) -> Paper:
        """Parse paper content from API specific Note format (similar to dictionary).

        Args:
            paper_content: Paper content to parse.
            paper_url: Url of the paper content to support parsing. Just used for debugging.

        Returns:
            Parsed content as a Paper item.

        """
        content = paper_content.content

        title = content["title"]
        authors = content["authors"]
        abstract = content["abstract"]
        url = f"{self.base_url}/{content['pdf']}"
        return Paper(title, authors, abstract, url)
