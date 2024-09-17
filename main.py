import asyncio

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import yt_dlp as youtube_dl  # Use yt-dlp instead of youtube_dl

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# BOT SETUP

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)

# MUSIC FUNCTIONALITY

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename


# BOT COMMANDS

voice_clients = {}


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


@bot.command(name='canta', help='To play song')
async def play(ctx, url):
    try:
        voice_client = voice_clients.get(ctx.guild.id)

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel.")
            return

        async with ctx.typing():
            title = await YTDLSource.from_url(url, loop=bot.loop)
            voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=title))
        await ctx.send('Now playing: {}' + title)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")


@bot.command(name='fermate', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='continua', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play_song command")


@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='salta', help='Skips the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.skip()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


# RUN BOT LOCALLY

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
