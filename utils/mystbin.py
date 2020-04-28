"""
Robo-Hz Discord Bot
Copyright (C) 2020 64Hz

Robo-Hz is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Robo-Hz is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with Robo-Hz. If not, see <https://www.gnu.org/licenses/>.
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
