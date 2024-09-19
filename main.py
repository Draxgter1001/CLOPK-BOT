import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import yt_dlp
from discord import FFmpegOpusAudio
from flask import Flask
from threading import Thread

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# BOT SETUP
intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)

# MUSIC QUEUE
music_queues = {}
voice_clients = {}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"'
}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'opus',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

async def play_next(ctx):
    if music_queues[ctx.guild.id]:
        next_url = music_queues[ctx.guild.id][0]  # Don't pop yet
        try:
            print(f"Fetching stream for URL: {next_url}")
            info = ytdl.extract_info(next_url, download=False)
            audio_url = info['url']
            print(f"Found stream URL: {audio_url}")

            source = FFmpegOpusAudio(audio_url, **FFMPEG_OPTIONS)
            voice_client = voice_clients[ctx.guild.id]
            voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop).result())
            await ctx.send(f'Now playing: {info["title"]}')
            music_queues[ctx.guild.id].pop(0)  # Remove the URL only after successfully playing
        except Exception as e:
            await ctx.send(f"An error occurred while playing the song: {e}")
            print(f"Error in play_next: {e}")
            music_queues[ctx.guild.id].pop(0)  # Remove the problematic URL
            await play_next(ctx)  # Try to play the next song
    else:
        await ctx.send("Queue is empty.")

@bot.command(name='canta', help='To play song')
async def play(ctx, *, url):
    try:
        voice_client = voice_clients.get(ctx.guild.id)

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel.")
            return

        if ctx.guild.id not in music_queues:
            music_queues[ctx.guild.id] = []

        # Validate URL
        if not url.startswith("https://www.youtube.com/watch?v="):
            await ctx.send("Please provide a valid YouTube URL.")
            return

        music_queues[ctx.guild.id].append(url)
        await ctx.send(f'Added to queue: {url}')

        if not voice_client.is_playing():
            await play_next(ctx)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        print(f"Error in play command: {e}")

@bot.command(name='frocio', help='Tells the bot to join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel

    try:
        await ctx.send(f"Attempting to connect to {channel.name}...")
        voice_client = await channel.connect()
        voice_clients[ctx.guild.id] = voice_client
        await ctx.send(f"Connected to {channel.name}")
    except discord.errors.ClientException as e:
        await ctx.send(f"Failed to connect to the voice channel: {e}")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.command(name='muori', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = voice_clients.get(ctx.guild.id)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        del voice_clients[ctx.guild.id]
    else:
        await ctx.send("The bot is not connected to a voice channel.")

@bot.command(name='fermate', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.command(name='continua', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play_song command")

@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.command(name='salta', help='Skips the song')
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await play_next(ctx)
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.command(name='coda', help='Displays the current music queue')
async def view_queue(ctx):
    if ctx.guild.id in music_queues and music_queues[ctx.guild.id]:
        queue = music_queues[ctx.guild.id]
        queue_list = "\n".join([f"{index + 1}. {url}" for index, url in enumerate(queue)])
        await ctx.send(f"Current queue:\n{queue_list}")
    else:
        await ctx.send("The queue is empty.")

# Flask server to keep the bot alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# RUN BOT
if __name__ == '__main__':
    keep_alive()
    bot.run(DISCORD_TOKEN)
