from discord.ext import commands, tasks
from discord.utils import get
from datetime import timedelta
import discord
import requests
import json
import asyncio
import dateutil.parser

def checklevel(cat):
    status = json.loads(requests.get(f"https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/category/{cat}").text)
    try:
        if status['status'] == 404:
            return True
    except KeyError:
        return False

# Time formatting from speedrunbot
def realtime(time): # turns XXX.xxx into h m s ms
    ms = int(time*1000)
    s,ms = divmod(ms,1000)
    m,s = divmod(s,60)
    h,m = divmod(m,60)  # separates time into h m s ms
    ms = "{:03d}".format(ms)
    s = "{:02d}".format(s)  #pads ms and s with0s
    if h>0:
        m = "{:02d}".format(m)  #if in hours, pad m with 0s
    return ((h>0) * (str(h)+'h ')) + str(m)+'m ' + str(s)+'s ' + ((str(ms)+'ms') * (ms!='000')) #src formatting 

async def worldrecord(self, ctx, category: str="Any"):
    head = {"Accept": "application/json", "User-Agent": "ziBot/0.1"}
    game = "mcbe"

    # Text formating (Any% Glitchless -> any_glitchless)
    cat = category.replace(" ","_")
    for char in "%()":
        cat = cat.replace(char,"")
    
    # Output formating
    wrs = {
            'cat': '',
            'platform': '',
            'runner': '',
            'link': '',
            'time': ''
            }
    platformsVar = json.loads(requests.get(
            f"https://www.speedrun.com/api/v1/variables/38dj2ex8",
            headers=head).text)
    platforms = platformsVar['data']['values']['choices']

    # Check if ILs
    level = checklevel(cat)
    if level is True:
        _type_ = 'level'
        catURL = f'{cat}/9kv7jy8k'
    else:
        _type_ = 'category'
        catURL = cat
    catName = json.loads(requests.get(
        f"https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/{_type_}/{catURL}?embed={_type_}",
        headers=head).text)['data'][f'{_type_}']['data']['name']
    if level is True:
        catName += " Any%"

    # Grab and Put Category Name to embed title
    wrs['cat']=catName
    embed = discord.Embed(
            title=f"{wrs['cat']} MCBE World Records",
            colour=discord.Colour.gold()
            )

    # Get WRs from each platforms (PC, Mobile, Console) then send to chat
    for platform in platforms:
        wr = json.loads(requests.get(
            "https://www.speedrun.com/api/v1/leaderboards/"+
            f"yd4ovvg1/{_type_}/{catURL}?top=1&var-38dj2ex8={platform}",
            headers=head).text)
        wrData = json.loads(requests.get(
                "https://www.speedrun.com/api/v1/runs/"+
                f"{wr['data']['runs'][0]['run']['id']}"+
                "?embed=players,level,platform",
                headers=head).text)['data']
        wrs['platform']=platforms[platform]
        if wrData['players']["data"][0]['rel'] == 'guest':
            wrs['runner']=wrData['players']['data'][0]['names']
        else:
            wrs['runner']=wrData['players']["data"][0]["names"]["international"]
        wrs['link']=wrData['weblink']
        wrs['time']=realtime(wrData['times']['realtime_t'])
        embed.add_field(name=f"{wrs['platform']}",value=f"{wrs['runner']} ({wrs['time']})",inline=False)
    await ctx.send(embed=embed)

async def pendingrun(self, ctx):
    mcbe_runs = 0
    mcbeil_runs = 0
    mcbece_runs = 0
    head = {"Accept": "application/json", "User-Agent": "ziBot/0.1"}
    gameID = 'yd4ovvg1' # MCBE's gameid
    gameID2 = 'v1po7r76' # MCBE CE's gameid
    runsRequest = requests.get(
            f'https://www.speedrun.com/api/v1/runs?game={gameID}&status=new&max=200&embed=category,players,level&orderby=submitted',
            headers=head)
    runs = json.loads(runsRequest.text)
    runsRequest2 = requests.get(
            f'https://www.speedrun.com/api/v1/runs?game={gameID2}&status=new&max=200&embed=category,players,level&orderby=submitted',
            headers=head)
    runs2 = json.loads(runsRequest2.text)

    for game in range(2):
        for i in range(200):
            leaderboard = ''
            level = False
            try:
                for key, value in runs['data'][i].items():
                    if key == 'id':
                        run_id = value
                    if key == 'weblink':
                        link = value
                    if key == 'level':
                        if value['data']:
                            level = True
                            categoryName = value['data']['name']
                    if key == 'category' and not level:
                        categoryName = value["data"]["name"]
                    if key == 'players':
                        if value["data"][0]['rel'] == 'guest':
                            player = value["data"][0]['name']
                        else:
                            player = value["data"][0]["names"]["international"]
                    if key == 'times':
                        rta = timedelta(seconds=value['realtime_t'])
                    if key == 'submitted':
                        timestamp = dateutil.parser.isoparse(value)
            except IndexError:
                break
            if game == 0:
                if level is True:
                    mcbeil_runs += 1
                    leaderboard = 'Individual Level Run'
                else:
                    mcbe_runs += 1
                    leaderboard = "Full Game Run"
            elif game == 1:
                leaderboard = "Category Extension Run"
                mcbece_runs += 1
            embed = discord.Embed(
                        title=leaderboard,
                        url=link,
                        description=
                        f"{categoryName} in `{str(rta).replace('000','')}` by **{player}**",
                        color=16711680 + i * 60,
                        timestamp=timestamp)
            await self.bot.get_channel(741199490391736340).send(embed=embed)
    runs = runs2
    gameID = gameID2
    total = mcbe_runs + mcbece_runs + mcbeil_runs
    embed_stats = discord.Embed(
                title='Pending Run Stats',
                description=
                f"Full Game Runs: {mcbe_runs}\nIndividual Level Runs: {mcbeil_runs}\nCategory Extension Runs: {mcbece_runs}\n**Total: {total}**",
                color=16711680 + i * 60)
    await self.bot.get_channel(741199490391736340).send(embed=embed_stats)

# Cog commands
class Src(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def pending(self, ctx):
        """Get pending runs from speedun.com"""
        async with ctx.typing():
            await self.bot.get_channel(741199490391736340).purge(limit=500)
            await pendingrun(self, ctx)
    
    @commands.command()
    async def wrs(self, ctx, category: str="any"):
        """Get mcbe world record runs from speedun.com
        `e.g. >wrs "Any% Glitchless"`"""
        async with ctx.typing():
            await worldrecord(self, ctx, category)

def setup(bot):
    bot.add_cog(Src(bot))
