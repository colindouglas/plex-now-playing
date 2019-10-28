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

streams_xml = ET.fromstring(now_playing.text)

streams_long = pd.DataFrame(columns=['value', 'field', 'stream'])

for i, stream in enumerate(streams_xml):
    df = pd.DataFrame.from_dict(stream.attrib, orient='index')
    df['property'] = df.index
    df['stream'] = i+1
    df.columns = ['value', 'field', 'stream']
    stream_df = streams_long.append(df, ignore_index=True)


streams = streams_long.pivot(index='stream', values='value', columns='field')
