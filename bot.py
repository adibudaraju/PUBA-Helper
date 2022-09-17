import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import showdown
from threading import Thread

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
        pre_str
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
    
    
    async def on_receive(self, room_id, inp_type, params):
        if inp_type == 'win':
            # print("ended")
            await self.save_replay(room_id)
    
    async def on_query_response(self, query_type, response):
        if(query_type == "savereplay"):
            # print("responded")
            id = response['id']
            await replayer_finished(self.pre_str + id, self.channel, self.message)
    
    async def on_connect(self):
        # print("connected")
        await self.join(self.battle)
    
def other():
    load_dotenv()
    showdown_user = os.getenv("SHOWDOWN_USER")
    showdown_pass = os.getenv("SHOWDOWN_PASS")
    ReplayClient(name=showdown_user, password=showdown_pass,
                 battle="battle-gen8randombattle-1666722038", channel=None).start(autologin=False)       

def main():
    load_dotenv()
    botID = int(os.getenv("BOT_ID"))
    channelIDs = [int(a) for a in os.getenv("CHANNEL_IDS").split(" ")]
    showdown_user = os.getenv("SHOWDOWN_USER")
    showdown_pass = os.getenv("SHOWDOWN_PASS")
    token = os.getenv("DISCORD_TOKEN")
    
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    bot = commands.Bot(command_prefix='.',intents=intents)

    # @client.event
    # async def on_ready():
    #     print(f'We have logged in as {client.user}')


    @client.event
    async def on_message(message):
        ch = message.channel
        if message.author.id == botID or ch.id not in channelIDs:
            return
        content = message.content
        if "play.pokemonshowdown.com" in content:
            battle_id = content[content.index("battle-"):]
            client2 = ReplayClient(name=showdown_user, password=showdown_pass, battle=battle_id,
                                   channel=ch, message=message, pre_str="https://replay.pokemonshowdown.com/")
            client2.start(autologin=False)
        elif "sports.psim.us" in content:
            battle_id = content[content.index("battle-"):]
            client2 = ReplayClient(name=showdown_user, password=showdown_pass, battle=battle_id,
                        channel=ch, message=message, pre_str="https://replay.pokemonshowdown.com/sports-", server_id="sports")
            client2.start(autologin=False)
            


    client.run(token)

async def replayer_finished(replay_link, ch, msg):
    # print("Replay at "+replay_link)
    await msg.reply("Replay at " + replay_link, mention_author=False)

if __name__ == "__main__":
    main()