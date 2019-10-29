# Python version
# Work in process!
from getpass import getpass
from xml.etree import ElementTree as ET
from datetime import datetime

import json
import os
import pandas as pd
import requests
import keyring

# Set working directory (ending with /) where it can save tokens, find credentials.
wkdir = '~/Scripts/'

# The location of the file that stores Plex token
token_path = os.path.expanduser(wkdir) + ".plex_token_py"

# Read in Plex token, update it if it's older than 1 day
if os.path.exists(token_path):
    token_save = pd.read_csv(token_path, header=None)
    token = token_save[1][1]
    last_token_update = datetime.strptime(token_save[1][2], "%Y-%m-%d %H:%M:%S.%f")
    time_since_update = datetime.now() - last_token_update
    update_token = time_since_update.days >= 1
else:
    update_token = True

if update_token:
    username = input("Enter Plex username")
    password = keyring.get_password("Plex-Now-Playing", username)
    if password is None:
        password = getpass()
        keyring.set_password("Plex-Now-Playing", username, password)
    plex_creds = [username, password]
    token_request = requests.post(
        url='https://plex.tv/users/sign_in.json',
        data="user%5Blogin%5D=" + plex_creds[0] + "&user%5Bpassword%5D=" + plex_creds[1],
        headers={
            "X-Plex-Client-Identifier": "NowPlayingScript",
            "X-Plex-Product": "NowPlayingScript",
            "X-Plex-Version": "0.0.1"}
    )
    token = json.loads(token_request.text)['user']['authToken']
    token_save = {
        "username": plex_creds[0],
        "token": token,
        "last_update": datetime.now()
    }
    pd.DataFrame.from_dict(data=token_save, orient='index').to_csv(token_path, header=False)

now_playing = requests.get(
    url="http://127.0.0.1:32400/status/sessions",
    headers={"X-Plex-Token": token}
)

streams_xml = ET.fromstring(now_playing.text)

# Create long-style dataframe of stream data
streams_long = pd.DataFrame(columns=['value', 'field', 'stream'])
for i, stream in enumerate(streams_xml):
    df = pd.DataFrame.from_dict(stream.attrib, orient='index')
    df['property'] = df.index
    df['stream'] = i
    df.columns = ['value', 'field', 'stream']
    streams_long = streams_long.append(df, ignore_index=True)

# Pivot df so it is rowwise by stream
streams = streams_long.pivot(index='stream', values='value', columns='field')

if not len(streams):
    print("Nothing playing")
else:
    streams = streams.assign(pretty_string=streams.parentTitle + streams.titleSort,
                             second_argument="butt")
    print(streams['second_argument'])