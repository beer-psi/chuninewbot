import string
from html import escape
from typing import TYPE_CHECKING, Optional

from aiohttp import web
from discord import Permissions
from discord.utils import oauth_url

from utils import json_loads

if TYPE_CHECKING:
    from bot import ChuniBot


COOKIE_CHARACTERS = string.ascii_lowercase + string.digits


router = web.RouteTableDef()


@router.get("/invite")
async def invite(request: web.Request) -> web.Response:
    permissions = Permissions(
        read_messages=True,
        send_messages=True,
        send_messages_in_threads=True,
        manage_messages=True,
        read_message_history=True,
    )
    url = oauth_url(request.config_dict["bot"].user.id, permissions=permissions)

    raise web.HTTPFound(url)


@router.post("/login")
async def login(request: web.Request) -> web.Response:
    params = {}
    content_type = request.headers.get("Content-Type")
    if content_type == "application/json":
        params = await request.json(loads=json_loads)
    elif content_type in ["application/x-www-form-urlencoded", "multipart/form-data"]:
        params = await request.post()
    else:
        raise web.HTTPBadRequest(reason="Invalid Content-Type")

    if "otp" not in params or "clal" not in params:
        raise web.HTTPBadRequest(reason="Missing parameters")

    otp = params["otp"]
    clal = params["clal"]
    if not isinstance(otp, str) or not isinstance(clal, str):
        raise web.HTTPBadRequest(reason="Invalid parameters")

    if clal.startswith("clal="):
        clal = clal[5:]

    if len(clal) != 64 or any(c not in COOKIE_CHARACTERS for c in clal):
        raise web.HTTPBadRequest(reason="Invalid cookie provided")

    if not otp.isdigit() and len(otp) != 6:
        raise web.HTTPBadRequest(reason="Invalid passcode provided")

    request.config_dict["bot"].dispatch(f"chunithm_login_{otp}", clal)

    goatcounter = request.config_dict["goatcounter"]
    goatcounter_tag = (
        f'<script data-goatcounter="{goatcounter}" async src="//gc.zgo.at/count.js"></script>'
        if goatcounter
        else ""
    )
    return web.Response(
        text=f"""
<!DOCTYPE html>
<html lang="en">
    <head>
        <title>chuninewbot login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta charset="utf-8">
        {goatcounter_tag}
    </head>
    <body>
        <h1>Success!</h1>
        <p>Check the bot's DMs to see if the account has been successfully linked.</p>

        <div>
            <p>full sync dx plus users can use this command to log in:</p>
            <code>m!login {escape(clal)}</code>
        </div>

        <div>
            <p>mimi xd bot users can use this command to log in:</p>
            <code>m>login clal={escape(clal)}</code>
        </div>

        <img alt="Chuni Penguin sleeping" src="https://chunithm-net-eng.com/mobile/images/pen_sleep_apng.png">
    </body>
</html>
""",
        content_type="text/html",
    )


async def on_response_prepare(_: web.Request, response: web.StreamResponse):
    response.headers.add("x-content-type-options", "nosniff")
    if response.headers.get("server"):
        del response.headers["server"]


def init_app(bot: "ChuniBot", goatcounter: Optional[str] = None) -> web.Application:
    app = web.Application()
    app.on_response_prepare.append(on_response_prepare)

    app.add_routes(router)

    app["bot"] = bot
    app["goatcounter"] = goatcounter
    return app
