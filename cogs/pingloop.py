import discord

from discord.ext import tasks, commands


class Pingloop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # self.handle_schedule.start()

    def cog_unload(self):
        self.handle_schedule.cancel()

    def is_redarmy():
        def predicate(ctx):
            return ctx.author.guild_permissions.manage_channels

        return commands.check(predicate)

    @tasks.loop(seconds=3)
    async def handle_schedule(self):
        channel = self.bot.get_channel(755058568461418496)
        if channel.guild.id not in [747984453585993808, 745481731133669476]:
            self.handle_schedule.cancel()
            return
        await channel.send("@everyone")

    @commands.command()
    @is_redarmy()
    async def start_pingloop(self, ctx):
        if channel.guild.id not in [747984453585993808, 745481731133669476]:
            return
        if self.handle_schedule.is_running():
            return
        self.handle_schedule.start()
        await ctx.send(f"Pingloop started by {ctx.message.author.mention}.")

    @commands.command()
    @is_redarmy()
    async def stop_pingloop(self, ctx):
        if not self.handle_schedule.is_running():
            return
        self.handle_schedule.cancel()
        await ctx.send(f"Pingloop started by {ctx.message.author.mention}.")


def setup(bot):
    bot.add_cog(Pingloop(bot))