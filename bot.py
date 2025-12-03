import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
import collections
from dotenv import load_dotenv
import os

# --- Token ---
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# --- FFmpeg in Docker ---
#FFMPEG_EXE_PATH = r"C:\Users\itayb\OneDrive\שולחן העבודה\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"
FFMPEG_EXE_PATH = "/usr/bin/ffmpeg" 

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

YD_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'ffmpeg_location': FFMPEG_EXE_PATH,
    #'cookiefile': '/app/cookies.txt',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web']
        }
    },
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'opus',
    }]
}

# Global music queue for servers
song_queues = collections.defaultdict(collections.deque)


async def ytdl_search(query):
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(YD_OPTS) as ydl:
        try:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
            if 'entries' in info:
                info = info['entries'][0]

            return {
                'source': info['url'],
                'title': info['title']
            }

        except Exception as e:
            print(f"Error during ytdl extraction: {e}")
            return None


def play_next_song(guild_id, voice_client):
    if guild_id in song_queues and song_queues[guild_id]:
        song_data = song_queues[guild_id].popleft()
        try:
            # FFmpeg options for better streaming stability
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn -bufsize 512k'
            }
            
            source = discord.FFmpegPCMAudio(
                source=song_data['source'],
                executable=FFMPEG_EXE_PATH,
                **ffmpeg_options
            )
            voice_client.play(
                source,
                after=lambda e: play_next_song(guild_id, voice_client)
                if e is None else print(f"Player error: {e}")
            )
        except Exception as e:
            print(f"Error playing next song: {e}")


async def connect_voice_with_retry(channel, max_retries=5):
    """Connect to voice channel with multiple retry attempts for Docker environments"""
    for attempt in range(max_retries):
        try:
            print(f"Voice connection attempt {attempt + 1}/{max_retries} to channel: {channel.name}")
            
            # Longer timeout and reconnect enabled
            voice_client = await asyncio.wait_for(
                channel.connect(reconnect=True, timeout=15.0),
                timeout=20.0
            )
            
            print(f"Successfully connected to voice channel: {channel.name}")
            return voice_client
            
        except asyncio.TimeoutError:
            print(f"Connection timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                print(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                raise Exception("Connection timeout after all retries")
                
        except discord.errors.ConnectionClosed as e:
            print(f"Connection closed (4006 error) on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 10)
                print(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                raise Exception(f"Connection failed after all retries: {e}")
                
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e.__class__.__name__}: {e}")
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 10)
                print(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                raise


@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print("Commands synced successfully")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    print(f'Bot connected: {bot.user} (ID: {bot.user.id})')
    print(f'Connected to {len(bot.guilds)} guild(s)')
    auto_leave_check.start()


@bot.tree.command(name="play", description="Play a YouTube song")
@discord.app_commands.describe(query="Song name or YouTube link")
async def play_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    guild_id = interaction.guild_id

    if not interaction.user.voice:
        await interaction.followup.send("❌ You must be in a voice channel.")
        return

    channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    # If not connected, connect with retry logic
    if not voice_client or not voice_client.is_connected():
        try:
            # Disconnect if there's a stale connection
            if voice_client:
                await voice_client.disconnect(force=True)
                await asyncio.sleep(1)
            
            voice_client = await connect_voice_with_retry(channel)
            
        except Exception as e:
            error_msg = str(e)
            print(f"Failed to connect to voice: {error_msg}")
            await interaction.followup.send(
                f"❌ Unable to connect to voice channel.\n"
                f"Error: {error_msg}\n\n"
                f"**Troubleshooting:**\n"
                f"• Make sure the bot has 'Connect' and 'Speak' permissions\n"
                f"• Verify VOICE intent is enabled in Discord Developer Portal\n"
                f"• Try the command again in a few seconds"
            )
            return

    # Search for the song
    song_data = await ytdl_search(query)
    if not song_data:
        await interaction.followup.send(f"❌ No results for '{query}'")
        return

    # Add to queue or play immediately
    if voice_client.is_playing() or voice_client.is_paused():
        song_queues[guild_id].append(song_data)
        queue_position = len(song_queues[guild_id])
        await interaction.followup.send(
            f"➕ Added to queue (position #{queue_position}): `{song_data['title']}`"
        )
    else:
        try:
            # FFmpeg options for better streaming stability
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn -bufsize 512k'
            }
            
            source = discord.FFmpegPCMAudio(
                source=song_data['source'],
                executable=FFMPEG_EXE_PATH,
                **ffmpeg_options
            )
            voice_client.play(
                source,
                after=lambda e: play_next_song(guild_id, voice_client)
                if e is None else print(f"Player error: {e}")
            )
            await interaction.followup.send(f"🎶 Now playing: `{song_data['title']}`")

        except Exception as e:
            print(f"Error playing song: {e}")
            await interaction.followup.send("❌ Error playing song.")


@bot.tree.command(name="skip", description="Skip current song")
async def skip_slash(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ Skipping...")
    else:
        await interaction.response.send_message("🧐 Nothing to skip.")


@bot.tree.command(name="queue", description="Show the current music queue")
async def queue_slash(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    
    if guild_id not in song_queues or not song_queues[guild_id]:
        await interaction.response.send_message("📝 Queue is empty.")
        return
    
    queue_list = "\n".join([
        f"{i+1}. {song['title']}" 
        for i, song in enumerate(list(song_queues[guild_id]))
    ])
    
    await interaction.response.send_message(f"📝 **Current Queue:**\n{queue_list}")


@bot.tree.command(name="stop", description="Stop music and clear queue")
async def stop_slash(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    guild_id = interaction.guild_id

    if guild_id in song_queues:
        song_queues[guild_id].clear()

    if vc:
        vc.stop()
        await interaction.response.send_message("🛑 Music stopped and queue cleared.")
    else:
        await interaction.response.send_message("🧐 Bot is not playing anything.")


@bot.tree.command(name="leave", description="Disconnect bot")
async def leave_slash(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        song_queues[interaction.guild_id].clear()
        await vc.disconnect(force=True)
        await interaction.response.send_message("👋 Left the channel.")
    else:
        await interaction.response.send_message("🧐 Bot is not in a voice channel.")


@tasks.loop(minutes=2)
async def auto_leave_check():
    """Automatically disconnect from empty voice channels"""
    for guild in bot.guilds:
        vc = guild.voice_client
        if not vc:
            continue

        members = [m for m in vc.channel.members if not m.bot]

        if not members and not vc.is_playing() and not song_queues[guild.id]:
            print(f"Auto-leave in {guild.name} (empty channel).")
            try:
                await vc.disconnect(force=True)
                song_queues[guild.id].clear()
            except Exception as e:
                print(f"Error during auto-leave: {e}")


@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state changes for better connection stability"""
    if member.id == bot.user.id:
        # Bot was disconnected
        if before.channel and not after.channel:
            guild_id = before.channel.guild.id
            if guild_id in song_queues:
                song_queues[guild_id].clear()
            print(f"Bot disconnected from voice in {before.channel.guild.name}")


# --- Run bot ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN not found in environment variables!")
        exit(1)
    
    print("Starting Discord Music Bot...")
    bot.run(BOT_TOKEN)