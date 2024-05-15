from http.client import SERVICE_UNAVAILABLE

import httpx
from bs4 import BeautifulSoup

from ._bs4 import BS4_FEATURE
from .exceptions import ChuniNetError, MaintenanceException


async def raise_on_chunithm_net_error(response: httpx.Response):
    if response.url.path != "/mobile/error/":
        return

    html = ""
    async for chunk in response.aiter_text():
        html += chunk

    dom = BeautifulSoup(html, BS4_FEATURE)
    error_blocks = dom.select(".block.text_l .font_small")
    code = int(error_blocks[0].text.split(": ", 1)[1])
    description = error_blocks[1].text if len(error_blocks) > 1 else ""

    raise ChuniNetError(code, description)


async def raise_on_scheduled_maintenance(response: httpx.Response):
    if response.status_code == SERVICE_UNAVAILABLE:
        raise MaintenanceException
