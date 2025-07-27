import os
import asyncio
import math
import random
import time
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import yt_dlp
from dotenv import load_dotenv
import tempfile
import shutil
import json
import requests
from fake_useragent import UserAgent

load_dotenv()

app = Client(
    "youtube_dl_bot",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

# Store user selections temporarily
user_data = {}

# Initialize user agent generator
try:
    ua = UserAgent()
except:
    ua = None

# Professional user agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
]

def get_random_user_agent():
    """Get a random user agent"""
    if ua:
        try:
            return ua.random
        except:
            pass
    return random.choice(USER_AGENTS)

def validate_youtube_url(url):
    """Validate and clean YouTube URL"""
    # Remove extra whitespace and common prefixes
    url = url.strip()
    
    # YouTube URL patterns
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}", True
    
    return url, False

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
        'user_agent': get_random_user_agent(),
        'sleep_interval': random.uniform(1, 3),
        'max_sleep_interval': 5,
        'extractor_retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': True,
        'ignoreerrors': False,
        'no_check_certificate': True,
        'prefer_insecure': False,
        # Enhanced anti-detection measures
        'referer': 'https://www.youtube.com/',
        'origin': 'https://www.youtube.com',
        # Updated YouTube-specific client options for 2024
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'android', 'ios'],
                'player_skip': ['configs', 'webpage'],
                'skip': ['translated_subs'],
                'include_live_dash': False,
                'include_hls': False
            }
        },
        'http_headers': {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'X-YouTube-Client-Name': '1',
            'X-YouTube-Client-Version': '2.20240201.01.00',
        }
    }
    
    # Add cookies if available
    cookies_path = get_cookies_path()
    if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
        base_opts['cookiefile'] = cookies_path
    
    if additional_opts:
        base_opts.update(additional_opts)
    
    return base_opts

def get_video_info_with_fallback(url, retry_count=0):
    """Fallback method with different strategies for app availability errors"""
    strategies = [
        # Strategy 1: Latest Web client (2024)
        {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                    'player_skip': ['configs'],
                    'skip': ['dash', 'hls', 'translated_subs'],
                    'include_live_dash': False
                }
            },
            'http_headers': {
                'X-YouTube-Client-Name': '1',
                'X-YouTube-Client-Version': '2.20240201.01.00',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://www.youtube.com',
                'Referer': 'https://www.youtube.com/'
            }
        },
        # Strategy 2: Android client with latest version
        {
            'user_agent': 'com.google.android.youtube/18.11.34 (Linux; U; Android 13; SM-G998B) gzip',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                    'player_skip': ['webpage', 'configs'],
                    'skip': ['translated_subs']
                }
            },
            'http_headers': {
                'X-YouTube-Client-Name': '3',
                'X-YouTube-Client-Version': '18.11.34',
                'User-Agent': 'com.google.android.youtube/18.11.34 (Linux; U; Android 13; SM-G998B) gzip'
            }
        },
        # Strategy 3: iOS client with latest version
        {
            'user_agent': 'com.google.ios.youtube/18.11.2 (iPhone15,2; U; CPU iOS 16_4 like Mac OS X)',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios'],
                    'player_skip': ['webpage', 'configs'],
                    'skip': ['translated_subs']
                }
            },
            'http_headers': {
                'X-YouTube-Client-Name': '5',
                'X-YouTube-Client-Version': '18.11.2',
                'User-Agent': 'com.google.ios.youtube/18.11.2 (iPhone15,2; U; CPU iOS 16_4 like Mac OS X)'
            }
        },
        # Strategy 4: Android Music client (often bypasses restrictions)
        {
            'user_agent': 'com.google.android.apps.youtube.music/5.16.51 (Linux; U; Android 11; Pixel 5)',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_music'],
                    'player_skip': ['webpage', 'configs'],
                    'skip': ['dash', 'hls', 'translated_subs']
                }
            },
            'http_headers': {
                'X-YouTube-Client-Name': '21',
                'X-YouTube-Client-Version': '5.16.51',
                'User-Agent': 'com.google.android.apps.youtube.music/5.16.51 (Linux; U; Android 11; Pixel 5)'
            }
        },
        # Strategy 5: Web embedded player (last resort)
        {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['web_embedded_player'],
                    'player_skip': ['webpage', 'configs', 'js'],
                    'skip': ['dash', 'hls', 'translated_subs']
                }
            },
            'http_headers': {
                'X-YouTube-Client-Name': '56',
                'X-YouTube-Client-Version': '1.20240201.01.00',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'X-YouTube-Identity-Token': '',
                'Referer': f'https://www.youtube.com/embed/{url.split("v=")[-1].split("&")[0] if "v=" in url else url.split("/")[-1]}'
            }
        }
    ]
    
    for i, strategy in enumerate(strategies):
        if retry_count > i:
            continue
            
        try:
            # Longer delay for app availability issues
            time.sleep(random.uniform(3, 8))
            ydl_opts = create_robust_ydl_opts(strategy)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Log the specific error for debugging
            print(f"Strategy {i+1} failed: {error_msg[:100]}...")
            
            if 'not available on this app' in error_msg:
                # Try next strategy for app availability errors
                continue
            elif 'player response' in error_msg:
                # Try next strategy for player response errors
                continue
            elif '403' in error_msg or 'forbidden' in error_msg:
                # Try next strategy for 403 errors
                continue
            elif 'format' in error_msg:
                # Try with basic format selection
                try:
                    basic_opts = create_robust_ydl_opts({
                        'format': 'best/worst',
                        'user_agent': strategy.get('user_agent', get_random_user_agent()),
                        'extractor_args': strategy.get('extractor_args', {})
                    })
                    with yt_dlp.YoutubeDL(basic_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        return info
                except:
                    continue
            else:
                continue
    
    return None

def get_video_info(url, retry_count=0):
    """Extract video information with robust error handling"""
    max_retries = 5  # Increased retries for app availability issues
    
    if retry_count >= max_retries:
        return None
    
    try:
        # Add random delay between retries
        if retry_count > 0:
            time.sleep(random.uniform(3, 8))
        
        ydl_opts = create_robust_ydl_opts()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
            
    except yt_dlp.utils.ExtractorError as e:
        error_msg = str(e).lower()
        
        if any(phrase in error_msg for phrase in ['not available on this app', 'player response', 'sign in to confirm', 'bot']):
            # Handle app availability and other detection specifically
            if retry_count < max_retries - 1:
                return get_video_info_with_fallback(url, retry_count + 1)
        
        return None
    except Exception as e:
        error_msg = str(e).lower()
        if any(phrase in error_msg for phrase in ['not available on this app', 'player response']) and retry_count < max_retries - 1:
            return get_video_info_with_fallback(url, retry_count + 1)
        elif retry_count < max_retries - 1:
            return get_video_info(url, retry_count + 1)
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

**Supported URL formats:**
• `https://www.youtube.com/watch?v=VIDEO_ID`
• `https://youtu.be/VIDEO_ID`
• `https://www.youtube.com/shorts/VIDEO_ID`

Just send me a YouTube URL to get started!
"""
    await message.reply_text(welcome_text)

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_url(client, message):
    original_url = message.text.strip()
    
    # Validate and clean YouTube URL
    cleaned_url, is_valid = validate_youtube_url(original_url)
    
    if not is_valid:
        await message.reply_text(
            "❌ **Invalid YouTube URL!**\n\n"
            "Please send a valid YouTube URL in one of these formats:\n"
            "• `https://www.youtube.com/watch?v=VIDEO_ID`\n"
            "• `https://youtu.be/VIDEO_ID`\n"
            "• `https://www.youtube.com/shorts/VIDEO_ID`\n\n"
            "**Example:** `https://www.youtube.com/watch?v=dQw4w9WgXcQ`"
        )
        return
    
    progress_msg = await message.reply_text("🔍 Analyzing video...")
    
    # Try multiple times with different strategies (increased attempts)
    video_info = None
    status_messages = [
        "🔍 Analyzing video...",
        "🔍 Analyzing video... (Using web client)",
        "🔍 Analyzing video... (Using Android client)",
        "🔍 Analyzing video... (Using iOS client)", 
        "🔍 Analyzing video... (Using music client)",
        "🔍 Analyzing video... (Final attempt with embed)"
    ]
    
    for attempt in range(5):  # Increased from 4 to 5
        if attempt > 0:
            await progress_msg.edit_text(f"{status_messages[min(attempt, len(status_messages)-1)]}")
        
        video_info = get_video_info(cleaned_url, attempt)
        if video_info:
            break
        
        # Longer wait before next attempt for app availability issues
        await asyncio.sleep(4)
    
    if not video_info:
        error_text = """
❌ **Failed to extract video information**

**Most likely causes:**
• 🚫 **App Restriction Error** ("content not available on this app")
• 🔒 **YouTube API changes** (client version outdated)
• 🤖 **Enhanced bot detection** (IP/user-agent blocked)
• 🌍 **Regional restrictions** (video not available in your area)
• 🔞 **Age restrictions** (requires sign-in)
• 🚫 **Video is private/deleted**

**Professional Solutions:**
1. 🍪 **Setup fresh cookies** (most effective - contact admin)
2. ⚡ **Update yt-dlp** (admin: `pip install -U yt-dlp`)
3. 🔄 **Try again in 30-60 minutes** (temporary blocks)
4. 🌐 **Use VPN** (if regionally blocked)
5. 📱 **Try different video** (test if bot-wide issue)
6. 🎵 **Try audio-only content** (often less restricted)

💡 **Technical Note:** "Not available on this app" errors indicate YouTube is blocking older client versions. Fresh cookies + updated yt-dlp usually resolve this.
"""
        await progress_msg.edit_text(error_text)
        return
    
    # Store video info for user
    user_data[message.from_user.id] = {
        'url': cleaned_url,
        'info': video_info
    }
    
    # Create format selection keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 Audio", callback_data="format_audio")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="format_info")],
        [InlineKeyboardButton("📄 Document", callback_data="format_document")],
        [InlineKeyboardButton("🎬 Video", callback_data="format_video")]
    ])
    
    title = video_info.get('title', 'Unknown Title')[:50]
    await progress_msg.edit_text(
        f"✅ **Video Found:** {title}...\n\n**Please select required format:** 😬",
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
        # Show video quality options with better error handling
        formats = video_info.get('formats', [])
        video_formats = []
        
        # Filter and validate formats
        for fmt in formats:
            try:
                if fmt.get('vcodec') != 'none' and fmt.get('height') and fmt.get('url'):
                    height = fmt.get('height')
                    ext = fmt.get('ext', 'mp4').upper()
                    filesize = fmt.get('filesize') or fmt.get('filesize_approx', 0)
                    size_str = format_filesize(filesize) if filesize else "~unknown"
                    vcodec = fmt.get('vcodec', 'unknown')[:12]  # Truncate long codec names
                    fps = fmt.get('fps', 30)
                    
                    # Skip problematic formats
                    if 'storyboard' in str(fmt.get('format_note', '')).lower():
                        continue
                    
                    quality_text = f"{height}p"
                    if fps > 30:
                        quality_text += f"{int(fps)}"
                    
                    format_text = f"{quality_text} [ {ext} ] {size_str} [ {vcodec} {fps} ]"
                    video_formats.append((fmt['format_id'], format_text, fmt))
            except Exception:
                continue  # Skip problematic formats
        
        if not video_formats:
            await callback_query.edit_message_text(
                "❌ **No video formats available**\n\n"
                "This might be due to:\n"
                "• Regional restrictions\n"
                "• Age restrictions\n"
                "• YouTube blocking access\n\n"
                "Try selecting **Audio** or **Document** format instead."
            )
            return
        
        # Sort by quality and remove duplicates
        unique_formats = []
        seen_qualities = set()
        
        for fmt_id, fmt_text, fmt_data in sorted(video_formats, key=lambda x: x[2].get('height', 0)):
            quality_key = (fmt_data.get('height'), fmt_data.get('ext'))
            if quality_key not in seen_qualities:
                seen_qualities.add(quality_key)
                unique_formats.append((fmt_id, fmt_text))
        
        # Create keyboard with video formats (show best options first)
        keyboard_buttons = []
        for fmt_id, fmt_text in unique_formats[-15:]:  # Show last 15 formats (highest quality)
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
        safe_title = "".join(c for c in original_title if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        
        # Configure yt-dlp options with enhanced anti-detection for 2024
        ydl_opts = create_robust_ydl_opts({
            'outtmpl': f'{temp_dir}/{safe_title}.%(ext)s',
            'retries': 20,  # Increased retries for app availability issues
            'file_access_retries': 20,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android', 'ios', 'android_music'],
                    'player_skip': ['configs', 'webpage'],
                    'skip': ['translated_subs'] if media_type != 'audio' else ['dash', 'hls', 'translated_subs'],
                    'include_live_dash': False,
                    'include_hls': False
                }
            }
        })
        
        if media_type == "audio":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        elif media_type == "video" and format_id:
            # Enhanced format validation with fallbacks
            available_formats = [f['format_id'] for f in video_info.get('formats', [])]
            if format_id in available_formats:
                ydl_opts['format'] = f'{format_id}/best[height<=720]/best/worst'
            else:
                ydl_opts['format'] = 'best[height<=720]/best/worst'
        elif media_type == "document":
            ydl_opts['format'] = 'best/worst'
        
        # Enhanced download with multiple client fallbacks for 2024
        max_download_retries = 5  # Increased from 4
        download_success = False
        last_error = None
        
        client_strategies = ['web', 'android', 'ios', 'android_music', 'web_embedded_player']
        
        for attempt in range(max_download_retries):
            try:
                if attempt > 0:
                    client_type = client_strategies[min(attempt, len(client_strategies)-1)]
                    await callback_query.edit_message_text(
                        f"📥 Download attempt {attempt + 1}/{max_download_retries}...\n"
                        f"🔄 Using {client_type} client to bypass app restrictions"
                    )
                    
                    # Update client strategy with latest versions
                    ydl_opts['extractor_args']['youtube']['player_client'] = [client_type]
                    
                    # Update client-specific headers
                    if client_type == 'android':
                        ydl_opts['user_agent'] = 'com.google.android.youtube/18.11.34 (Linux; U; Android 13; SM-G998B) gzip'
                        ydl_opts['http_headers']['X-YouTube-Client-Name'] = '3'
                        ydl_opts['http_headers']['X-YouTube-Client-Version'] = '18.11.34'
                    elif client_type == 'ios':
                        ydl_opts['user_agent'] = 'com.google.ios.youtube/18.11.2 (iPhone15,2; U; CPU iOS 16_4 like Mac OS X)'
                        ydl_opts['http_headers']['X-YouTube-Client-Name'] = '5'
                        ydl_opts['http_headers']['X-YouTube-Client-Version'] = '18.11.2'
                    elif client_type == 'android_music':
                        ydl_opts['user_agent'] = 'com.google.android.apps.youtube.music/5.16.51 (Linux; U; Android 11; Pixel 5)'
                        ydl_opts['http_headers']['X-YouTube-Client-Name'] = '21'
                        ydl_opts['http_headers']['X-YouTube-Client-Version'] = '5.16.51'
                    elif client_type == 'web_embedded_player':
                        ydl_opts['user_agent'] = get_random_user_agent()
                        ydl_opts['http_headers']['X-YouTube-Client-Name'] = '56'
                        ydl_opts['http_headers']['X-YouTube-Client-Version'] = '1.20240201.01.00'
                    else:  # web
                        ydl_opts['user_agent'] = get_random_user_agent()
                        ydl_opts['http_headers']['X-YouTube-Client-Name'] = '1'
                        ydl_opts['http_headers']['X-YouTube-Client-Version'] = '2.20240201.01.00'
                    
                    ydl_opts['sleep_interval'] = random.uniform(8, 15)
                    
                    # Simulate different IP
                    ydl_opts['http_headers']['X-Forwarded-For'] = f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}'
                    
                    time.sleep(random.uniform(8, 15))
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    download_success = True
                    break
                    
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                if 'not available on this app' in error_msg:
                    # Specific handling for app availability errors
                    if attempt < max_download_retries - 1:
                        await callback_query.edit_message_text(
                            f"⚠️ App restriction error. Switching to {client_strategies[min(attempt+1, len(client_strategies)-1)]} client...\n"
                            f"Attempt {attempt + 1}/{max_download_retries}"
                        )
                        continue
                elif 'player response' in error_msg:
                    # Specific handling for player response errors
                    if attempt < max_download_retries - 1:
                        await callback_query.edit_message_text(
                            f"⚠️ Player response error. Switching to {client_strategies[min(attempt+1, len(client_strategies)-1)]} client...\n"
                            f"Attempt {attempt + 1}/{max_download_retries}"
                        )
                        continue
                elif '403' in error_msg or 'forbidden' in error_msg:
                    # Specific handling for 403 errors
                    if attempt < max_download_retries - 1:
                        await callback_query.edit_message_text(
                            f"⚠️ Access denied (403). Trying alternative method...\n"
                            f"Attempt {attempt + 1}/{max_download_retries}"
                        )
                        continue
                elif 'format' in error_msg and 'not available' in error_msg:
                    # Handle format not available
                    if attempt < max_download_retries - 1:
                        ydl_opts['format'] = 'best/worst'  # Fallback to any available format
                        continue
                
                if attempt == max_download_retries - 1:
                    raise e
        
        if not download_success:
            error_text = "❌ **Download failed after multiple attempts**\n\n"
            if last_error:
                error_msg = str(last_error).lower()
                if 'not available on this app' in error_msg:
                    error_text += "**Reason:** Content not available on app clients\n\n"
                    error_text += "**Solutions:**\n"
                    error_text += "• 🍪 **Critical:** Ask admin to setup fresh browser cookies\n"
                    error_text += "• ⚡ **Update:** Admin should update yt-dlp (`pip install -U yt-dlp`)\n"
                    error_text += "• ⏰ **Wait:** Try again in 1-2 hours\n"
                    error_text += "• 🎵 **Alternative:** Try Audio format (less restricted)\n"
                    error_text += "• 🌐 **VPN:** Use different IP/region\n\n"
                    error_text += "💡 **Note:** This error means YouTube is blocking older client versions."
                elif 'player response' in error_msg:
                    error_text += "**Reason:** YouTube player response extraction failed\n\n"
                    error_text += "**Solutions:**\n"
                    error_text += "• 🍪 **Critical:** Ask admin to setup fresh cookies\n"
                    error_text += "• ⚡ **Update:** Admin should update yt-dlp (`pip install -U yt-dlp`)\n"
                    error_text += "• ⏰ **Wait:** Try again in 30-60 minutes\n"
                    error_text += "• 🎵 **Alternative:** Try Audio format (often works better)\n"
                    error_text += "• 🌐 **VPN:** Use different IP address\n\n"
                    error_text += "💡 **Note:** This error indicates YouTube has updated their anti-bot systems."
                elif '403' in error_msg:
                    error_text += "**Reason:** YouTube blocked access (403 Forbidden)\n\n"
                    error_text += "**Solutions:**\n"
                    error_text += "• 🍪 Ask admin to setup cookies\n"
                    error_text += "• ⏰ Try again in 10-15 minutes\n"
                    error_text += "• 🎵 Try Audio format instead\n"
                    error_text += "• 🌐 Video might be region-blocked"
                elif 'format' in error_msg:
                    error_text += "**Reason:** Requested format not available\n\n"
                    error_text += "**Solutions:**\n"
                    error_text += "• 📄 Try Document format\n"
                    error_text += "• 🎵 Try Audio format\n"
                    error_text += "• 📹 Select a different video quality"
                else:
                    error_text += f"**Error:** {str(last_error)[:200]}..."
            
            await callback_query.edit_message_text(error_text)
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
        if 'not available on this app' in error_msg.lower():
            await callback_query.edit_message_text(
                "❌ **Content Not Available on App**\n\n"
                "**Critical Issue:** YouTube is blocking app-based access to this content.\n\n"
                "**Immediate Solutions:**\n"
                "🍪 **Most Important:** Contact admin to setup fresh browser cookies\n"
                "⚡ **Update Required:** Admin needs to update yt-dlp to latest version\n"
                "⏰ **Temporary Fix:** Wait 2-3 hours and try again\n"
                "🎵 **Alternative:** Try Audio download (may still work)\n"
                "🌐 **VPN Solution:** Try different IP address/region\n\n"
                "💡 **Technical:** This error indicates YouTube updated their client restrictions. Browser cookies bypass this completely."
            )
        elif 'player response' in error_msg.lower():
            await callback_query.edit_message_text(
                "❌ **YouTube Player Response Error**\n\n"
                "**Critical Issue:** YouTube has updated their anti-bot systems.\n\n"
                "**Immediate Solutions:**\n"
                "🍪 **Most Important:** Contact admin to setup fresh browser cookies\n"
                "⚡ **Update Required:** Admin needs to update yt-dlp library\n"
                "⏰ **Temporary Fix:** Wait 1-2 hours and try again\n"
                "🎵 **Alternative:** Try Audio download (may still work)\n"
                "🌐 **VPN Solution:** Try different IP address/region\n\n"
                "💡 **Technical:** This error indicates YouTube updated their player API. Fresh cookies from a real browser session usually fix this."
            )
        elif '403' in error_msg.lower() or 'forbidden' in error_msg.lower():
            await callback_query.edit_message_text(
                "❌ **YouTube Access Blocked (403 Forbidden)**\n\n"
                "**This happens when:**\n"
                "• YouTube detects automated access\n"
                "• IP address is temporarily blocked\n"
                "• Video has restrictions\n\n"
                "**Solutions:**\n"
                "🍪 **Best:** Ask admin to setup browser cookies\n"
                "⏰ **Wait:** Try again in 15-30 minutes\n"
                "🎵 **Alternative:** Try Audio download\n"
                "🌐 **VPN:** Video might be region-blocked\n\n"
                "💡 Cookies bypass most YouTube restrictions!"
            )
        else:
            await callback_query.edit_message_text(f"❌ Error during download: {str(e)[:300]}...")
    
    finally:
        # Clean up temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)
        # Clear user data
        if user_id in user_data:
            del user_data[user_id]

if __name__ == "__main__":
    app.run()
