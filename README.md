# YouTube Downloader Telegram Bot

A professional Telegram bot for downloading YouTube videos with multiple format options, trimming, and compression features. Optimized for Railway cloud deployment.

## Features

- 🎥 Multiple format selection (Video, Audio, Subtitle, Animation, Document)
- 🎬 Quality selection with detailed format information
- ✂️ Video trimming with precise time controls
- 🗜️ Video compression for large files
- 📂 File splitting for 2GB+ videos
- 📤 Direct file upload to Telegram
- 🚀 Cloud-optimized for Railway deployment

## Railway Deployment

### One-Click Deploy
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

### Manual Deployment

1. **Fork this repository**

2. **Connect to Railway:**
   - Go to [Railway](https://railway.app/)
   - Click "Deploy from GitHub repo"
   - Select your forked repository

3. **Set Environment Variables:**
   ```
   API_ID=your_api_id_here
   API_HASH=your_api_hash_here
   BOT_TOKEN=your_bot_token_here
   ```

4. **Deploy:**
   - Railway will automatically detect the configuration
   - FFmpeg will be installed via nixpacks.toml
   - Bot will start automatically

### Getting Bot Credentials

1. **API_ID and API_HASH:**
   - Go to https://my.telegram.org/
   - Log in with your Telegram account
   - Go to "API development tools"
   - Create a new application
   - Copy API_ID and API_HASH

2. **BOT_TOKEN:**
   - Message @BotFather on Telegram
   - Create a new bot with `/newbot`
   - Copy the bot token

## Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install FFmpeg:**
   - Windows: Download from https://ffmpeg.org/
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`

3. **Configure environment:**
   - Copy `.env.example` to `.env`
   - Fill in your credentials

4. **Run the bot:**
   ```bash
   python bot.py
   ```

## Usage

1. Send `/start` to begin
2. Send any YouTube URL
3. Select format type (Video recommended)
4. Choose quality/format from the list
5. Either download directly or trim the video first
6. For trimming, enter start and end times in `HH:MM:SS` format

## File Size Handling

- **Small files (<50MB):** Direct upload
- **Medium files (50MB-2GB):** Compression option available
- **Large files (>2GB):** Automatic compression or splitting into parts

## Technical Details

- **Framework:** Pyrogram (MTProto API)
- **Video Processing:** yt-dlp + FFmpeg
- **Cloud Platform:** Railway
- **File Storage:** Temporary (auto-cleanup)
- **Memory Optimized:** For cloud deployment

## Support

For issues and questions:
- Create an issue on GitHub
- Check the Railway deployment logs
- Ensure FFmpeg is properly installed

## License

MIT License - feel free to modify and use for your projects.
