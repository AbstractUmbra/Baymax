""" Quick func to publish to mystb.in and return url. """

from aiohttp import (
    ClientSession,
    ClientTimeout
)


async def mystbin(content: str) -> str:
    """Upload the content to mystbin and return the url.
    :param content: str: Raw content to upload
    :return: str: URL to the uploaded content
    :raises aiohttp.ClientException: on failure to upload
    """
    timeout = ClientTimeout(total=15.0)
    async with ClientSession(raise_for_status=True) as cli_sesh:
        async with cli_sesh.post('https://mystb.in/documents',
                                 data=content.encode('utf-8'),
                                 timeout=timeout) as res:
            post = await res.json()
    uri = post['key']
    return f'https://mystb.in/{uri}'
