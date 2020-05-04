"""
The MIT License (MIT)

Copyright (c) 2020 AbstractUmbra

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

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
