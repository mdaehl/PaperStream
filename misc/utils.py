import asyncio
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
import bs4
import requests
from tqdm.asyncio import tqdm_asyncio

import config


@dataclass
class Paper:
    title: str
    authors: List[str]
    abstract: Optional[str]
    url: str
    source_domain: str = None
    html_content: str = None

    @property
    def id(self):
        return self.url

    def update(self, new):
        for key, value in new.items():
            if hasattr(self, key):
                setattr(self, key, value)


def get_soup(url: str, headers: Optional[dict] = None) -> bs4.BeautifulSoup:
    """Compact function to retrieve url and pass it into bs4."""
    content = requests.get(
        url, proxies=config.proxies, verify=config.verify_ssl, headers=headers
    ).content.decode("utf-8")
    soup = bs4.BeautifulSoup(content, features="lxml")
    return soup


async def fetch_url(
    session: aiohttp.client.ClientSession,
    url: str,
    headers: Optional[dict],
    params: Optional[dict],
) -> str:
    """Fetch URL using an aiohttp Session to allow asynchronous execution."""
    async with session.get(
        url, headers=headers, params=params, proxy=config.proxies["http"]
    ) as response:
        return await response.text()


async def get_urls_content(
    urls: List[str],
    headers_list: Optional[List[dict]] = None,
    params_list: Optional[List[dict]] = None,
) -> List[str]:
    if not headers_list:
        headers_list = len(urls) * [None]
    if not params_list:
        params_list = len(urls) * [None]

    connector = aiohttp.TCPConnector(
        limit=config.request_limit, verify_ssl=config.verify_ssl
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_url(session, url, headers, params)
            for url, headers, params in zip(urls, headers_list, params_list)
        ]
        try:
            html_contents = await tqdm_asyncio.gather(*tasks)
        except asyncio.TimeoutError:
            print("Timeout")

        return html_contents
