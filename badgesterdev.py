import disnake, aiohttp, asyncio, aiofiles, aiofiles.os
from disnake.ext import commands
from collections import Counter
from datetime import datetime
from config import devservers, devids, bottoken, roblosecurity
import ijson, json, time

intents = disnake.Intents.default()
intents.message_content = True

tasks = {}

e = {"mag": "https://em-content.zobj.net/source/whatsapp/352/magnifying-glass-tilted-left_1f50d.png", "pensive": "https://em-content.zobj.net/source/apple/354/pensive-face_1f614.png", "scroll": "https://em-content.zobj.net/source/apple/354/dvd_1f4c0.png", "link": "https://em-content.zobj.net/source/apple/354/link_1f517.png"}

squarebadgelist = json.loads(open("squarebadges.json").read())
valuablelist = json.loads(open("valuableids.json").read())

async def upload_list(filename):
    data = aiohttp.FormData()
    
    file = await aiofiles.open(filename, "rb")
    data.add_field('fileToUpload', file, filename=filename)
    for key, value in {'reqtype': 'fileupload', 'userhash': ''}.items():
        data.add_field(key, str(value))
    
    async with aiohttp.ClientSession() as session:
        response = await session.post("https://catbox.moe/user/api.php", data=data) 
        return (await response.text())

async def find_badges(namesearch: list = [], descriptionsearch: list = [], gamesearch: list = [], disabledbadges: bool = False, squareonly: bool = False, legacyonly: bool = True):
    real = {}
    async with aiofiles.open("badges.json", "r") as f:
        async for record in ijson.items(f, "item"):
            if type(record['id']) == int and record['id'] <= 2124945818 or not legacyonly:
                if record['enabled'] and record["awardingUniverse"]["rootPlaceId"] and record["statistics"]["awardedCount"] > 1 or disabledbadges and record["awardingUniverse"]["rootPlaceId"] and record["awardingUniverse"]["name"]:
                    if not squareonly or squareonly and record["id"] in squarebadgelist:
                        badgename = record['name'].lower()
                        badgedescription = record['description'].lower() if record['description'] else ""
                        badgegame = record['awardingUniverse']['name'].lower()
                        
                        r = []

                        for l in [(badgename,namesearch),(badgedescription,descriptionsearch),(badgegame, gamesearch)]:
                            rr = []
                            string = l[0]
                            for filt in l[1]:
                                if filt.startswith("-"):
                                    filt = filt[1:]
                                    if filt in string: 
                                        rr = [False]
                                        break
                                elif len(filt.split('"')) > 2:
                                    filt = filt.split('"')[1]
                                    rr.append(any(filt == word for word in string.split()))
                                    rr.append(filt == string)
                                else:
                                    rr.append(filt in string)
                            if len(rr) != 0:
                                r.append(any(rr))
                            else:
                                r.append(False)

                        if all(r):
                            real[record["id"]] = {"placeid": record['awardingUniverse']["rootPlaceId"], "badgename": record['name'], "universeid": record["awardingUniverse"]["id"], "placename": record["awardingUniverse"]["name"]}
    return real

bot = commands.Bot(intents=intents, command_prefix="badgester!")

@bot.event
async def on_ready():
    print(f'Logged in {bot.user} | {bot.user.id}')

@bot.slash_command(name="ping", description="pong!")
async def ping(inter):
    await inter.response.send_message(":wave:")

async def detailedinfo(session, badgelist):
    t1 = time.time()
    rq = await session.get(f"https://games.roblox.com/v1/games/multiget-playability-status?" + "&universeIds=".join(map(str, [datt["universeid"] for datt in badgelist.values()])))
    if rq.status != 200:
        print(f"detailed {time.time()} errored {rq.status}")
        await asyncio.sleep(20)
        return (await detailedinfo(session, badgelist))
    else:
        badgelist_copy = badgelist.copy()
        js = await rq.json()
        for place in js:
            if place["isPlayable"] == True:
                for badge, badgedata in badgelist.items():
                    if badgedata["universeid"] == place["universeId"]:
                        del badgelist_copy[badge]
                        break

        t2 = time.time()
        print(f"detailed: {t2-t1}")
        return badgelist_copy


async def checkforuser(session, badgelist, userid):
    t1 = time.time()
    badge_ids = ','.join(str(badge_id) for badge_id in badgelist.keys())
    url = f"https://badges.roproxy.com/v1/users/{userid}/badges/awarded-dates?badgeIds={badge_ids}"
    
    response = await session.get(url)
    if response.status != 200:
        print(f"User {userid} error {response.status}")
        await asyncio.sleep(20)
        return await checkforuser(session, badgelist, userid)
    
    badgelist_copy = badgelist.copy()
    data = await response.json()
    awarded_badge_ids = [item.get("badgeId") for item in data.get("data", [])]
    for badge_id in awarded_badge_ids:
        if badge_id in badgelist_copy:
            del badgelist_copy[badge_id]
    
    t2 = time.time()
    print(f"User: {userid} Time taken: {t2 - t1}")
    return badgelist_copy



async def checkforvaluabl(session, badgelist):
        t1 = time.time()
        args = "?badgeIds="
        nonbadgeid = []
        vals = []
        for badgeid,badgedata in badgelist.items():
            if badgeid > 2154061671:
                nonbadgeid.append(str(badgeid))
            if badgeid in valuablelist or badgeid <=2124945818:
                vals.append(badgeid)
        if len(nonbadgeid) != 0:
            args = f"{args}{','.join(nonbadgeid)}"
            rq = await session.get(f"https://bor-valuable-badge-database-production.up.railway.app/api/v3/query/bybadgeids{args}")
            if rq.status != 200:
                print(f" valu {time.time()} errored {rq.status}")
                await asyncio.sleep(20)
                return (await checkforvaluabl(session, badgelist))
            else:
                js = await rq.json()
                for place in js["data"]:
                    if place.get("value") != 0:
                        vals.append(place.get("badge_id"))
        
        newbadgelist = {}
        for val in vals:
            newbadgelist[val] = badgelist[val]
                        
        t2 = time.time()
        print(f"valua: {t2-t1}")
        return newbadgelist

async def get_user(username: str = "", userid: int = 0):
    body = {"excludeBannedUsers": False}
    url = "https://users.roblox.com/v1/"
    if username != "":
        body["usernames"] = [username]
        url = "https://users.roblox.com/v1/usernames/users"
    elif userid != 0:
        body["userIds"] = [userid]
        url = "https://users.roblox.com/v1/users"
    
    async with aiohttp.ClientSession() as session:
        r = await session.post(url, json=body)
        status = r.status
        if status != 200:
            print(f"get_user {status}")
            await asyncio.sleep(5)
            return (await get_user(username, userid))
        else:
            js = await r.json()
            if len(js.get("data")) == 0:
                return None
            else:
                return js.get("data")[0]

async def searcher(inter, badgenamelist,badgedesclist,gamenamelist,userid,value,squareonly,includedisabled,detailed,forceupload):
    global tasks
    x = ", "
    new = "\n"
    
    newbadgenamelist = []
    for word in badgenamelist.split(","):
        if word == '' or word == "-" or word == '""':
            pass
        else:
            try:
                newbadgenamelist.append(word.lower())
            except:
                newbadgenamelist.append(word)
    newbadgedesclist = []
    for word in badgedesclist.split(","):
        if word == '' or word == "-" or word == '""':
            pass
        else:
            try:
                newbadgedesclist.append(word.lower())
            except:
                newbadgedesclist.append(word)
    newgamenamelist  = []
    for word in gamenamelist.split(","):
        if word == '' or word == "-" or word == '""':
            pass
        else:
            try:
                newgamenamelist.append(word.lower())
            except:
                newgamenamelist.append(word)
    
    if len(newbadgenamelist) == 0 and newbadgedesclist == 0 and newgamenamelist == 0:
        await inter.response.send_message("No search prompt?", ephemeral=True)
        return
    
    user = None
    if userid != "":
        try:
            user = await get_user(int(userid))
        except:
            user = await get_user(userid)
        
        if user == None:
            await inter.response.send_message("Invalid userid/username?", ephemeral=True)
            return
        excl = f" excluding owned badges for {user['name']}({user['id']})"
    
    
    embed = disnake.Embed(colour=0x2f3136)
    embed.timestamp = datetime.fromtimestamp(time.time()+15)
    footertext = f"Searching for {'Square ' if squareonly else ''}{'disabled ' if includedisabled else ''}{value} badges"
    if userid != "":
        footertext = f"{footertext}{excl if userid != 0 else ''}"
    if detailed:
        footertext = f"{footertext} and hiding private/deleted games"
    badgenamelisttext = f"> 🏷️ - `{','.join(newbadgenamelist)}`"
    badgedesclisttext = f"> 📄 - `{','.join(newbadgedesclist)}`"
    gamenamelisttext = f"> 🎲 - `{','.join(newgamenamelist)}`"
    
    if len(newbadgenamelist) != 0:
        footertext = f"{footertext}{new}{badgenamelisttext}"
    if len(newbadgedesclist) != 0:
        footertext = f"{footertext}{new}{badgedesclisttext}"
    if len(newgamenamelist) != 0:
        footertext = f"{footertext}{new}{gamenamelisttext}"
    
    embed.set_footer(text=footertext, icon_url=e.get("mag"))
    
    await inter.response.send_message(embed=embed)
    message = await inter.original_response()
    
    tasks[message.id] = {"user": message.author.id, "status": "getting badges", "do": True, "progress": "", "message": message, "interaction": inter}
    
    badgelist = await find_badges(newbadgenamelist,newbadgedesclist,newgamenamelist,squareonly,includedisabled,legacyonly=True if value=="Legacy" else False)
    #badgelist = await asyncio.get_event_loop().run_in_executor(executor = None, func=functools.partial(find_badges, whitelist = whitelisted, blacklist = blacklisted, gamesearch = whitelistedgames, blackgamesearch = blacklistedgames, disabledbadges = includedisabled, squareonly=squareonly, legacyonly=True if value=="Legacy" else False))

    if len(badgelist) == 0:
        tasks[message.id]["status"] = "no badges found"
        embed.set_footer(text="No badges found", icon_url=e.get("pensive"))
        embed.timestamp = None
        await message.reply(content=f"{inter.author.mention}",embed=embed)
        return

    filename = f"{round(time.time())}.txt"
    
    newlist = {}
    if detailed or userid != "" or value != "Legacy":
        keys = list(badgelist.keys())
        gamelist = [keys[i:i+100] for i in range(0, len(keys), 100)]

        embed.timestamp = datetime.fromtimestamp(time.time())
        embed.set_footer(text="Getting more information...", icon_url=e["mag"])
        progressmessage = await message.reply(embed=embed)
        tasks[message.id]["status"] = "getting more information"
        i = 0
        async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": roblosecurity}) as session:
            for games in gamelist:
                if tasks[message.id]["do"] != True:
                    embed.timestamp = None
                    embed.set_footer(text="Bye bye", icon_url=e["pensive"])
                    await message.reply(content=f"{inter.author.mention}",embed=embed)
                    return
                    
                i+=1
                taskss = []
                okgamelist = {key: badgelist[key] for key in games}
                counter = Counter()
                tttt1 = time.time()
                if detailed:
                    taskss.append(detailedinfo(session, okgamelist))
                    
                if user != None:
                    taskss.append(checkforuser(session, okgamelist, user['id']))
                
                if value != "Legacy":
                    taskss.append(checkforvaluabl(session, okgamelist))

                ttasks = await asyncio.gather(*taskss)
                for result in ttasks:
                    counter.update(set(result))
                result_dict = dict(counter)

                for badgeid,matches in result_dict.items():
                    if matches == len(ttasks):
                        newlist[badgeid] = badgelist[badgeid]
                
                tasks[message.id]["progress"] = f"{i}/{len(gamelist)}"
                tttt2 = time.time()
                if i >= 5:
                    i = 0
                    embed.set_footer(text=f"Getting more information... ({i}/{len(gamelist)})", icon_url=e["mag"])
                    embed.timestamp = datetime.fromtimestamp(time.time()+((tttt2-tttt1)*(len(gamelist)-i)))
                    await progressmessage.edit(embed=embed)
            badgelist = newlist

    async with aiofiles.open(filename, "wb") as out:
        for badgeid,badgedata in badgelist.items():
            await out.write(f"{badgedata.get('badgename')} | https://www.roblox.com/badges/{badgeid} | {badgedata.get('placename')}: https://www.roblox.com/games/{badgedata.get('placeid')}\n".encode(encoding='utf-8'))
    
    embed.timestamp = None
    try:
        if forceupload:
            link = await upload_list(filename)

            embed.set_footer(text=f'Found {len(badgelist)} badges!', icon_url=e["link"])
            await message.reply(f'{inter.author.mention} {link}', embed=embed)
        else:
            embed.set_footer(text=f'Found {len(badgelist)} badges!', icon_url=e["scroll"])
            await message.reply(f'{inter.author.mention}', embed=embed, file=disnake.File(filename))
    except:
        link = await upload_list(filename)
    
        embed.set_footer(text=f'Found {len(badgelist)} badges!', icon_url=e["link"])
        await message.reply(f'{inter.author.mention} {link}', embed=embed)
            
    await aiofiles.os.remove(filename)
    tasks[message.id]["status"] = "done"


@bot.slash_command(name="search", description="search badges")
async def search(inter, 
badgesearch: str = commands.Param(default="",name="badge_name",description='Search in badge names: (hi,"chat",-bye)'), 
descriptionsearch: str = commands.Param(default="",name="badge_description",description="Search in badge descriptions"), 
gamesearch: str = commands.Param(default="",name="game_name",description='Search in game names'), 
userid: str = commands.Param(name="user_id", description="Hides owned badges", default=""),
value: str = commands.Param(name="value", choices=["Legacy", "Valuable", "Free"], description="[Default = Legacy]", default="Legacy"), 
squareonly: bool = commands.Param(name="square_only", choices=[True, False], description="[Default = False] | Works for legacy badges only", default=False), 
includedisabled: bool = commands.Param(name="include_disabled", choices=[True, False], description="[Default = False]", default=False), 
detailed: bool = commands.Param(name="hide_private_games", choices=[True, False], description="[Default = False] !! WILL TAKE MORE TIME !!", default=False), 
forceupload: bool = commands.Param(name="force_upload", choices=[True, False], description="[Default = False] Uploads output to the catbox.moe", default=False),

):
    await searcher(inter, badgesearch,descriptionsearch,gamesearch,userid,value,squareonly,includedisabled,detailed,forceupload)

@bot.slash_command(name="tasks", description="tasks list (dev only)", guild_ids=devservers)
async def taskscmd(inter):
    if inter.author.id not in devids:
        await inter.response.send_message("nuh uh", ephemeral=True)
        return
    msg = ""
    for taskid,task in tasks.items():
        msg = f"{msg}\n{task['interaction'].author.mention} {task['message'].jump_url} {task['status']} {task['progress']}"
    try:
        await inter.response.send_message(msg, ephemeral=True)
    except:
        async with aiofiles.open("tasks.txt", "wb") as out:
            await out.write(f"{msg}".encode(encoding='utf-8'))
        await inter.response.send_message(file=disnake.File("tasks.txt"), ephemeral=True)
        await aiofiles.os.remove("tasks.txt")
    

async def autocomp_tasks(inter: disnake.ApplicationCommandInteraction, user_input: str):
    return [str(lang) for lang in tasks]

@bot.slash_command(name="canceltask", description="cancel your search task using message id")
async def cancelcmd(inter, messageid: str = commands.Param(autocomplete=autocomp_tasks)):
    global tasks
    if inter.author.id !=  tasks[int(messageid)]["interaction"].author.id and inter.author.id not in devids:
        await inter.response.send_message("nuh uh", ephemeral=True)
        return
    tasks[int(messageid)]["do"] = False
    tasks[int(messageid)]["status"] = "canceled"
    await inter.response.send_message(f"canceled {tasks[int(messageid)]['message'].jump_url} {tasks[int(messageid)]['interaction'].author.mention} <:dave:1180190285268013106>", ephemeral=True)

bot.run(bottoken)