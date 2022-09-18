from typing import final
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import showdown
from threading import Thread
import ast
import pygsheets

bo3s = []
tr = None
users = None
teams = None
abbvs = None

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
        draft,
        sheets,
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
        self.draft = draft
        self.sheets=sheets
    
    
    async def on_receive(self, room_id, inp_type, params):
        if inp_type == 'win':
            # print("ended")
            await self.save_replay(room_id)
    
    async def on_query_response(self, query_type, response):
        if(query_type == "savereplay"):
            # print("responded")
            id = response['id']
            if not self.draft:
                await replayer_finished_bracket(self.pre_str + id, self.message, self.channel, response['log'], self.sheets)
            else:
                await replayer_finished_draft(self.pre_str + id, self.channel, response['log'], self.sheets)
    
    async def on_connect(self):
        # print("connected")
        await self.join(self.battle)
    

def main():
    global users
    global teams
    global abbvs
    global tr
    load_dotenv()
    botID = (os.getenv("BOT_ID"))
    gc = pygsheets.authorize(service_account_env_var="G_JSON")
    si = 11
    sheets = {"Mackey": gc.open_by_url(os.getenv("MACKEY_SHEET")).worksheets()[si:], "Ross-Ade": gc.open_by_url(os.getenv("ROSSADE_SHEET")).worksheets()[si:], "Holloway": gc.open_by_url(os.getenv("HOLLOWAY_SHEET")).worksheets()[si:]}
    tr = gc.open_by_url(os.getenv("MACKEY_SHEET")).worksheet_by_title('Team Reference')
    users = tr.get_col(7)
    teams = tr.get_col(2)
    abbvs = tr.get_col(8)
    users = [u.lower().strip() for u in users]
    abbvs = [a.lower().strip() for a in abbvs]
    channelIDs = [a for a in os.getenv("CHANNEL_IDS").split(" ")]
    draft_dict=ast.literal_eval(os.getenv("DRAFT_LINKS_IDS"))
    bracket_dict=ast.literal_eval(os.getenv("BRACKET_LINKS_IDS"))
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
        
        if str(message.author.id) == botID or str(ch.id) not in channelIDs:
            return
        
        draft = False
        final_channel = ch
        if ch.id in draft_dict.keys():
            final_channel = client.get_channel(draft_dict[ch.id])
            draft = True
        
        elif ch.id in bracket_dict.keys():
            final_channel = client.get_channel(bracket_dict[ch.id])
        
        if "play.pokemonshowdown.com" in content:
            battle_id = content[content.index("battle-"):]
            client2 = ReplayClient(name=showdown_user, password=showdown_pass, battle=battle_id,
                        channel=final_channel, message=message, pre_str="https://replay.pokemonshowdown.com/", draft=draft, sheets=sheets)
            client2.start()
        elif "sports.psim.us" in content:
            battle_id = content[content.index("battle-"):]
            client2 = ReplayClient(name=showdown_user, password=showdown_pass, battle=battle_id,
                        channel=final_channel, message=message, pre_str="https://replay.pokemonshowdown.com/sports-", server_id="sports", draft=draft, sheets=sheets)
            client2.start()
        
    client.run(token)

async def replayer_finished_bracket(replay_link, msg, channel, log, sheets):
    global bo3s
    won = False
    score = 0
    log_lines = log.splitlines()
    # print(log_lines)
    user1 = log_lines[0][4:].lower()
    user2 = log_lines[1][4:].lower()
    if user1 > user2:
        temp = user1
        user1 = user2
        user2 = temp
    winner = log_lines[len(log_lines)-1][5:].lower()
    if winner == user1:
        score = 1
    elif winner == user2:
        score = -1
    else:
        await msg.channel.send("Could not find users for match, though replay is at\n" + replay_link)
        return
    if (user1, user2) in [(t[0], t[1]) for t in bo3s]:
        for t in bo3s:
            if t[0]==user1 and t[1]==user2:
                t[2].append(replay_link)
                t[3] += score
                if abs(t[3])*len(t[2])>=3:
                    won=True
                    final_score = f"2-{len(t[2])-2}"
                    replays_string = ""
                    for replay in t[2]:
                        replays_string+=f'\n{replay}'
                    bo3s.remove(t)
                break
    else:
        bo3s.append([user1, user2, [replay_link], score])
        
    if won:
        
        team1 = ""
        team2 = ""
        index1 = -1
        index2 = -1
        for i in range(len(users)):
            if users[i] == user1:
                index1 = i
            elif users[i] == user2:
                index2 = i
            if index1>=0 and index2>=0:
                break
        
        if index1 == -1:
            if index2 == -1:
                team1 = "Showdown User " + user1
                team2 = "Showdown User " + user2
            else:
                team2 = teams[index2]
        elif index2 == -1:
            team2 = "Showdown User " + user2
            team1 = teams[index1]
        else:
            team1 = teams[index1]
            team2 = teams[index2]
        
        if score > 0:
            final_str = f"Botfficial Bracket Result\n{team1} def. {team2} {final_score}{replays_string}"
        else:
            final_str = f"Botfficial Bracket Result\n{team2} def. {team1} {final_score}{replays_string}"
        await channel.send(final_str)

        
    
async def replayer_finished_draft(replay_link, channel, log, sheets):
    log_lines = log.splitlines()
    # print(log_lines)
    user1 = log_lines[0][4:].lower().strip()
    user2 = log_lines[1][4:].lower().strip()
    winner = log_lines[len(log_lines)-1][5:].lower().strip()
    index1 = -1
    index2 = -1
    
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
    
    for i in range(len(users)):
        if users[i] == user1:
            index1 = i
        elif users[i] == user2:
            index2 = i
        if index1>=0 and index2>=0:
            break
    
    if index1 == -1:
        if index2 == -1:
            team1 = "Showdown User " + user1
            team2 = "Showdown User " + user2
        else:
            team2 = teams[index2]
        division = "Unknown Division"
    elif index2 == -1:
        team2 = "Showdown User " + user2
        team1 = teams[index1]
        division = "Unknown Division"
    else:
        team1 = teams[index1]
        team2 = teams[index2]
        abbv1 = abbvs[index1]
        abbv2 = abbvs[index2]
        found1 = False
        found2 = False
        for div in sheets.keys():
            found1 = False
            found2 = False
            for w in sheets[div]:
                if w.title.lower().strip() == abbv1:
                    found1 = True
                if w.title.lower().strip() == abbv2:
                    found2 = True
                if found1 and found2:
                    break
            if found1 and found2:
                division = div
                break
    
    if(winner==user1):
        final_str = f"Botfficial Match Result ({division})\n{team1} def. {team2} {alive1}-{alive2}\n{replay_link}"
    elif(winner==user2):
        final_str = f"Botfficial Match Result ({division})\n{team2} def. {team1} {alive2}-{alive1}\n{replay_link}"
    else:
        final_str = f"ERROR - winner was {winner} but could not be identified as a player"
    await channel.send(final_str)

if __name__ == "__main__":
    main()
    
    
########  
#OLD CODE
########

# for div in sheets.keys():
    #     for w in sheets[div]:
    #         if w.rows > 5 and w.cols > 5 and user1 in str(w.cell('E4').value_unformatted).lower():
    #             team1 = str(w.cell('E1').value_unformatted)
    #             division = div
    #             found = True
    #             break
    #     if found:
    #         break
    
    # if not found:
    #     team1 = "Showdown User " + user1
    #     team2 = "Showdown User " + user2
    #     division = "Unidentified Division"
    # else:
    #     found2 = False
        
    #     for w in sheets[division]:
    #         if w.rows > 5 and w.cols > 5 and user2 in str(w.cell('E4').value_unformatted).lower():
    #             team2 = str(w.cell('E1').value_unformatted)
    #             found2 = True
    #             break
    #     if not found2:
    #         team2 = "Showdown User " + user2
    #         division = "Unidentified Division"
    