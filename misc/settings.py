http_proxy = None
https_proxy = None

proxies = {"http": http_proxy, "https": https_proxy}

verify_ssl = True

request_limit = 50  # number of simultaneously opened connections for aiohttp & asyncio; 50 does work reliably from experience

# In general, a limit of 10 works reliably for feed parsing but sometimes Elsevier API can be a bottleneck.
# The elsevier API allows 10 requests per second, however a request limit of 4 seemed to be the upper limit to work reliably with a large number of requests.
# Hence, lower the limit to 4, in case you run into problems.
feed_completion_request_limit = 10

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
}

credentials_file = "misc/credentials.yaml"

feed_config_file = "misc/feed_config.yaml"

output_file_dir = "output_files"  # used a default folder for parsed proceedings
