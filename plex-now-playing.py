# Python version
# Work in process!

import requests, json
from xml.etree import ElementTree as ET

response = requests.post(
  url = 'https://plex.tv/users/sign_in.json',
  data = "user%5Blogin%5D=USERNAME&user%5Bpassword%5D=HUNTER@",
  headers = {
    "X-Plex-Client-Identifier": "NowPlayingScript", 
    "X-Plex-Product": "NowPlayingScript",
    "X-Plex-Version": "0.0.1"}
    )

token = json.loads(response.text)['user']['authToken']

print(token)

now_playing = requests.get(
  url = "http://127.0.0.1:32400/status/sessions",
  headers = {"X-Plex-Token": token}
  )
  
streams = ET.fromstring(now_playing.text)
