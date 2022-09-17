import discord
from discord.ext import commands



# This example requires the 'message_content' intent.
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='.',intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    channelIDsToListen = [ 1020695939255648278 ]
    if '$hello' in channelIDsToListen:
        await message.channel.send('Hi')
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')
    if message.content.startswith('http'):
        link = message.content
        battle_id = link.strip("http://sports.psim.us/")
        await message.channel.send(battle_id)



client.run("MTAyMDY5Njg0NTY4NjY3MzQ0OA.GBW3jE.XjRsuwP-94-HFbOM9gkJs8o1hd7XAKnr4bss94")