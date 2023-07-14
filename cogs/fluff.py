from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context

if TYPE_CHECKING:
    from bot import ChuniBot

class CbuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛐", style=discord.ButtonStyle.blurple, custom_id="cbucbucbu")
    async def cbucbucbu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.message is None or interaction.message.reference is None or interaction.channel is None:
            return
        
        message = interaction.channel.get_partial_message(interaction.message.reference.message_id)

        await message.reply(
            "https://cdn.discordapp.com/emojis/1093540495818502164.gif",
            mention_author=False,
            view=CbuView(),
        )


class FluffCog(commands.Cog, name="Fluff"):
    def __init__(self) -> None:
        super().__init__()

    @commands.command("unny")
    async def cunny(self, ctx: Context):
        """😭"""

        if (
            ctx.message.reference is not None
            and ctx.message.reference.message_id is not None
        ):
            reference = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
        else:
            reference = ctx.message

        await reference.reply(
            "https://cdn.discordapp.com/attachments/1041530799704526961/1110813221008441375/uohhhroll.gif",
            mention_author=False,
        )

    @commands.command("bu")
    @commands.check(lambda x: x.author.id != 204553051007090688)
    async def bu(self, ctx: Context):
        """🛐"""

        if (
            ctx.message.reference is not None
            and ctx.message.reference.message_id is not None
        ):
            reference = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
        else:
            reference = ctx.message

        await reference.reply(
            "https://cdn.discordapp.com/emojis/1093540495818502164.gif",
            mention_author=False,
            view=CbuView(),
        )


async def setup(bot: "ChuniBot"):
    await bot.add_cog(FluffCog())
