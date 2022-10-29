from typing import final
from xml.dom.pulldom import parseString
import discord
import signal
from discord.ext import commands
import os
from dotenv import load_dotenv
import showdown
from threading import Thread
import ast
import pygsheets
from datetime import datetime, timedelta
import signal
import time
import sys

draft_tracking = True
bracket_matches = []
bracket_series = None
bracket_needed_to_win = 0
bracket_tracking = True
tr = None
users = None
teams = None
abbvs = None
recents = []
storage = None
officer_role_id = None
dev_id = None

class GracefulKiller:
  def __init__(self):
    signal.signal(signal.SIGTERM, self.exit_gracefully)
    self.kill_now = False

  def exit_gracefully(self, *args):
    closing_save()
    self.kill_now = True
    sys.exit()

def showdown_format(in_str):
    return (''.join(ch for ch in in_str if ch.isalnum())).lower().strip()

def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start




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
        global recents
        if(query_type == "savereplay"):
            # print("responded")
            #print(response['log'])
            id = response['id']
            if id in recents:
                return
            
            recents.append(id)
            if len(recents) > 20:
                recents.pop(0)
                
            id = self.battle[7:]    
            
            if not self.draft:
                await replayer_finished_bracket(self.pre_str + id, self.message, self.channel, response['log'], self.sheets)
            else:
                await replayer_finished_draft(self.pre_str + id, self.channel, response['log'], self.sheets)
            await self.leave(self.battle)
        
    async def on_login(self, login_response):
        await super().on_login(login_response)
        await self.join(self.battle)
    

def main():
    global users
    global teams
    global abbvs
    global tr
    global bracket_series
    global storage
    global bracket_tracking
    global bracket_needed_to_win
    global officer_role_id
    global dev_id
    load_dotenv()
    gk = GracefulKiller()
    botID = (os.getenv("BOT_ID"))
    gc = pygsheets.authorize(service_account_env_var="G_JSON")
    si = 11
    sheets = {"Mackey": gc.open_by_url(os.getenv("MACKEY_SHEET")).worksheets()[si:], "Ross-Ade": gc.open_by_url(os.getenv("ROSSADE_SHEET")).worksheets()[si:], "Holloway": gc.open_by_url(os.getenv("HOLLOWAY_SHEET")).worksheets()[si:]}
    tr = gc.open_by_url(os.getenv("MACKEY_SHEET")).worksheet_by_title('Team Reference')
    users = tr.get_col(7)
    teams = tr.get_col(2)
    abbvs = tr.get_col(8)
    users = [showdown_format(u) for u in users]
    abbvs = [a.lower().strip() for a in abbvs]
    channelIDs = [a for a in os.getenv("CHANNEL_IDS").split(" ")]
    draft_dict=ast.literal_eval(os.getenv("DRAFT_LINKS_IDS"))
    bracket_dict=ast.literal_eval(os.getenv("BRACKET_LINKS_IDS"))
    showdown_user = os.getenv("SHOWDOWN_USER")
    showdown_pass = os.getenv("SHOWDOWN_PASS")
    token = os.getenv("DISCORD_TOKEN")
    officer_role_id=ast.literal_eval(os.getenv("OFFICER_ID"))
    dev_id=ast.literal_eval(os.getenv("DEV_ID"))
    
    storage = gc.open_by_url(os.getenv("STORAGE_URL")).worksheet_by_title('Storage')
    # bracket_series = os.getenv("BO3_TRACKING").strip().upper() == "T"
    draft_tracking = storage.get_value("A2").strip().upper() == "T"
    bracket_tracking = storage.get_value("B2").strip().upper() == "T"
    bracket_needed_to_win = int((str(storage.get_value("C2"))).strip())
    bracket_series = bracket_needed_to_win > 1
    # print(f"{bracket_series}   {bracket_tracking}   {bracket_needed_to_win}")
    
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    bot = commands.Bot(command_prefix='.',intents=intents)
    
    def is_admin(person):
        return person.id == dev_id or officer_role_id in [role.id for role in person.roles]

    @client.event
    async def on_ready():
        await client.change_presence(activity=discord.Game(name="Type '!pb help' for a DM with info about me!"))


    @client.event
    async def on_message(message):
        global bracket_tracking
        global draft_tracking
        global bracket_needed_to_win
        global bracket_series
        if str(message.author.id) == botID:
            return
        ch = message.channel
        content = message.content.strip()
        if content.lower().startswith("!pb ") and len(content)>4:
            content = content.lower()[4:]
            command = ""
            param = ""
            if content == "help":
                help_msg = "Hello! I'm the PUBA Helper bot, aimed at automating and aiding processes in the PUBA server."
                help_msg += "\nI track all links posted in #match-live-links or #bracket-live-links and save the replays."
                help_msg += "\nMore functionality hopefully coming soon!"
                await message.author.send(help_msg)
            elif content == "get-bracket-tracking":
                if bracket_tracking:
                    await message.reply("Bracket tracking is currently ON.")
                else:
                    await message.reply("Bracket tracking is currently OFF.")
            elif content == "get-draft-tracking":
                if draft_tracking:
                    await message.reply("Draft tracking is currently ON.")
                else:
                    await message.reply("Draft tracking is currently OFF.")
            elif content == "get-bracket-wins-needed":
                await message.reply(f"Bracket is first to {bracket_needed_to_win} wins.")
            elif len(content.split()) > 1:
                command = content.split()[0].lower().strip()
                param = content.split()[1].lower().strip()
            else:
                return
            
            if command == "set-bracket-tracking":
                if not is_admin(message.author):
                    await message.reply("Sorry, only admins can use this command!")
                elif param == "off":
                    bracket_tracking = False
                    await message.reply("Bracket tracking has been set to OFF.")
                elif param == "on":
                    bracket_tracking = True
                    await message.reply("Bracket tracking has been set to ON.")
                else:
                    await message.reply("Sorry, the only valid options for this command are 'off' and 'on'.")
                
            elif command == "set-draft-tracking":
                if not is_admin(message.author):
                    await message.reply("Sorry, only admins can use this command!")
                elif param == "off":
                    draft_tracking = False
                    await message.reply("Draft tracking has been set to OFF.")
                elif param == "on":
                    draft_tracking = True
                    await message.reply("Draft tracking has been set to ON.")
                else:
                    await message.reply("Sorry, the only valid options for this command are 'off' and 'on'.")
            
            elif command == "set-bracket-wins-needed":
                if not is_admin(message.author):
                    await message.reply("Sorry, only admins can use this command!")
                elif param.isdigit() and int(param) > 0 and int(param) < 10:
                    bracket_needed_to_win = int(param)
                    bracket_series = bracket_needed_to_win > 1
                    await message.reply(f"Bracket is now first to {param} wins.")
                else:
                    await message.reply("Sorry, the parameter for this command needs to be a reasonably sized positive number.")
            
            return
        
        if str(ch.id) not in channelIDs:
            return
        
        draft = False
        final_channel = ch
        if draft_tracking and ch.id in draft_dict.keys():
            final_channel = client.get_channel(draft_dict[ch.id])
            draft = True
        
        elif bracket_tracking and ch.id in bracket_dict.keys():
            final_channel = client.get_channel(bracket_dict[ch.id])
        
        else:
            return
        
        if "play.pokemonshowdown.com" in content.lower() and "replay." not in content.lower():
            new_cont = content.split(" ")
            for c in new_cont:
                if "play.pokemonshowdown.com" in c.lower():
                    battle_id = c[c.index("battle-"):]
                    break
            
            client2 = ReplayClient(name=showdown_user, password=showdown_pass, battle=battle_id,
                        channel=final_channel, message=message, pre_str="https://replay.pokemonshowdown.com/", draft=draft, sheets=sheets)
            client2.start(autologin=True)
        elif "sports.psim.us" in content.lower():
            new_cont = content.split(" ")
            for c in new_cont:
                if "sports.psim.us" in c.lower():
                    battle_id = c[c.index("battle-"):]
                    
            client2 = ReplayClient(name=showdown_user, password=showdown_pass, battle=battle_id,
                        channel=final_channel, message=message, pre_str="https://replay.pokemonshowdown.com/sports-", server_id="sports", draft=draft, sheets=sheets)
            client2.start(autologin=True)        
    client.run(token)
    
    
def get_users_winner(log_lines):
    #print(log_lines)
   
    user2 = showdown_format(log_lines[1][4:])
    winner = "unknown"
    for line in log_lines:
        line2 = line.lower().strip()
        if line2.startswith("|player|p1|"):
             user1 = showdown_format(line2[11:line2.find("|", 11)])
        elif line2.startswith("|player|p2|"):
             user2 = showdown_format(line2[11:line2.find("|", 11)])
        elif line2.startswith("|win|"):
            winner = showdown_format(line2[5:])
    return user1, user2, winner

def get_teams_mons_division(log_lines, user1, user2, sheets):
    global users
    global teams
    global abbvs
    global tr
    
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
    
    for i in range(len(users)):
        if users[i] == user1:
            index1 = i
        elif users[i] == user2:
            index2 = i
        if index1>=0 and index2>=0:
            break
    
    division = "Unknown Division"
    
    if index1 == -1:
        if index2 == -1:
            team2 = "Showdown User " + user2
        else:
            team2 = teams[index2]
        team1 = "Showdown User " + user1
    elif index2 == -1:
        team2 = "Showdown User " + user2
        team1 = teams[index1]
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
    
    return team1, team2, alive1, alive2, division


async def bracket_series_finished(replay_link, msg, channel, log, sheets):
    global bracket_matches
    global bracket_needed_to_win
    won = False
    score = 0
    log_lines = log.splitlines()
    # print(log_lines)
    user1, user2, winner = get_users_winner(log_lines)
    if user1 > user2:
        temp = user1
        user1 = user2
        user2 = temp
    if winner == user1:
        score = 1
    elif winner == user2:
        score = -1
    else:
        await msg.channel.send("Could not find users for match, though replay is at\n" + replay_link)
        return
    if (user1, user2) in [(t[0], t[1]) for t in bracket_matches]:
        for t in bracket_matches:
            if datetime.now() - t[4] > timedelta(days=1):
                bracket_matches.remove(t)
                bracket_matches.append([user1, user2, [replay_link], score, datetime.now()])
                break
            if t[0]==user1 and t[1]==user2:
                # print(datetime.now() - t[4])
                t[2].append(replay_link)
                t[3] += score
                winner_score = (abs(t[3])+len(t[2]))/2
                if winner_score>=bracket_needed_to_win:
                    won=True
                    loser_score = len(t[2]) - winner_score
                    final_score = f"{int(winner_score)}-{int(loser_score)}"
                    replays_string = ""
                    for replay in t[2]:
                        replays_string+=f'\n{replay}'
                    bracket_matches.remove(t)
                break
    else:
        bracket_matches.append([user1, user2, [replay_link], score, datetime.now()])
        
    if won:
        team1, team2, alive1, alive2, division = get_teams_mons_division(log_lines, user1, user2, sheets)
        
        if score > 0:
            final_str = f"Botfficial Bracket BO{2*bracket_needed_to_win-1} Result\n{team1} def. {team2} {final_score}{replays_string}"
        else:
            final_str = f"Botfficial Bracket BO{2*bracket_needed_to_win-1} Result\n{team2} def. {team1} {final_score}{replays_string}"
        await channel.send(final_str)

async def bracket_bo1(replay_link, msg, channel, log, sheets):
    log_lines = log.splitlines()
    # print(log_lines)
    user1, user2, winner = get_users_winner(log_lines)
    team1, team2, alive1, alive2, division = get_teams_mons_division(log_lines, user1, user2, sheets)
        
    if(winner==user1):
        final_str = f"Botfficial Bracket BO1 Result\n{team1} def. {team2} {alive1}-{alive2}\n{replay_link}"
    elif(winner==user2):
        final_str = f"Botfficial Bracket BO1 Result\n{team2} def. {team1} {alive2}-{alive1}\n{replay_link}"
    else:
        final_str = f"ERROR - winner was {winner} but could not be identified as a player"
    await channel.send(final_str)



async def replayer_finished_bracket(replay_link, msg, channel, log, sheets):
    global bracket_series
    if bracket_series:
        await bracket_series_finished(replay_link, msg, channel, log, sheets)
    else:
        await bracket_bo1(replay_link, msg, channel, log, sheets)


        
    
async def replayer_finished_draft(replay_link, channel, log, sheets):
    log_lines = log.splitlines()
    # print(log_lines)
    
    user1, user2, winner = get_users_winner(log_lines)
    team1, team2, alive1, alive2, division = get_teams_mons_division(log_lines, user1, user2, sheets)
                
    if(winner==user1):
        final_str = f"Botfficial Match Result ({division})\n{team1} def. {team2} {alive1}-{alive2}\n{replay_link}"
    elif(winner==user2):
        final_str = f"Botfficial Match Result ({division})\n{team2} def. {team1} {alive2}-{alive1}\n{replay_link}"
    else:
        final_str = f"ERROR - winner was {winner} but could not be identified as a player"
    await channel.send(final_str)


def closing_save():
    storage.update_value('A2', str(draft_tracking)[0])
    storage.update_value('B2', str(bracket_tracking)[0])
    storage.update_value('C2', str(bracket_needed_to_win))
    


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
    