import asyncio
import discord
import json
import prettify_exceptions
import sys
import traceback

from .errors.fun import DiceTooBig
from discord.ext import commands


class ErrorHandler(commands.Cog):
    """Handle errors."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = self.bot.logger

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(
                f"The bot doesn't have `{missing_perms}` permission to do this command!"
            )

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                f"Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            )

        if isinstance(error, commands.CommandOnCooldown):
            bot_msg = await ctx.send(
                f"{ctx.message.author.mention}," + f" slowdown bud!"
            )
            await asyncio.sleep(round(error.retry_after))
            await bot_msg.delete()
            return

        if isinstance(error, commands.CommandInvokeError):
            _traceback = ''.join(prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__))
            self.bot.logger.error(f"Something went wrong! error: {error}\n{_traceback}")

            # Give details about the error
            # print(
            #     "Ignoring exception in command {}:".format(ctx.command), file=sys.stderr
            # )
            # print(_traceback, file=sys.stderr)

            # Send embed that when user react withh greenTick bot will send it to bot owner
            desc = (
                f"The command was unsuccessful because of this reason:\n```{error}```\n"
                + "React with <:greenTick:767209095090274325> to report the error to ZiRO2264#4572"
            )
            e = discord.Embed(
                title="Something went wrong!",
                description=desc,
                colour=discord.Colour(0x2F3136),
            )
            e.set_footer(text="Waiting for answer...", icon_url=ctx.author.avatar_url)
            msg = await ctx.send(embed=e)
            await msg.add_reaction("<:greenTick:767209095090274325>")

            def check(reaction, user):
                return (
                    user == ctx.author
                    and str(reaction.emoji) == "<:greenTick:767209095090274325>"
                )

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check
                )
            except asyncio.TimeoutError:
                e.set_footer(
                    text="You were too late to answer.", icon_url=ctx.author.avatar_url
                )
                await msg.edit(embed=e)
                await msg.clear_reactions()
            else:
                e_owner = discord.Embed(
                    title="Something went wrong!",
                    description=f"An error occured:\n```{error}```",
                    colour=discord.Colour(0x2F3136),
                )
                e_owner.add_field(name="Executor", value=ctx.author)
                e_owner.add_field(name="Message", value=ctx.message.content)
                e_owner.add_field(name="Guild", value=ctx.guild)
                bot_owner = self.bot.get_user(self.bot.master[0])
                await bot_owner.send(embed=e_owner)
                e.set_footer(
                    text=f"Error has been reported to {bot_owner}",
                    icon_url=ctx.author.avatar_url,
                )
                await msg.edit(embed=e)
                await msg.clear_reactions()

            return


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
