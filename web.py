from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from bot import ChuniBot


router = web.RouteTableDef()


@router.post("/chuninewbot/login")
async def login(request: web.Request) -> web.Response:
    params = {}
    content_type = request.headers.get("Content-Type")
    if content_type == "application/json":
        params = await request.json()
    elif content_type in ["application/x-www-form-urlencoded", "multipart/form-data"]:
        params = await request.post()
    else:
        raise web.HTTPBadRequest(reason="Invalid Content-Type")

    if "otp" not in params or "clal" not in params:
        raise web.HTTPBadRequest(reason="Missing parameters")

    request.config_dict["bot"].dispatch("chunithm_login", params["otp"], params["clal"])
    return web.Response(
        text="""<h1>Success!</h1>
<h5>Check the bot's DMs to see if the account has been successfully linked.</h5>

<img src="https://chunithm-net-eng.com/mobile/images/pen_sleep_apng.png">
""",
        content_type="text/html",
    )


def init_app(bot: "ChuniBot") -> web.Application:
    app = web.Application()
    app.add_routes(router)
    app["bot"] = bot
    return app
