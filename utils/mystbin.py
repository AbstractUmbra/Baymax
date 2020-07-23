import aiohttp

MB_POST = "https://mystb.in/documents"

async def mb(content: str, *, session: aiohttp.ClientSession = None):
    timeout = aiohttp.ClientTimeout(total=15.0)
    session = session or aiohttp.ClientSession(raise_for_status=True)
    async with session.post(MB_POST, data=content.encode("utf-8"), timeout=timeout) as mb_res:
        url = await mb_res.json()
    short_id = url['key']
    return f"https://mystb.in/{short_id}"