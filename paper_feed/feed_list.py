import warnings
from itertools import chain

import yaml
from tqdm import tqdm

from misc import settings
from .content_completion import ContentCompletor
from .feed import Feed


class FeedList:
    """Feed list class which manages all processing across the individual feeds."""

    def __init__(
        self,
        use_config_file: bool,
        source_file: str | None = None,
        target_file: str | None = None,
        online: bool | None = None,
        appending: bool | None = None,
        remove_duplicates_within_feed: bool = True,
        remove_duplicates_across_feeds: bool = False,
        force_content: bool = False,
    ):
        """Args:
        use_config_file: Whether to use the YAML config file for the feeds.
        source_file: Optional source feed file, if no config file is used.
        target_file: Optional target feed file where the info should be saved, if no config file is used.
        online: Whether the feed file is online or not, if no config file is used.
        appending: Whether to append the content to an existing file or overwrite it, if no config file is used.
        remove_duplicates_within_feed: Whether to remove duplicate entries within a feed w.r.t. new entries.
        remove_duplicates_across_feeds: Whether to remove duplicate entries across feeds w.r.t. new entries.
        force_content: Whether to force content to be retrieved or not.
        """
        self.force_content = force_content

        # ensure there is just on feed input and the args match that
        if use_config_file and (
            source_file or target_file or online or appending
        ):
            raise ValueError(
                "You cannot use the config file and provide additional attributes."
            )
        # ensure that all params are present if the config should not be used
        if not use_config_file and not (
            source_file and target_file and online and appending
        ):
            raise ValueError(
                "You need to use the config file or provide additional information."
            )

        self.required_feed_attributes = {
            "source_file": str,
            "target_file": str,
            "online": bool,
            "appending": bool,
        }

        self.config_file = settings.feed_config_file

        # duplicate handling
        self.remove_duplicates_within_feed = remove_duplicates_within_feed
        self.remove_duplicates_across_feeds = remove_duplicates_across_feeds
        if (
            self.remove_duplicates_within_feed
            and remove_duplicates_across_feeds
        ):
            warnings.warn(
                "Duplicate removal within and across feeds was activated, therefore remove across feeds is selected."
            )

        if use_config_file:
            feed_settings = self._load_feed_settings_from_file()
        else:
            feed_settings = [
                {
                    "source_file": source_file,
                    "target_file": target_file,
                    "online": online,
                    "appending": appending,
                }
            ]

        self._validate_feed_settings(feed_settings)
        self.feed_settings = feed_settings

        self.feeds = self._init_feeds()

    @staticmethod
    def _load_feed_settings_from_file() -> list[dict]:
        """Load the relevant section from the config file, that contains the settings for all feeds.

        Returns:
            Dictionary containing the settings of all feeds.

        """
        try:
            return yaml.safe_load(open(settings.feed_config_file)).get(
                "pairings"
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"The file {settings.feed_config_file} was not found. Please check again or adapt the path in the config file."
            )
        except AttributeError:
            raise AttributeError(
                f"The file {settings.feed_config_file} seems to be missing the relevant section. Please check the template file."
            )

    def _validate_feed_settings(self, feed_settings: list[dict]) -> None:
        """Validate if the feed settings fulfill all requirements (contain the required attributes).

        Args:
            feed_settings: List of feed settings to validate.

        """
        for feed_setting in feed_settings:
            for key, expected_type in self.required_feed_attributes.items():
                # check if all attributes are present
                if key not in feed_setting:
                    raise KeyError(
                        f"Missing required key: '{key}' in feed_settings."
                    )

                # check if all elements in the attributes list are of the expected type
                if not isinstance(feed_setting[key], expected_type):
                    raise TypeError(
                        f"All elements in the list for key '{key}' should be of type {expected_type.__name__}."
                    )

    def _init_feeds(self) -> list[Feed]:
        """Initialize all feeds in the feed list.

        Returns:
            List of feeds objects from the feed list.

        """
        feeds = []
        for feed_setting in tqdm(
            self.feed_settings,
            total=len(self.feed_settings),
            desc="Initializing Feeds",
        ):
            feeds.append(
                Feed(
                    source_file=feed_setting["source_file"],
                    target_file=feed_setting["target_file"],
                    online=feed_setting["online"],
                    appending=feed_setting["appending"],
                )
            )
        return feeds

    def get_feed_data(self) -> None:
        """Retrieve the paper data of all feeds w.r.t. duplicates and assign the new contents to the papers of all feeds. The update stats are printed subsequently for information purposes."""
        self._remove_duplicates()
        self._complete_paper_data()
        self._print_stats()

    def _remove_duplicates(self):
        """Remove the duplicate entries within/across the feeds if desired."""
        id_lists = [feed.paper_ids for feed in self.feeds]

        if self.remove_duplicates_across_feeds:
            combined_id_list = list(chain.from_iterable(id_lists))
            unique_ids = set(combined_id_list)
            remove_status = {paper_id: False for paper_id in unique_ids}
            for feed in self.feeds:
                remove_status = feed.remove_papers_from_incomplete_feed(
                    unique_ids, remove_status
                )

        elif self.remove_duplicates_within_feed:
            unique_ids_lists = [set(id_list) for id_list in id_lists]
            for feed, unique_ids in zip(self.feeds, unique_ids_lists):
                feed.remove_papers_from_incomplete_feed(unique_ids)

    def _complete_paper_data(self) -> None:
        """Get the HTML contents of all papers from all feeds that are in the feed list. The content completor optimizes that data retrieval to minimize the requests. Finally assign the contents to the feeds and their respective papers."""
        incomplete_paper_list = [
            feed.incomplete_feed_papers for feed in self.feeds
        ]
        content_retriever = ContentCompletor(
            incomplete_paper_list, force_content=self.force_content
        )
        contents = content_retriever.get_contents()
        content_retriever.assign_contents(contents=contents)

    def _print_stats(self) -> None:
        """Print all update statistics, after parsing the feed list to inform the user about changes."""
        print("Update statistics:")
        for feed in self.feeds:
            print(f"{feed.target_file}: {feed.n_new_papers} new papers")

    def save_feeds(self) -> None:
        """Save the papers of each feed in the feed list."""
        for feed in tqdm(
            self.feeds,
            total=len(self.feeds),
            desc="Generating and saving atom feeds.",
        ):
            feed.save_feed()
