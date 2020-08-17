import discord
import asyncio
import aiohttp
import re
import json
import datetime
import time
import threading
import logging

from formatting import hformat
from typing import Optional
from discord.ext import tasks, commands

session = aiohttp.ClientSession()

streamingSites = [
    "Amazon",
    "AnimeLab",
    "Crunchyroll",
    "Funimation",
    "Hidive",
    "Hulu",
    "Netflix",
    "Viz",
    "VRV"
]

scheduleQuery = '''
query($page: Int = 0, $amount: Int = 50, $watched: [Int!]!, $nextDay: Int!) {
  Page(page: $page, perPage: $amount) {
    pageInfo {
      currentPage
      hasNextPage
    }
    airingSchedules(notYetAired: true, mediaId_in: $watched, sort: TIME, airingAt_lesser: $nextDay) {
      media {
        id
        siteUrl
        format
        duration
        episodes
        title {
          romaji
        }
        coverImage {
          large
          color
        }
        externalLinks {
          site
          url
        }
        studios(isMain: true) {
          edges {
            isMain
            node {
              name
            }
          }
        }
      }
      episode
      airingAt
      timeUntilAiring
      id
    }
  }
}
'''

searchAni = '''
query($name:String,$aniformat:MediaFormat){
    Page(perPage:5,page:1){
        media(search:$name,type:ANIME,format:$aniformat){
            title {
                romaji, 
                english
            },
            id,
            format,
            siteUrl
        }
    } 
}
'''

# Temporary watchlish
watchlist=[116006]

async def getschedule(self, _time_, page):
    q = await query(scheduleQuery, {"page": 1,"amount": 50, "watched": watchlist, "nextDay": _time_})
    q = q['data']
    channel = self.bot.get_channel(744528830382735421)
    if q['Page']['airingSchedules']:
        for e in q['Page']['airingSchedules']:
            self.logger.info(f"Scheduling {e['media']['title']['romaji']} episode {e['episode']} (about to air in {str(datetime.timedelta(seconds=e['timeUntilAiring']))})")
            async def queueSchedule(self):
                anime = e['media']['title']['romaji']
                eps = e['episode']
                sites = []
                for site in e['media']['externalLinks']:
                    if str(site['site']) in streamingSites:
                        sites.append(f"[{site['site']}]({site['url']})")
                sites = " | ".join(sites)

                embed = discord.Embed(title="New Release!",
                                    description=f"Episode {eps} of {anime} has just aired!")
                if sites:
                   embed.add_field(name="Streaming Sites",value=sites, inline=False)
                else:
                    embed.add_field(name="Streaming Sites",value="No official stream links available")
                await channel.send(embed=embed)
            await asyncio.sleep(e['timeUntilAiring'])
            await queueSchedule(self)

    if q['Page']['pageInfo']['hasNextPage']:
        getschedule(self, int(time.time() + (24 * 60 * 60 * 1000 * 1) / 1000 ), page+1)


async def query(query: str, variables: Optional[str]):
    if not query:
        return None
    async with session.post("https://graphql.anilist.co", json={'query': query, 'variables': variables}) as req:
        try:
            if (json.loads(await req.text())['errors']):
                return None
        except KeyError:
            return json.loads(await req.text())

async def find_id(self, ctx, url, _type_: None):
    # if input is ID, just return it, else find id via name (string)
    try:
        _id_ = int(url)
        return _id_
    except ValueError:
        _id_ = await find_with_name(self, ctx, url, _type_)
        if not _id_:
            return
        return str(_id_['Media']['id'])

    # regex for AniList and MyAnimeList
    regexAL = r"/anilist\.co\/anime\/(.\d*)/"
    regexMAL = r"/myanimelist\.net\/anime\/(.\d*)"
    
    # if AL link then return the id
    match = re.search(regexAL, url)
    if match:
        return match.group(1)
    
    # if MAL link get the id, find AL id out of MAL id then return the AL id
    match = re.search(regexMAL, url)
    if not match:
        return None
    q = await query("query($malId: Int){Media(idMal:$malId){id}}", {'malId': match.group(1)})
    if q is None:
        print("Error")
        return
    return q['data']['Media']['id']

async def getinfo(self, ctx, other, _format_: str=None):
    mediaId = await find_id(self, ctx, other, _format_)
    a = await query("query($mediaId: Int){Media(id:$mediaId)" +
            "{id, title {romaji, english}, episodes, status," +
            " startDate {year, month, day}, endDate {year, month, day}," +
            " genres, coverImage {large}, description, averageScore, studios{nodes{name}}, seasonYear, externalLinks {site, url} } }",
            {'mediaId' : mediaId})
    if a is None:
        return
    a = a['data']

    # Streaming Site
    sites = []
    for each in a['Media']['externalLinks']:
        if str(each['site']) in streamingSites:
            sites.append(f"[{each['site']}]({each['url']})")
    sites = " | ".join(sites)

    # Description
    desc = a['Media']['description']
    if desc is not None:
        for d in ["</i>","<i>","<br>"]:
            desc = desc.replace(d,"")
    else:
        desc = "No description."

    # English Title
    engTitle = a['Media']['title']['english']
    if engTitle is None:
        engTitle = a['Media']['title']['romaji']

    # Studio Name
    studios = []
    for studio in a['Media']['studios']['nodes']:
        studios.append(studio['name']) 
    studio = ", ".join(studios)

    # Year its aired/released
    seasonYear = a['Media']['seasonYear']
    if seasonYear is None:
        seasonYear = "Unknown"

    # Rating
    rating = a['Media']['averageScore']
    if rating is None:
        rating = "0"

    # Episodes
    eps = a['Media']['episodes']
    if eps is None:
        eps = "0"
    
    # Status
    stat = hformat(a['Media']['status'])

    embed = discord.Embed(
            title = f"{a['Media']['title']['romaji']}",
            url = f"https://anilist.co/anime/{a['Media']['id']}",
            description = f"**{engTitle} ({seasonYear})**\n{desc}\n\n**Studios**: {studio}",
            colour = discord.Colour(0x02A9FF)
            )
    embed.set_author(name="AniList",
                    icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png")
    embed.set_thumbnail(url=a['Media']['coverImage']['large'])
    embed.add_field(name="Average Score",value=f"{rating}/100",)
    embed.add_field(name="Episodes",value=f"{eps}")
    embed.add_field(name="Status",value=f"{stat}")
    genres = ", ".join(a['Media']['genres'])
    embed.add_field(name="Genres",value=genres, inline=False)
    if sites:
        embed.add_field(name="Streaming Sites",value=sites, inline=False)
    await ctx.send(embed=embed)
    return

async def search_ani(self, ctx, anime):
    q = await query(searchAni, {'name': anime})
    q = q['data']
    embed = discord.Embed(title="Top 5 Search Result",
                            colour = discord.Colour(0x02A9FF)
                            )
    embed.set_author(name="AniList",
                    icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png")
    if not q['Page']['media']:
        embed = discord.Embed(title="No Result Found",
                            colour = discord.Colour(0x02A9FF)
                            )
        embed.set_author(name="AniList",
                        icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png")
        await ctx.send(embed=embed)
        return
    for each in q['Page']['media']:
        engTitle = each['title']['english']
        if not engTitle:
            engTitle = "No english title."
        embed.add_field(name=f"[{each['format']}] {each['title']['romaji']}",
        value=f"**ID**: [{each['id']}]({each['siteUrl']})\n{engTitle}",
        inline=False)
    await ctx.send(embed=embed)

async def find_with_name(self, ctx, anime, _type_):
    if not _type_:
        q = await query("query($name:String){Media(search:$name,type:ANIME){id," +
            "title {romaji,english}, coverImage {large}, status, episodes, averageScore, seasonYear  } }",
            {'name': anime})
    else: 
        _type_ = str(_type_.upper())
        q = await query("query($name:String,$atype:MediaFormat){Media(search:$name,type:ANIME,format:$atype){id," +
            "title {romaji,english}, coverImage {large}, status, episodes, averageScore, seasonYear  } }",
            {'name': anime,'atype': _type_})
    try:
        return q['data']
    except TypeError:
        if not _type_:
            await ctx.send(f"{anime} not found")
            return None
        await ctx.send(f"{anime} with format {_type_} not found")
        return None

async def createAnnoucementEmbed(entry: str=None, date: str=None, upNext: str=None):
    print("Not usable yet.")

class AniList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.handle_schedule.start()
        self.logger = logging.getLogger('discord')

    def cog_unload(self):
        self.handle_schedule.cancel()

    @tasks.loop(hours=24)
    async def handle_schedule(self):
        self.logger.warning("Checking for new releases...")
        await getschedule(self, int(time.time() + (24 * 60 * 60 * 1000 * 1) / 1000 ), 1)

    @commands.command()
    async def anime(self, ctx, instruction: str="help", other: str=None, _format_: str=None):
        """**Instruction**: `help, info, search`\n**Other**: MyAnimeList or AniList URL/ID\n**Format**: Movie, TV, OVA, etc [Optional]"""
        if instruction == "help":
            embed = discord.Embed(
                    title = f"Help with anime",
                    description = f"` {ctx.prefix}anime <instruction> <other> <_format_>`",
                    colour = discord.Colour.green()
                    )
            embed.add_field(name="Command Description", value=f"{ctx.command.help}")
            await ctx.send(embed=embed)
            return
        if instruction == "info":
            if not other:
                return
            async with ctx.typing():
                await getinfo(self, ctx, other, _format_)
            return
        if instruction == "search" or instruction == "find":
            if not other:
                return
            async with ctx.typing():
                await search_ani(self, ctx, other)
                return
            return
        if instruction == "watch":
            await ctx.send("This command is not available yet.")
            return
        if instruction == "check":
            await getschedule(self, int(time.time() + (24 * 60 * 60 * 1000 * 1) / 1000 ), 1)
            return
        await ctx.send(f"There's no command called '{instruction}'!")
        return
        

def setup(bot):
    bot.add_cog(AniList(bot))

