# YouTube Downloader Telegram Bot

A professional Telegram bot for downloading YouTube videos with format selection and trimming capabilities.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install FFmpeg (required for video trimming):
   - Windows: Download from https://ffmpeg.org/
   - Add ffmpeg to your system PATH

3. Configure `.env`:
   - Get API_ID and API_HASH from https://my.telegram.org/
   - Get BOT_TOKEN from @BotFather

4. Run the bot:
```bash
python bot.py
```

## Features

- 🎥 Multiple format selection (Audio, Video, Info, Subtitle, etc.)
- 🎬 Quality selection with detailed format information
- ✂️ Video trimming with precise time controls
- 📤 Direct file upload to Telegram
- 🔄 Professional user interface with inline keyboards

## Usage

1. Send `/start` to begin
2. Send any YouTube URL
3. Select format type (Video recommended)
4. Choose quality/format from the list
5. Either download directly or trim the video first
6. For trimming, enter start and end times in `HH:MM:SS` format
