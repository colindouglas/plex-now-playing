from getpass import getpass
from xml.etree import ElementTree as ET
from datetime import datetime
import json
import csv
import os
import requests
import keyring
import re

WORKING_DIR = '~/Scripts/'              # Working directory (ending with /) where script saves tokens
PLEX_SERVER = 'http://127.0.0.1:32400'  # Address of Plex server to query
USERNAME = ''                           # Plex username to login, only required on first run
PASSWORD = ''                           # Plex password to login, after first run, stored in keyring

# The location of the file that stores Plex token
token_path = os.path.expanduser(WORKING_DIR) + '.plextoken'

# Check if there's a token saved
token = None
username = None
if os.path.exists(token_path):
    with open(token_path) as token_file:
        token_dict = next(csv.DictReader(token_file))
    token = token_dict.get('token')
    username = token_dict.get('username')
    token_last_update = datetime.strptime(token_dict.get('last_update'), '%Y-%m-%d %H:%M:%S.%f')
    since_last_update = datetime.now() - token_last_update

# Update the token if there wasn't one saved, or it's older than a day
if not token or since_last_update.days >= 1:
    username = username or USERNAME
    password = keyring.get_password('Plex-Now-Playing', username) or PASSWORD
    keyring.set_password('Plex-Now-Playing', username, password)
    plex_creds = [username, password]
    token_request = requests.post(
        url='https://plex.tv/users/sign_in.json',
        data='user%5Blogin%5D=' + plex_creds[0] + '&user%5Bpassword%5D=' + plex_creds[1],
        headers={
            'X-Plex-Client-Identifier': 'Plex-Now-Playing',
            'X-Plex-Product': 'Plex-Now-Playing',
            'X-Plex-Version': '0.0.1'}
    )
    if token_request.status_code < 300:
        token = json.loads(token_request.text)['user']['authToken']
        token_data = {
            'username': plex_creds[0],
            'token': token,
            'last_update': datetime.now()
        }
        with open(token_path, 'w') as token_file:
            writer = csv.DictWriter(token_file, token_data.keys())
            writer.writeheader()
            writer.writerow(token_data)
    else:
        print('Authentication problem')

# Ask the local Plex server for the current sessions
if token:
    now_playing = requests.get(
        url=PLEX_SERVER + '/status/sessions',
        headers={'X-Plex-Token': token}
    )

# Parse the XML returned by Plex
streams_xml = ET.fromstring(now_playing.text)

# Return either the time a transcoded started _or_ the current time as a string 
def parse_stream_time(stream):
    start_time = stream.get('lastViewedAt', default=datetime.now())  # If there's no LastViewedAt, use current time
    if type(start_time) is str:
        start_time = int(start_time)
        start_time = datetime.fromtimestamp(start_time)
    return start_time.strftime('%b %d, %I:%M')  # Mon 01, HH:MM

# Return the user watching the stream. Truncate emails before @
def parse_stream_user(stream):
    user_full = stream.find('User').get('title', default='Unknown User')
    try:
        user = re.search('[^@]+', user_full).group(0)
    except AttributeError:
        user = user_full
    return user


if len(streams_xml):
    # For each stream, print an informative line about the stream
    for stream in streams_xml:
        # How to display TV show episodes
        # Date: User // Series - S0E00 - Episode 
        if stream.get('type') == 'episode':
            episode_name = stream.get('title', default='Unknown Episode')
            series_name_long = stream.get('grandparentTitle', default='Unknown Series')
            series_name = ' '.join(series_name_long.split(' ')[:5])  # Only first five words
            episode = 'E' + stream.get('index', default='')
            start_time = parse_stream_time(stream)
            user = parse_stream_user(stream)
            try:
                season_string = stream.get('parentTitle', default='')
                season = "S" + re.search('[0-9]+', season_string).group(0)
            except AttributeError:
                season = ''
            print(
                start_time + ': ' + user + " // " +
                series_name + " - " + season + episode + " - " + episode_name
            )
        # How to display Movies
        # Date: User // Movie Title (YEAR)
        elif stream.get('type') == 'movie':
            movie_title = stream.get('title', default='Unknown Movie')
            movie_year = stream.get('originallyAvailableAt').split('-')[0]
            start_time = parse_stream_time(stream)
            user = parse_stream_user(stream)
            print(
                start_time + ': ' + user + " // " +
                movie_title + " (" + movie_year + ")"
                )
        # How to display Music tracks
        # Date: User // Arist - Track
        elif stream.get('type') == 'track':
            track_title = stream.get('title', default='Unknown Song')
            track_artist = stream.get('grandparentTitle', default='Unknown Artist')
            # track_album = stream.get('parentTitle', default='Unknown Album')
            start_time = parse_stream_time(stream)
            user = parse_stream_user(stream)
            print(
                start_time + ': ' + user + " // " +
                track_artist + " - " + track_title
                )
        else:
            start_time = parse_stream_time(stream)
            user = parse_stream_user(stream)
            print(start_time + ': ' + user + " // " +
                  "Unknown Stream"
                  )

else:
    print('Nothing playing')
