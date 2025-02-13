import argparse
import re

import requests
from tqdm import tqdm
import bs4

from misc import settings


def load_xml_feed_file(file_path: str) -> str:
    """Load feed file and get its content.

    Args:
        file_path: Path to the feed file.

    Returns:
        Content of the feed file.
    """
    try:
        content = requests.get(
            file_path,
            proxies=settings.proxies,
            verify=settings.verify_ssl,
        ).content.decode("utf-8")
    except requests.exceptions.InvalidSchema:
        raise ValueError(f"{file_path} is no valid URL.")
    return content


def get_activation_link(
    content: str,
) -> str:
    """Extract confirmation url from feed content.

    Args:
        content: Content of the feed file.

    Returns:
        Confirmation url required to activate the feed.

    """
    soup = bs4.BeautifulSoup(content, "xml")
    content_html = soup.find("content").text
    content_soup = bs4.BeautifulSoup(content_html, "html.parser")
    confirmation_url = content_soup.find("a", string="Confirm")
    confirmation_url = confirmation_url["href"]
    return confirmation_url


def activate_feed(
    args: argparse.Namespace,
) -> None:
    """Activate the Google Scholar feeds automatically by extracting the confirmation url and opening it via requests
    and a header to emulate a user. Basic request calls are blocked by Google. Google Scholar does NOT send out a mail
    if the confirmation was completed successful. Instead, you should get recommendations in your feed as soon as
    Google Scholar sends out a mail notification (usually every few days based on your keywords).

    Args:
        args: Command line arguments.
    """
    print("Activating google scholar feeds.")
    files = args.files

    for file in tqdm(files):
        content = load_xml_feed_file(file)
        link = get_activation_link(content)
        response = requests.get(
            link,
            proxies=settings.proxies,
            headers=settings.headers,
            verify=settings.verify_ssl,
        )
        if response.status_code != 200:
            raise Warning(
                f"Google seems to block the automatic activation. You can either try to wait or open the url {link} manually."
            )


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--files",
        "-f",
        nargs="+",
        help="Path/s to the xml file/s.",
    )
    input_args = arg_parser.parse_args()
    activate_feed(input_args)
