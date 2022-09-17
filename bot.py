import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import showdown
from threading import Thread
import ast
import pygsheets

class ReplayClient(showdown.Client):
    
    def __init__(
        self,
        name="",
        password="",
        *,
        loop=None,
        max_room_logs=5000,
        server_id="showdown",
        server_host=None,
        strict_exceptions=False,
        battle,
        channel,
        message,
        pre_str,
        detailed,
        sheets
    ):
        super().__init__(name=name, 
                         password=password,
                         loop=loop,
                         max_room_logs=max_room_logs,
                         server_id=server_id,
                         server_host=server_host,
                         strict_exceptions=strict_exceptions)
        self.battle = battle
        self.channel = channel
        self.message = message
        self.pre_str = pre_str
        self.detailed = detailed
        self.sheets=sheets
    
    
    async def on_receive(self, room_id, inp_type, params):
        if inp_type == 'win':
            print("ended")
            await self.save_replay(room_id)
    
    async def on_query_response(self, query_type, response):
        if(query_type == "savereplay"):
            print("responded")
            id = response['id']
            if not self.detailed:
                await replayer_finished_simple(self.pre_str + id, self.message)
            else:
                await replayer_finished_detailed(self.pre_str + id, self.channel, response['log'], self.sheets)
    
    async def on_connect(self):
        print("connected")
        await self.join(self.battle)
    

def main():
    load_dotenv()
    botID = int(os.getenv("BOT_ID"))
    gc = pygsheets.authorize(service_account_file="gsheets-key.json")
    si = 11
    sheets = {"Mackey": gc.open_by_url(os.getenv("MACKEY_SHEET")).worksheets()[si:], "Ross-Ade": gc.open_by_url(os.getenv("ROSSADE_SHEET")).worksheets()[si:], "Holloway": gc.open_by_url(os.getenv("HOLLOWAY_SHEET")).worksheets()[si:]}
    channelIDs = [int(a) for a in os.getenv("CHANNEL_IDS").split(" ")]
    draft_dict=ast.literal_eval(os.getenv("DRAFT_LINKS_IDS"))
    showdown_user = os.getenv("SHOWDOWN_USER")
    showdown_pass = os.getenv("SHOWDOWN_PASS")
    token = os.getenv("DISCORD_TOKEN")
    
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    bot = commands.Bot(command_prefix='.',intents=intents)
    
    

    @client.event
    async def on_ready():
        await client.change_presence(activity=discord.Game(name="Type '!pb help' for a DM with info about me!"))


    @client.event
    async def on_message(message):
        ch = message.channel
        content = message.content.strip()
        if content.lower().startswith("!pb ") and len(content)>4:
            content = content.lower()[4:]
            
            if content == "help":
                help_msg = "Hello! I'm the PUBA Helper bot, aimed at automating and aiding processes in the PUBA server."
                help_msg += "\nI track all links posted in #match-live-links or #bracket-live-links and save the replays."
                help_msg += "\nMore functionality hopefully coming soon!"
                await message.author.send(help_msg)
            
            
            return
        
        if message.author.id == botID or ch.id not in channelIDs:
            return
        
        detailed = False
        final_channel = ch
        if ch.id in draft_dict.keys():
            final_channel = client.get_channel(draft_dict[ch.id])
            detailed = True
        
        
        if "play.pokemonshowdown.com" in content:
            battle_id = content[content.index("battle-"):]
            client2 = ReplayClient(name=showdown_user, password=showdown_pass, battle=battle_id,
                        channel=final_channel, message=message, pre_str="https://replay.pokemonshowdown.com/", detailed=detailed, sheets=sheets)
            client2.start(autologin=False)
        elif "sports.psim.us" in content:
            battle_id = content[content.index("battle-"):]
            client2 = ReplayClient(name=showdown_user, password=showdown_pass, battle=battle_id,
                        channel=final_channel, message=message, pre_str="https://replay.pokemonshowdown.com/sports-", server_id="sports", detailed=detailed, sheets=sheets)
            client2.start(autologin=False)
        
    client.run(token)

async def replayer_finished_simple(replay_link, msg):
    # print("Replay at "+replay_link)
    await msg.reply("Replay: " + replay_link, mention_author=False)
    
async def replayer_finished_detailed(replay_link, channel, log, sheets):
    log_lines = log.splitlines()
    # print(log_lines)
    user1 = log_lines[0][4:].lower()
    user2 = log_lines[1][4:].lower()
    winner = log_lines[len(log_lines)-1][5:].lower()
    
    alive1 = 6
    alive2 = 6
    
    for line in log_lines:
        if "|faint|p1a" in line:
            alive1-=1
        if "|faint|p2a" in line:
            alive2-=1
    
    team1 = ""
    team2 = ""
    division = ""
    found = False
    for div in sheets.keys():
        for w in sheets[div]:
            if w.rows > 5 and w.cols > 5 and user1 in str(w.cell('E4').value_unformatted).lower():
                team1 = str(w.cell('E1').value_unformatted)
                division = div
                found = True
                break
        if found:
            break
    
    if not found:
        team1 = "Showdown User " + user1
        team2 = "Showdown User " + user2
        division = "Unidentified Division"
    else:
        found2 = False
        
        for w in sheets[division]:
            if w.rows > 5 and w.cols > 5 and user2 in str(w.cell('E4').value_unformatted).lower():
                team2 = str(w.cell('E1').value_unformatted)
                found2 = True
                break
        if not found2:
            team2 = "Showdown User " + user2
            division = "Unidentified Division"
    
    
    if(winner==user1):
        final_str = f"Botfficial Match Result ({division})\n{team1} def. {team2} {alive1}-{alive2}\n{replay_link}"
    elif(winner==user2):
        final_str = f"Botfficial Match Result ({division})\n{team2} def. {team1} {alive2}-{alive1}\n{replay_link}"
    else:
        final_str = f"ERROR - winner was {winner} but could not be identified as a player"
    await channel.send(final_str)

if __name__ == "__main__":
    main()