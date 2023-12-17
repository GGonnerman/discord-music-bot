import discord
import glob
import os
import shutil
import yt_dlp
from discord.ext import commands
from dotenv import load_dotenv
from time import sleep
from random import shuffle

from database import setup_database, store_volume, retrieve_volume

# Load private bot token
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Register intents
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True

# Create the bot itself
bot = commands.Bot(command_prefix='>', intents=intents)

status_map = {}
song_queues = {}

@bot.event
async def on_ready():
    print("Bot is ready!")

@bot.event
async def on_join():
    pass

@bot.event
async def on_message(message):
    if not message.content.startswith(">"):
        return

    content = message.content[1:].strip()
    author = message.author
    # TODO: Doesn't feel like these things need to be here
    author_name = author.global_name

    try:
        if content == "help":
            commands = [
                ["clear", "empties the queue"],
                ["help", "prints this help message"],
                ["join", "joins the voice channel the user is in"],
                ["leave", "leaves the voice channel"],
                ["pause", "pauses song playback"],
                ["play <url>", "adds the specified url to the queue"],
                ["queue <optional count>", "prints the next x songs in the queue"],
                ["resume", "resumes song playback"],
                ["shuffle", "shuffles the queue"],
                ["fshuffle", "shuffles the queue fast (use if you plan to shuffle multiple times"],
                ["skip", "skips the current song"],
                ["status", "prints the bots status"],
                ["stop", "empties the queue and ends the current song"],
                ["volume", "prints the current volume"],
                ["volume <0-100>", "sets a new volume"],
            ]

            message_string = f"Listed below are all valid commands:\n"

            commands_string = []
            for command, description in commands:
                commands_string.append(f"**{command}**: {description}")

            message_string += "\n".join(commands_string)

            await message.channel.send(message_string)

        elif content == "join":
            
            if not author.voice:
                await message.channel.send(f"You are not currently in a voice channel.")
                return

            voice_channel = author.voice.channel

            await voice_channel.connect()
            await message.channel.send(f"Joined {voice_channel.name}")

        elif content == "leave" or content == "disconnect":
            # leave the voice channel, flush the song queue, and delete the downloaded song files

            voice_client = get_voice_client(message.guild)
            channel_name = voice_client.channel.name

            clear_song_queue(message.guild)
            delete_guild_songs(message.guild)

            await voice_client.disconnect()
            await message.channel.send(f"Disconnected from {channel_name}")

        elif content == "status":
            await message.channel.send(get_status(message.guild))

        elif content.startswith("play "):
            content = content.split(" ")[1]

            voice_client = get_voice_client(message.guild)

            attempt_message = await message.channel.send(f"Attempting to add <{content}> to queue...")

            previous_queue_size = 0
            if message.guild in song_queues:
                previous_queue_size = len(song_queues[message.guild])

            result = add_song_to_queue(message.guild, content)

            if not voice_client.is_paused() and not voice_client.is_playing():
                # If there is not current media track, play our song
                play_next_song(message.guild)
            else:
                # there is a current media track, so don't play our song, but do download it if it will be next in the queue
                if previous_queue_size == 0:
                    predownload_next_song(message.guild)


            await attempt_message.edit(content=result)

        elif content == "skip":
            voice_client = get_voice_client(message.guild)
            if skip_song(message.guild):
                await message.channel.send("Successfully skipped song")
            else:
                await message.channel.send("Failed to skip song")

        elif content == "shuffle":
            voice_client = get_voice_client(message.guild)
            result = shuffle_queue(message.guild)

            await message.channel.send(result)

        elif content == "fshuffle":
            voice_client = get_voice_client(message.guild)
            result = shuffle_queue(message.guild, should_predownload=False)

            await message.channel.send(result)

        elif content == "clear":
            clear_song_queue(message.guild)
            await message.channel.send("Cleared the queue")

        elif content == "stop":
            clear_song_queue(message.guild)
            skip_song(message.guild)
            await message.channel.send("Cleared the queue")

        elif content == "pause":
            voice_client = get_voice_client(message.guild)

            if voice_client.is_paused():
                await message.channel.send("Song is already paused")
                return

            voice_client.pause()
            await message.channel.send("Paused song")

        elif content == "resume":
            voice_client = get_voice_client(message.guild)

            if not voice_client.is_paused():
                await message.channel.send("Song is not currently paused")
                return

            voice_client.resume()
            await message.channel.send("Resumed song")

        elif content == "volume":
            await message.channel.send(f"Volume is {int(100*get_volume(message.guild))}")

        elif content.startswith("volume "):
            content = content.split(" ")[1]

            try:
                new_volume = float(content)
            except Exception:
                await message.channel.send(f"Invalid volume {content}")

            set_volume(message.guild, new_volume/100)
            await message.channel.send(f"Set volume to {int(new_volume)}")

        elif content.startswith("queue"):
            content = content[5:].strip()

            count = 5

            if content != "":
                try:
                    count = int(content)
                except:
                    await message.channel.send(f"Unable to parse {content}")
                    return

            queue_preview = get_queue(message.guild, count)

            if not queue_preview:
                await message.channel.send("The queue is currently empty")
                return
            
            queue_str = "\n".join([f"({i}) {name}" for i, name in enumerate(queue_preview)])
            
            await message.channel.send("Queue:\n" + queue_str)
        else:
            await message.channel.send(f"Could not understand message \"{content}\" from {author_name}")

    except Exception as e:
        await message.channel.send(str(e))

def get_voice_client(guild):
    matching_clients = [client for client in bot.voice_clients if client.guild == guild]
    if len(matching_clients) == 0:
        raise Exception("Not currently connected to a voice channel")
    return matching_clients[0]

def extract_songs(url):
    ydl_opts = {
        'format': 'bestaudio',
        'extract_flat': 'in_playlist',
        'ignoreerrors': True,
    }
    song_info = None
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        song_info = ydl.extract_info(url, download=False)

    processed_info = {
        "title": song_info["title"]
    }

    if "entries" in song_info:
        processed_info["ids"] = [
            {
                "title": song["title"],
                "id": song["id"]
            } for song in song_info["entries"]
        ]
        processed_info["type"] = "playlist"
    else:
        processed_info["ids"] = [{
            "title": song_info["title"],
            "id": song_info["id"]
        }]
        processed_info["type"] = "song"

    return processed_info

def add_song_to_queue(guild, url):
    if guild not in song_queues:
        song_queues[guild] = []

    try:
        info = extract_songs(url)
    except Exception as e:
        print(f"Failed to add {url} to {guild}s queue")
        print(e)
        return f"Unable to add <{url}> to queue"

    song_queues[guild].extend(info["ids"])

    if info["type"] == "playlist":
        return f"Successfully added playlist {info['title']} to queue"

    return f"Successfully added {info['title']} to queue"

def skip_song(guild):
    try:
        voice_client = get_voice_client(guild)
        voice_client.stop()
        clear_status(guild)
        return True
    except Exception:
        pass

    return False

def predownload_next_song(guild):
    if len(song_queues[guild]) > 0:
        get_downloaded_file(guild, song_queues[guild][0]["id"])

def play_next_song(guild, prev_id=None):
    if guild not in song_queues: return None
    if len(song_queues[guild]) == 0:
        clear_status(guild)
        return None
    try:
        voice_client = get_voice_client(guild)
    except Exception:
        return
    if voice_client.is_playing() or voice_client.is_paused():
        return

    # If there was a previous song, delete it
    if prev_id: delete_song(guild, prev_id)

    next_song = song_queues[guild].pop(0)
    play_song(guild, next_song)

    predownload_next_song(guild)

def download_file(guild, id):
    url = f"https://www.youtube.com/watch?v={id}"

    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': f"guilds/{guild.id}/{guild.id}-{id}.%(ext)s"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        song_info = ydl.extract_info(url, download=True)

    downloaded_path = f"guilds/{guild.id}/{guild.id}-{id}.{song_info['ext']}"

    return downloaded_path

def get_potential_path(guild, id):
    potential_paths = glob.glob(f"guilds/{guild.id}/{guild.id}-{id}.*")
    if len(potential_paths) == 0: return None
    return potential_paths[0]

def get_downloaded_file(guild, id):
    potential_path = get_potential_path(guild, id)
    if potential_path != None:
        return potential_path
    return download_file(guild, id)

def delete_song(guild, id):
    if get_potential_path(guild, id):
        os.remove(get_potential_path(guild, id))
    
def play_song(guild, song):

    title = song["title"]
    id = song["id"]

    try:
        voice_client = get_voice_client(guild)
    except Exception:
        return

    downloaded_path = get_downloaded_file(guild, id)

    ffmpeg_options = {'options': '-vn'}
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(downloaded_path, **ffmpeg_options), volume=retrieve_volume(guild))

    set_status(guild, f"📣 Playing {title} in {voice_client.channel.name} 📣")

    voice_client.play(source, after=lambda e: play_next_song(guild, id))

def set_volume(guild, volume):
    if volume < 0 or volume > 1: raise ValueError("Invalid volume")
    # Store the new volume no matter what
    store_volume(guild, volume)

    try:
        voice_client = get_voice_client(guild)
    except:
        return

    # TODO: Try to figure out how to update volume of current audio source
    if voice_client.source:
        voice_client.source.volume = volume

def shuffle_queue(guild, should_predownload=True):
    if guild not in song_queues or len(song_queues[guild]) == 0:
        return "The queue is currently empty"

    # Only actually shuffle if there is more than 1 song
    if len(song_queues[guild]) > 1:
        delete_song(guild, song_queues[guild][0]["id"])
        shuffle(song_queues[guild])
        if should_predownload: predownload_next_song(guild)

    return "Successfully shuffled queue"

def set_status(guild, status_message):
    status_map[guild] = status_message

def clear_status(guild):
    status_map.pop(guild, None)

def get_status(guild):
    if guild not in status_map:
        return "Just hanging out"

    return status_map[guild]

def get_volume(guild):
    return retrieve_volume(guild)

def clear_song_queue(guild):
    song_queues.pop(guild, None)

def get_queue(guild, count=5):
    if guild not in song_queues: return None
    if len(song_queues[guild]) == 0: return None

    return [song["title"] for song in song_queues[guild][:count]]

def delete_all_guild_songs():
    GUILD_PATH = "./guilds"
    if os.path.isdir(GUILD_PATH):
        shutil.rmtree(GUILD_PATH, ignore_errors=True)

def delete_guild_songs(guild):
    guild_id = str(guild.id)
    if not guild_id.isnumeric():
        raise Exception("Woah, guild id wasnt numeric! ", guild_id)

    if os.path.isdir(f"./guilds/{guild_id}/"):
        shutil.rmtree(f"./guilds/{guild_id}/", ignore_errors=True)

# Delete any leftover songs from last time it was running
delete_all_guild_songs()

# Setup database (currently only used for persistent volume)
setup_database()

# Start the bot
bot.run(TOKEN)
