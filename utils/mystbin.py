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

import aiohttp

MB_POST = "https://mystb.in/documents"

async def mb(content: str, *, session: aiohttp.ClientSession = None, suffix: str = None):
    """ Post `content` to MystB.in with optional suffix text. """
    timeout = aiohttp.ClientTimeout(total=15.0)
    session = session or aiohttp.ClientSession(raise_for_status=True)
    async with session.post(MB_POST, data=content.encode("utf-8"), timeout=timeout) as mb_res:
        url = await mb_res.json()
    short_id = url['key']
    suffix = f".{suffix}" if suffix else None
    return f"https://mystb.in/{short_id}{suffix}"
