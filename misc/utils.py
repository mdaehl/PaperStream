import asyncio
import warnings
from dataclasses import dataclass

import aiohttp
import bs4
import requests
from tqdm.asyncio import tqdm_asyncio

from misc import settings


@dataclass
class Paper:
    """Helper class to handle paper instances."""

    title: str
    authors: list[str]
    abstract: str | None
    url: str
    source_domain: str = None
    html_content: str = None

    @property
    def id(self) -> str:
        """Returns: ID of the paper, which is defined as its url."""
        return self.url

    def update(self, new_val_dict: dict) -> None:
        """Update method to update variables just as in dictionaries inplace.

        Args:
            new_val_dict: Dictionary containing the value/key pairs to use for updating.

        """
        for key, value in new_val_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)


def get_soup(url: str, headers: dict | None = None) -> bs4.BeautifulSoup:
    """Compact function to retrieve url content and pass it into BeautifulSoup.

    Args:
        url: Url to get the content of.
        headers: Headers to use for requesting the url content.

    Returns:
        soup object of the provided url w.r.t. to the provided headers.
    """
    content = requests.get(
        url,
        proxies=settings.proxies,
        verify=settings.verify_ssl,
        headers=headers,
    ).content.decode("utf-8")
    soup = bs4.BeautifulSoup(content, features="lxml")
    return soup


async def fetch_url(
    session: aiohttp.client.ClientSession,
    url: str,
    headers: dict | None,
    params: dict | None,
) -> str:
    """Fetch Url content using an aiohttp client session to allow asynchronous execution.

    Args:
        session: Aiohttp client session used for the request.
        url: Url to get the content of.
        headers: Headers to use for requesting the url content.
        params: Parameters to pass to the url.

    Returns:
        Text of the content of the provided url.
    """
    retries = 3
    backoff_factor = 1

    for attempt in range(retries):
        try:
            async with session.get(
                url,
                headers=headers,
                params=params,
                proxy=settings.proxies["http"],
            ) as response:
                return await response.text()
        except (
            aiohttp.ClientConnectionError,
            aiohttp.ServerDisconnectedError,
        ):
            if attempt < retries - 1:
                backoff_time = backoff_factor * (2**attempt)
                warnings.warn(
                    f"Server disconnected. Retrying in {backoff_time} seconds..."
                )
                await asyncio.sleep(backoff_time)


async def get_urls_content(
    urls: list[str],
    headers_list: list[dict] | None = None,
    params_list: list[dict] | None = None,
    request_limit: int | None = settings.request_limit,
) -> list[str]:
    """Request the contents from multiple urls asynchronously.

    Args:
        urls: Urls to get the content of.
        headers_list: Headers to use for requesting the urls.
        params_list: Parameters to use for requesting the urls.
        request_limit: Request limit of asynchronous requests. By default, the settings request limit is used.

    Returns:
        List containing the contents of the provided urls.

    """
    if not headers_list:
        headers_list = len(urls) * [None]
    if not params_list:
        params_list = len(urls) * [None]

    connector = aiohttp.TCPConnector(
        limit=request_limit,
        verify_ssl=settings.verify_ssl,
        limit_per_host=request_limit,
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_url(session, url, headers, params)
            for url, headers, params in zip(urls, headers_list, params_list)
        ]
        html_contents = await tqdm_asyncio.gather(*tasks)

        return html_contents
