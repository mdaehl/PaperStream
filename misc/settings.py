http_proxy = None
https_proxy = None

proxies = {"http": http_proxy, "https": https_proxy}

verify_ssl = True

request_limit = 2  # number of simultaneously opened connections for aiohttp & asyncio

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
}

credentials_file = "credentials.yaml"

config_file = "config.yaml"

output_file_dir = "../output_files"
