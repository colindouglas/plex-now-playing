# Python version
# Work in process!

# Set working directory (ending with /) where it can save tokens, find credentials.
# NOTE: Password will be saved in plaintext in this folder! Choose somewhere secure.
wkdir = '~/Scripts/.plex_creds'

import requests, json, csv, os, pandas as pd
from xml.etree import ElementTree as ET

cred_file = open(os.path.expanduser(wkdir))
plex_creds = next(csv.reader(cred_file))

token_request = requests.post(
    url='https://plex.tv/users/sign_in.json',
    data="user%5Blogin%5D=" + plex_creds[0] + "&user%5Bpassword%5D=" + plex_creds[1],
    headers={
        "X-Plex-Client-Identifier": "NowPlayingScript",
        "X-Plex-Product": "NowPlayingScript",
        "X-Plex-Version": "0.0.1"}
)

token = json.loads(token_request.text)['user']['authToken']

now_playing = requests.get(
    url="http://127.0.0.1:32400/status/sessions",
    headers={"X-Plex-Token": token}
)

streams = ET.fromstring(now_playing.text)

stream_df = pd.DataFrame(columns=['value', 'field', 'stream'])

for i, stream in enumerate(streams):
    df = pd.DataFrame.from_dict(stream.attrib, orient='index')
    df['property'] = df.index
    df['stream'] = i+1
    df.columns = ['value', 'field', 'stream']
    stream_df = stream_df.append(df, ignore_index=True)


stream_df = stream_df.pivot(index='stream', values='value', columns='field')
