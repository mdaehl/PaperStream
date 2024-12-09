import asyncio
import itertools
import re
from collections import defaultdict
from copy import deepcopy
from typing import List
import warnings
import textwrap

from misc import utils, settings
from misc.utils import Paper
from .content_handler import (
    ArxivContentHandler,
    ElsevierContentHandler,
    IEEEContentHandler,
    SpringerContentHandler,
    NatureContentHandler,
)


class ContentCompletor:
    """Content completor to get missing data of incomplete papers from Google Scholar notifications."""

    def __init__(
        self, paper_lists: List[List[Paper]], force_content: bool = False
    ):
        """Initialize a ContentCompletor object.

        Args:
            paper_lists: List of papers
            force_content: Whether to force content to be retrieved or not.
        """
        self.paper_lists = paper_lists

        self.content_handlers = {
            "arxiv.org": ArxivContentHandler(),
            "ieee.org": IEEEContentHandler(force_content=force_content),
            "sciencedirect.com": ElsevierContentHandler(
                force_content=force_content
            ),
            "springer.com": SpringerContentHandler(),
            "nature.com": NatureContentHandler(),
        }

        self.papers_grouped_by_source = defaultdict(list)
        self.request_infos = {}
        self.index_mapping_request_to_flatten_paper = {}

        self.mapping_flattened_list_to_two_d = {}

        # order that maps global index to the list of papers that is created for each domain in source_grouped_papers
        self.input_order_indices = defaultdict(list)

    def get_contents(self):
        """Get the contents of the papers in the paper list. First group them across the different feeds to optimize the request. Subsequently, build the request urls and request their contents.

        Returns:
            Requested paper contents.

        """
        self._group_papers_by_domain()
        self._build_request_urls()
        contents = self._request_contents()
        return contents

    def _group_papers_by_domain(self) -> None:
        """Group papers of all feeds according to their publishers to allow combined (optimized) requests later."""
        flattened_idx = 0
        for idx_feed, paper_list in enumerate(self.paper_lists):
            for idx_paper, paper in enumerate(paper_list):
                self.papers_grouped_by_source[paper.source_domain].append(
                    paper
                )
                self.input_order_indices[paper.source_domain].append(
                    flattened_idx
                )
                self.mapping_flattened_list_to_two_d[flattened_idx] = (
                    idx_feed,
                    idx_paper,
                )
                flattened_idx += 1

    def _build_request_urls(self) -> None:
        """Build the request urls (and headers) based on the publisher."""
        for domain, papers in self.papers_grouped_by_source.items():
            content_handler = self.content_handlers.get(domain)

            if content_handler:
                request_info = content_handler.get_request_info(papers)
                self.request_infos[domain] = request_info

    def _request_contents(self) -> list[str]:
        """Request all html contents with aiohttp based on the request urls and headers.

        Returns:
            Requested paper contents.

        """
        loop = asyncio.get_event_loop()
        request_urls = list(
            itertools.chain.from_iterable(
                map(lambda x: x["request_urls"], self.request_infos.values())
            )
        )
        request_headers = list(
            itertools.chain.from_iterable(
                map(
                    lambda x: x["request_headers"], self.request_infos.values()
                )
            )
        )

        contents = loop.run_until_complete(
            utils.get_urls_content(
                request_urls,
                request_headers,
                request_limit=settings.feed_completion_request_limit,
            )
        )
        return contents

    def _regroup_contents(self, contents: list[str]) -> dict:
        """Group the split contents w.r.t. to the domains to make later processing easier.

        Args:
            contents: Requested paper contents.

        Returns:
            Grouped contents w.r.t. domains as dictionary containing domain specific lists.

        """
        grouped_contents = {}
        global_pos = 0
        for domain, i in self.request_infos.items():
            grouped_contents[domain] = []
            for _ in i["request_urls"]:
                grouped_contents[domain].append(contents[global_pos])
                global_pos += 1
        return grouped_contents

    def assign_contents(self, contents: list[str]) -> None:
        """Assign the requested contents and assign them to the respective papers the paper list. Therefore, the request content is split /processed by the content handlers, if required.

        Args:
            contents: New paper contents to assign them to the existing papers.

        """
        # group contents w.r.t. domains
        grouped_contents = self._regroup_contents(contents)

        for domain, content_list in grouped_contents.items():
            content_handler = self.content_handlers[domain]

            content_ids_list = self.request_infos[domain]["identifiers"]
            paper_data_list = []
            for content, content_ids in zip(content_list, content_ids_list):
                paper_data_list += (
                    content_handler.get_paper_contents_from_request_content(
                        content, content_ids
                    )
                )

            # update the paper list
            flattened_indices = self.input_order_indices[domain]
            list_two_d_indices = [
                self.mapping_flattened_list_to_two_d[idx]
                for idx in flattened_indices
            ]

            for paper_data, two_d_idx in zip(
                paper_data_list, list_two_d_indices
            ):
                # skip paper data which could be not retrieved correctly
                if paper_data["title"] is None:
                    continue

                feed_idx, paper_idx = two_d_idx
                selected_paper = self.paper_lists[feed_idx][paper_idx]

                if self._validate_assignment(selected_paper, paper_data):
                    selected_paper.update(paper_data)

    @staticmethod
    def _validate_assignment(selected_paper: Paper, paper_data: dict) -> bool:
        """Validate the assignment of the new content to the existing paper.

        Args:
            selected_paper: Paper to which the data is assigned.
            paper_data: Data which is used for updating/assigned new information.

        Returns:
            Whether the assignment is valid and the data should be updated.
        """
        unprocessed_title = selected_paper.title
        processed_title = paper_data["title"]
        new_title = deepcopy(
            processed_title
        )  # avoid altering the original data
        old_title = deepcopy(
            unprocessed_title
        )  # avoid altering the original data

        # compare bare strings (without spacing, case-sensitivity or special characters)
        new_title = re.sub(r"[^a-zA-Z0-9]", "", new_title).lower()
        old_title = re.sub(r"[^a-zA-Z0-9]", "", old_title).lower()

        # sometimes the actual title is longer/shorter compared to the requested one
        # therefore check if either one is in the other one
        if old_title in new_title or new_title in old_title:
            return True
        else:
            # use user input for manual validation/selection
            user_input = input(
                textwrap.fill(
                    f"\nThe titles of the original title and the updated one do not seem to match. The "
                    f"unprocessed title is '{unprocessed_title}' and the processed title is '{processed_title}'. "
                    f"Please check at the URL {selected_paper.url} if they refer to the same paper but might just "
                    f"be different versions. If you would like to match them, enter 'yes' and 'no' if the processed"
                    f" content should be ignored. You can also 'cancel' to check the for a potential error source "
                    f"yourself and stop the ongoing processing.\n",
                    width=80,
                )
            )
            while True:
                if user_input == "yes":
                    return True
                elif user_input == "no":
                    warnings.warn(
                        f"The paper {unprocessed_title} is not updated with extra content."
                    )
                    return False
                elif user_input == "cancel":
                    raise ValueError(
                        f"Original title ({unprocessed_title}) and updated title ({processed_title}) do not match."
                    )
                else:
                    user_input = input(
                        "\nInvalid input. Please type 'yes', 'no', or 'cancel'.\n"
                    )
