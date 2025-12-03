# Discord Music Bot 🎵

A Discord bot that plays music from YouTube in voice channels. Built with Python and designed to run in Docker containers.

## Features

- 🎵 Play music from YouTube (search or direct links)
- ⏭️ Skip tracks
- 📝 View queue
- 🛑 Stop playback and clear queue
- 👋 Auto-disconnect from empty channels
- 🔄 Automatic reconnection for stable playback in Docker

## Prerequisites

- Docker installed on your system
- A Discord bot token (see setup below)

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Enable these **Privileged Gateway Intents**:
   - ✅ PRESENCE INTENT
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT
5. Under "Bot Permissions", enable:
   - ✅ Connect
   - ✅ Speak
   - ✅ Use Voice Activity
6. Copy your bot token (keep it secret!)

### 2. Invite Bot to Your Server

Generate an invite link with these scopes:
- `bot`
- `applications.commands`

And these permissions:
- Connect
- Speak
- Send Messages
- Use Slash Commands

### 3. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your bot token
nano .env
```

Replace `your_bot_token_here` with your actual Discord bot token.

## Running with Docker

### Build the image:
```bash
docker build -t musicbot .
```

### Run the container:
```bash
docker run -d \
  --name musicbot \
  --env-file ./.env \
  --network host \
  --restart unless-stopped \
  musicbot
```

### View logs:
```bash
docker logs -f musicbot
```

### Stop the bot:
```bash
docker stop musicbot
docker rm musicbot
```

## Commands

All commands use Discord slash commands:

| Command | Description |
|---------|-------------|
| `/play <query>` | Play a song from YouTube (search or URL) |
| `/skip` | Skip the current song |
| `/queue` | Show the current queue |
| `/stop` | Stop playback and clear queue |
| `/leave` | Disconnect the bot from voice channel |

## Running Locally (without Docker)

### Install dependencies:
```bash
pip install -r requirements.txt
```

### Install FFmpeg:
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Run the bot:
```bash
python bot.py
```

## Troubleshooting

### Bot won't connect to voice channel
- Make sure **VOICE intent** is enabled in Discord Developer Portal
- Verify the bot has "Connect" and "Speak" permissions
- Try using `--network host` with Docker

### YouTube extraction warnings
- The bot automatically handles this with fallback clients
- No action needed from your side

### Stream interruptions
- The bot has automatic reconnection built-in
- If issues persist, check your network connection

## Project Structure

```
.
├── bot.py              # Main bot code
├── Dockerfile          # Docker configuration
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
├── .env.example       # Template for .env
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## License

MIT License - Feel free to use and modify!

## Contributing

Pull requests are welcome! For major changes, please open an issue first.

## Support

If you encounter any issues, please open a GitHub issue with:
- Error logs
- Steps to reproduce
- Your environment (OS, Docker version, etc.)