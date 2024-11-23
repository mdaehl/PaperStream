import argparse
from paper_feed import FeedList


def parse_feed_list(
    use_config_file: bool,
    source_file: str,
    target_file: str,
    online: bool,
    appending: bool,
    remove_duplicates_within_feed: bool,
    remove_duplicates_across_feeds: bool,
):
    """Parse the feed list w.r.t. the provided user input and save the feed files.

    Args:
    use_config_file: Whether to use the YAML config file for the feeds.
    source_file: Optional source feed file, if no config file is used.
    target_file: Optional target feed file where the info should be saved, if no config file is used.
    online: Whether the feed file is online or not, if no config file is used.
    appending: Whether to append the content to an existing file or overwrite it, if no config file is used.
    remove_duplicates_within_feed: Whether to remove duplicate entries within a feed w.r.t. new entries.
    remove_duplicates_across_feeds: Whether to remove duplicate entries across feeds w.r.t. new entries.
    """
    feed_list = FeedList(
        use_config_file=use_config_file,
        source_file=source_file,
        target_file=target_file,
        online=online,
        appending=appending,
        remove_duplicates_within_feed=remove_duplicates_within_feed,
        remove_duplicates_across_feeds=remove_duplicates_across_feeds,
    )
    feed_list.get_feed_data()
    feed_list.save_feeds()


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--use_config",
        "-u",
        action="store_true",
        help="Use mapping of feeds from config file.",
    )
    arg_parser.add_argument(
        "--source", "-s", help="Path to xml feeds file.", type=str
    )
    arg_parser.add_argument(
        "--target",
        "-t",
        help="Name of the result feed file (target_file) without extension.",
        type=str,
    )
    arg_parser.add_argument(
        "--online",
        "-o",
        action="store_true",
        help="Whether the feed file is stored online.",
    )
    arg_parser.add_argument(
        "-a",
        "--append",
        action="store_true",
        help="Append new entries to current feed file",
    )
    arg_parser.add_argument(
        "--remove_within",
        action="store_true",
        help="Remove duplicates within feeds.",
    )
    arg_parser.add_argument(
        "--remove_across",
        action="store_true",
        help="Remove duplicates across feeds.",
    )
    input_args = arg_parser.parse_args()

    parse_feed_list(
        use_config_file=input_args.use_config,
        source_file=input_args.source,
        target_file=input_args.target,
        online=input_args.online,
        appending=input_args.append,
        remove_duplicates_within_feed=input_args.remove_within,
        remove_duplicates_across_feeds=input_args.remove_across,
    )
