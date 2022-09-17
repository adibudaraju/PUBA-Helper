import os
import discord
from dotenv import load_dotenv
import showdown

class ReplayClient(showdown.Client):
    async def on_receive(self, room_id, inp_type, params):
        if inp_type == 'win':
            print("ended")
            await self.save_replay(room_id)
    
    async def on_query_response(self, query_type, response):
        print("responded")
        id = response['id']
        print("Replay at replay.pokemonshowdown.com/"+id)
        
    async def on_connect(self):
        print("connected")
        await self.join("battle-gen8randombattle-1666665495")

        
def main():
    showdown_user = os.getenv("SHOWDOWN_USER")
    showdown_pass = os.getenv("SHOWDOWN_PASS")
    ReplayClient(name=showdown_user, password=showdown_pass).start(autologin=False)       

if __name__ == "__main__":
    main()




# server_id="sports"