# A Discord Music Bot

## Table of Contents:

1. Features

2. Installation

3. Usage

4. Future Roadmap

## Features

- Simple music bot for discord
- Plays music from yt-dlp
  - Has support for videos and playlists
- Stores persistent server data in a SQLite database
- Worked in multiple servers (*however, this is untested*)

## Installation

### Manual

- Clone this repository
- Using python, install dependencies from `requirements.txt`
```
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```
- Setup a discord bot at [Discord Applications](https://discord.com/developers/applications)
  - Grab your token (select your app > Bot > TOKEN) 
  - Grab your client id (select your app > General Information > APPLICATION ID)
- Use the template example.env to create your .env with your bot token 
- Add the bot to your server at https://discordapp.com/oauth2/authorize?&client_id=CLIENTID&scope=bot&permissions=8 replacing CLIENTID with your client id
- Run with `python main.py`

## Usage

### Here are all of the commands
- **clear**: empties the queue
- **help**: prints this help message
- **join**: joins the voice channel the user is in
- **leave**: leaves the voice channel
- **pause**: pauses song playback
- **play <url>**: adds the specified url to the queue
- **queue <optional count>**: prints the next x songs in the queue
- **resume**: resumes song playback
- **shuffle**: shuffles the queue
- **fshuffle**: shuffles the queue fast (use if you plan to shuffle multiple times)
- **skip**: skips the current song
- **status**: prints the bots status
- **stop**: empties the queue and ends the current song
- **volume**: prints the current volume
- **volume <float 0-1>**: sets a new volume

## Future Roadmap

- Add ability to save and recall specific queues
- Ability to require a certain role to control
- Support for local files
- Better responses to commands
  - Duration of songs
  - Total number of songs from a queues
  - Number of songs added from a playlist
  - Better skip message
- Clean up where guild vs guild.id is used
- Potentially test with [Cogs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html)
