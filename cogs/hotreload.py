import os
import pathlib

import discord
from discord.ext import commands, tasks

# put your extension names in this list
# if you don't want them to be reloaded
IGNORE_EXTENSIONS = []


def path_from_extension(extension: str) -> pathlib.Path:
    return pathlib.Path(extension.replace(".", os.sep) + ".py")


class HotReload(commands.Cog):
    """
    Cog for reloading extensions as soon as the file is edited
    """

    def __init__(self, bot):
        self.bot = bot
        self.hot_reload_loop.start()

    def cog_unload(self):
        self.hot_reload_loop.stop()

    @tasks.loop(seconds=3)
    async def hot_reload_loop(self):
        for extension in list(self.bot.extensions.keys()):
            if extension in IGNORE_EXTENSIONS:
                continue
            path = path_from_extension(extension)
            time = os.path.getmtime(path)

            try:
                if self.last_modified_time[extension] == time:
                    continue
            except KeyError:
                self.last_modified_time[extension] = time

            try:
                # For d.py 2.0, await the next line
                await self.bot.reload_extension(extension)
            except commands.ExtensionError:
                print(f"Couldn't reload extension: {extension}")
            else:
                print(f"Reloaded extension: {extension}")
            finally:
                self.last_modified_time[extension] = time

    @hot_reload_loop.before_loop
    async def cache_last_modified_time(self):
        self.last_modified_time = {}
        # Mapping = {extension: timestamp}
        for extension in self.bot.extensions.keys():
            if extension in IGNORE_EXTENSIONS:
                continue
            path = path_from_extension(extension)
            time = os.path.getmtime(path)
            self.last_modified_time[extension] = time


async def setup(bot):
    cog = HotReload(bot)
    await bot.add_cog(cog)


# For d.py 2.0, comment the above setup function
# and uncomment the below
# async def setup(bot):
#     cog = HotReload(bot)
#     await bot.add_cog(cog)
