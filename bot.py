import os
import asyncio
import math
import random
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import yt_dlp
from dotenv import load_dotenv
import tempfile
import shutil
import json

load_dotenv()

app = Client(
    "youtube_dl_bot",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

# Store user selections temporarily
user_data = {}

# Professional user agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
]

def get_cookies_path():
    """Get path to cookies file"""
    cookies_dir = os.path.join(os.path.dirname(__file__), 'cookies')
    os.makedirs(cookies_dir, exist_ok=True)
    return os.path.join(cookies_dir, 'youtube_cookies.txt')

def create_robust_ydl_opts(additional_opts=None):
    """Create robust yt-dlp options with anti-bot measures"""
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'user_agent': random.choice(USER_AGENTS),
        'sleep_interval': random.uniform(1, 3),
        'max_sleep_interval': 5,
        'extractor_retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
        'ignoreerrors': False,
        'no_check_certificate': True,
        'prefer_insecure': False,
        'http_headers': {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    
    # Add cookies if available
    cookies_path = get_cookies_path()
    if os.path.exists(cookies_path):
        base_opts['cookiefile'] = cookies_path
    
    # Try to extract cookies from browser as fallback
    for browser in ['chrome', 'firefox', 'safari', 'edge']:
        try:
            base_opts['cookiesfrombrowser'] = (browser,)
            break
        except:
            continue
    
    if additional_opts:
        base_opts.update(additional_opts)
    
    return base_opts

def get_video_info(url, retry_count=0):
    """Extract video information with robust error handling"""
    max_retries = 3
    
    if retry_count >= max_retries:
        return None
    
    try:
        # Add random delay between retries
        if retry_count > 0:
            time.sleep(random.uniform(2, 5))
        
        ydl_opts = create_robust_ydl_opts()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
            
    except yt_dlp.utils.ExtractorError as e:
        error_msg = str(e).lower()
        
        if 'sign in to confirm' in error_msg or 'bot' in error_msg:
            # Handle bot detection specifically
            if retry_count < max_retries - 1:
                return get_video_info_with_fallback(url, retry_count + 1)
        
        return None
    except Exception as e:
        if retry_count < max_retries - 1:
            return get_video_info(url, retry_count + 1)
        return None

def get_video_info_with_fallback(url, retry_count=0):
    """Fallback method with different strategies"""
    strategies = [
        # Strategy 1: Use different user agent and headers
        {
            'user_agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'http_headers': {
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept': '*/*',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
        },
        # Strategy 2: Mobile user agent
        {
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
        },
        # Strategy 3: Embed extraction
        {
            'user_agent': random.choice(USER_AGENTS),
            'extract_flat': False,
            'force_json': True,
        }
    ]
    
    for i, strategy in enumerate(strategies):
        if retry_count > i:
            continue
            
        try:
            time.sleep(random.uniform(3, 6))  # Longer delay
            ydl_opts = create_robust_ydl_opts(strategy)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
                
        except Exception as e:
            continue
    
    return None

def format_duration(seconds):
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes} minutes {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} hours {minutes} minutes"

def format_filesize(bytes_size):
    """Format file size in human readable format"""
    if bytes_size == 0:
        return "0 B"
    size_names = ["B", "KiB", "MiB", "GiB"]
    i = int(math.floor(math.log(bytes_size, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_size / p, 2)
    return f"{s} {size_names[i]}"

async def split_video(file_path, max_size=1024*1024*1024):  # 1GB
    """Split video file if larger than max_size"""
    file_size = os.path.getsize(file_path)
    if file_size <= max_size:
        return [file_path]
    
    # Calculate number of parts needed
    parts = math.ceil(file_size / max_size)
    part_files = []
    
    # Use ffmpeg to split video
    base_name = os.path.splitext(file_path)[0]
    extension = os.path.splitext(file_path)[1]
    
    # Get video duration
    import subprocess
    result = subprocess.run([
        'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', file_path
    ], capture_output=True, text=True)
    
    total_duration = float(result.stdout.strip())
    part_duration = total_duration / parts
    
    for i in range(parts):
        start_time = i * part_duration
        part_file = f"{base_name}_part{i+1}{extension}"
        
        subprocess.run([
            'ffmpeg', '-i', file_path, '-ss', str(start_time),
            '-t', str(part_duration), '-c', 'copy', part_file, '-y'
        ], capture_output=True)
        
        if os.path.exists(part_file):
            part_files.append(part_file)
    
    return part_files

@app.on_message(filters.command("start"))
async def start_command(client, message):
    welcome_text = """
🎬 **YouTube Downloader Bot**

Send me a YouTube URL and I'll help you download it in your preferred format!

Supported formats:
• 📹 Video (MP4, WebM)
• 🎵 Audio (MP3, M4A)
• 📄 Document
• ℹ️ Info only

Just send me a YouTube URL to get started!
"""
    await message.reply_text(welcome_text)

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_url(client, message):
    url = message.text.strip()
    
    # Basic YouTube URL validation
    if "youtube.com" not in url and "youtu.be" not in url:
        await message.reply_text("❌ Please send a valid YouTube URL!")
        return
    
    progress_msg = await message.reply_text("🔍 Analyzing video...")
    
    # Try multiple times with different strategies
    video_info = None
    for attempt in range(3):
        if attempt > 0:
            await progress_msg.edit_text(f"🔍 Analyzing video... (Attempt {attempt + 1}/3)")
        
        video_info = get_video_info(url, attempt)
        if video_info:
            break
        
        # Wait before next attempt
        await asyncio.sleep(2)
    
    if not video_info:
        error_text = """
❌ **Failed to get video information**

This might be due to:
• Video is private or restricted
• YouTube bot detection
• Video is not available in your region

**Solutions:**
1. Try again in a few minutes
2. Make sure the video is public
3. Contact admin if issue persists

💡 **Tip:** The bot automatically tries multiple methods to bypass restrictions.
"""
        await progress_msg.edit_text(error_text)
        return
    
    # Store video info for user
    user_data[message.from_user.id] = {
        'url': url,
        'info': video_info
    }
    
    # Create format selection keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 Audio", callback_data="format_audio")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="format_info")],
        [InlineKeyboardButton("📄 Document", callback_data="format_document")],
        [InlineKeyboardButton("🎬 Video", callback_data="format_video")]
    ])
    
    await progress_msg.edit_text(
        "**Please select required format:** 😬",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex("format_"))
async def handle_format_selection(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    format_type = callback_query.data.split("_")[1]
    
    if user_id not in user_data:
        await callback_query.answer("❌ Session expired. Please send the URL again.")
        return
    
    video_info = user_data[user_id]['info']
    
    if format_type == "info":
        # Show video information
        duration = format_duration(video_info.get('duration', 0))
        info_text = f"""
📹 **Video Information**

**Title:** {video_info.get('title', 'N/A')}
**Duration:** {duration}
**Views:** {video_info.get('view_count', 'N/A'):,}
**Uploader:** {video_info.get('uploader', 'N/A')}
**Upload Date:** {video_info.get('upload_date', 'N/A')}

**Description:**
{video_info.get('description', 'N/A')[:500]}...
"""
        await callback_query.edit_message_text(info_text)
        return
    
    elif format_type == "audio":
        # Handle audio download
        await callback_query.edit_message_text("🎵 Preparing audio download...")
        await download_media(callback_query, "audio")
        return
    
    elif format_type == "document":
        # Handle document download
        await callback_query.edit_message_text("📄 Preparing document download...")
        await download_media(callback_query, "document")
        return
    
    elif format_type == "video":
        # Show video quality options
        formats = video_info.get('formats', [])
        video_formats = []
        
        for fmt in formats:
            if fmt.get('vcodec') != 'none' and fmt.get('height'):
                height = fmt.get('height')
                ext = fmt.get('ext', 'mp4').upper()
                filesize = fmt.get('filesize') or fmt.get('filesize_approx', 0)
                size_str = format_filesize(filesize) if filesize else "unknown"
                vcodec = fmt.get('vcodec', 'unknown')
                fps = fmt.get('fps', 30)
                
                quality_text = f"{height}p"
                if fps > 30:
                    quality_text += f"{int(fps)}"
                
                format_text = f"{quality_text} [ {ext} ] {size_str} [ {vcodec} {fps} ]"
                video_formats.append((fmt['format_id'], format_text, fmt))
        
        # Remove duplicates and sort by quality
        unique_formats = []
        seen_qualities = set()
        
        for fmt_id, fmt_text, fmt_data in sorted(video_formats, key=lambda x: x[2].get('height', 0)):
            quality_key = (fmt_data.get('height'), fmt_data.get('ext'))
            if quality_key not in seen_qualities:
                seen_qualities.add(quality_key)
                unique_formats.append((fmt_id, fmt_text))
        
        # Create keyboard with video formats
        keyboard_buttons = []
        for fmt_id, fmt_text in unique_formats[-15:]:  # Show last 15 formats
            keyboard_buttons.append([InlineKeyboardButton(fmt_text, callback_data=f"video_{fmt_id}")])
        
        keyboard_buttons.append([InlineKeyboardButton("🔙 Go Back", callback_data="go_back")])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await callback_query.edit_message_text(
            "**Please select your required quality / format** 🦾",
            reply_markup=keyboard
        )

@app.on_callback_query(filters.regex("video_"))
async def handle_video_quality_selection(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    format_id = callback_query.data.split("_", 1)[1]
    
    if user_id not in user_data:
        await callback_query.answer("❌ Session expired. Please send the URL again.")
        return
    
    video_info = user_data[user_id]['info']
    
    # Find selected format
    selected_format = None
    for fmt in video_info.get('formats', []):
        if fmt['format_id'] == format_id:
            selected_format = fmt
            break
    
    if not selected_format:
        await callback_query.answer("❌ Format not found!")
        return
    
    # Show download confirmation
    height = selected_format.get('height', 'unknown')
    ext = selected_format.get('ext', 'mp4').upper()
    filesize = selected_format.get('filesize') or selected_format.get('filesize_approx', 0)
    size_str = format_filesize(filesize) if filesize else "unknown"
    vcodec = selected_format.get('vcodec', 'unknown')
    fps = selected_format.get('fps', 30)
    duration = format_duration(video_info.get('duration', 0))
    
    quality_text = f"{height}p"
    if fps > 30:
        quality_text += f"{int(fps)}"
    
    confirmation_text = f"""
**Selected Format:** {quality_text} [ {ext} ] {size_str} [ {vcodec} {fps} ]
**Upload Type:** Video

**YouTube Duration:** {duration}
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Get TG File", callback_data=f"download_{format_id}")],
        [InlineKeyboardButton("🔙 Go Back", callback_data="go_back")]
    ])
    
    await callback_query.edit_message_text(confirmation_text, reply_markup=keyboard)

@app.on_callback_query(filters.regex("download_"))
async def handle_download(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    format_id = callback_query.data.split("_", 1)[1]
    
    if user_id not in user_data:
        await callback_query.answer("❌ Session expired. Please send the URL again.")
        return
    
    await callback_query.edit_message_text("**Contacting YouTube to get 🕹 download details**")
    await download_media(callback_query, "video", format_id)

@app.on_callback_query(filters.regex("go_back"))
async def handle_go_back(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    if user_id not in user_data:
        await callback_query.answer("❌ Session expired. Please send the URL again.")
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 Audio", callback_data="format_audio")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="format_info")],
        [InlineKeyboardButton("📄 Document", callback_data="format_document")],
        [InlineKeyboardButton("🎬 Video", callback_data="format_video")]
    ])
    
    await callback_query.edit_message_text(
        "**Please select required format:** 😬",
        reply_markup=keyboard
    )

async def download_media(callback_query: CallbackQuery, media_type: str, format_id: str = None):
    user_id = callback_query.from_user.id
    url = user_data[user_id]['url']
    video_info = user_data[user_id]['info']
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Get original title for filename
        original_title = video_info.get('title', 'video')
        # Clean filename from invalid characters
        safe_title = "".join(c for c in original_title if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        
        # Configure yt-dlp options with anti-bot measures
        ydl_opts = create_robust_ydl_opts({
            'outtmpl': f'{temp_dir}/{safe_title}.%(ext)s',
        })
        
        if media_type == "audio":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': f'{temp_dir}/{safe_title}.%(ext)s',
            })
        elif media_type == "video" and format_id:
            ydl_opts['format'] = format_id
        elif media_type == "document":
            ydl_opts['format'] = 'best'
        
        # Download with retry mechanism
        max_download_retries = 2
        download_success = False
        
        for attempt in range(max_download_retries):
            try:
                if attempt > 0:
                    await callback_query.edit_message_text(f"📥 Download attempt {attempt + 1}/{max_download_retries}...")
                    # Rotate user agent for retry
                    ydl_opts['user_agent'] = random.choice(USER_AGENTS)
                    time.sleep(random.uniform(3, 6))
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    download_success = True
                    break
                    
            except Exception as e:
                if attempt == max_download_retries - 1:
                    raise e
                continue
        
        if not download_success:
            await callback_query.edit_message_text("❌ Download failed after multiple attempts!")
            return
        
        # Find downloaded file
        downloaded_files = []
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            if os.path.isfile(file_path):
                downloaded_files.append(file_path)
        
        if not downloaded_files:
            await callback_query.edit_message_text("❌ Download failed!")
            return
        
        main_file = downloaded_files[0]
        file_size = os.path.getsize(main_file)
        original_filename = os.path.basename(main_file)
        
        # Check if file needs to be split (>1GB)
        if file_size > 1024 * 1024 * 1024:  # 1GB
            await callback_query.edit_message_text("📁 File is large, splitting into parts...")
            split_files = await split_video(main_file)
            
            for i, part_file in enumerate(split_files):
                progress_text = f"📤 Uploading part {i+1}/{len(split_files)}..."
                await callback_query.edit_message_text(progress_text)
                
                # Create proper filename for parts
                name, ext = os.path.splitext(original_filename)
                part_filename = f"{name}_part{i+1}{ext}"
                
                if media_type == "audio":
                    await callback_query.message.reply_audio(
                        part_file,
                        file_name=part_filename,
                        title=f"{safe_title} - Part {i+1}"
                    )
                elif media_type == "document":
                    await callback_query.message.reply_document(
                        part_file,
                        file_name=part_filename
                    )
                else:
                    await callback_query.message.reply_video(
                        part_file,
                        file_name=part_filename
                    )
        else:
            await callback_query.edit_message_text("📤 Uploading file...")
            
            if media_type == "audio":
                await callback_query.message.reply_audio(
                    main_file,
                    file_name=original_filename,
                    title=safe_title,
                    performer=video_info.get('uploader', 'Unknown')
                )
            elif media_type == "document":
                await callback_query.message.reply_document(
                    main_file,
                    file_name=original_filename
                )
            else:
                await callback_query.message.reply_video(
                    main_file,
                    file_name=original_filename
                )
        
        await callback_query.edit_message_text("✅ Upload completed successfully!")
        
    except Exception as e:
        error_msg = str(e)
        if 'sign in to confirm' in error_msg.lower() or 'bot' in error_msg.lower():
            await callback_query.edit_message_text(
                "❌ **YouTube Bot Detection**\n\n"
                "YouTube has detected automated access. This is temporary.\n"
                "Please try again in a few minutes or contact admin for cookies setup."
            )
        else:
            await callback_query.edit_message_text(f"❌ Error during download: {str(e)}")
    
    finally:
        # Clean up temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)
        # Clear user data
        if user_id in user_data:
            del user_data[user_id]

if __name__ == "__main__":
    app.run()
