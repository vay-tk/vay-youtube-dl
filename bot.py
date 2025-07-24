import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
import yt_dlp
from dotenv import load_dotenv
import subprocess
import json
import tempfile
import shutil
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8000))

app = Client("youtube_dl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Storage for user sessions
user_sessions = {}

# Use temp directory for Railway
DOWNLOAD_DIR = tempfile.mkdtemp()

# Health check server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "bot": "running"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_health_server():
    """Start health check server in a separate thread"""
    try:
        server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
        print(f"Health check server started on port {PORT}")
        server.serve_forever()
    except Exception as e:
        print(f"Health server error: {e}")

def cleanup_temp_files():
    """Clean up old temporary files"""
    try:
        if os.path.exists(DOWNLOAD_DIR):
            for file in os.listdir(DOWNLOAD_DIR):
                file_path = os.path.join(DOWNLOAD_DIR, file)
                if os.path.isfile(file_path):
                    # Remove files older than 1 hour
                    if os.path.getmtime(file_path) < (time.time() - 3600):
                        os.remove(file_path)
    except Exception:
        pass

def get_video_info(url):
    """Extract video information using yt-dlp"""
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        return None

def format_duration(seconds):
    """Convert seconds to readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes} minutes {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def get_format_keyboard():
    """Create format selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎵 Audio", callback_data="format_audio")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="format_info")],
        [InlineKeyboardButton("📝 Subtitle", callback_data="format_subtitle")],
        [InlineKeyboardButton("🎭 Animation", callback_data="format_animation")],
        [InlineKeyboardButton("📄 Document", callback_data="format_document")],
        [InlineKeyboardButton("🎥 Video", callback_data="format_video")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_video_quality_keyboard(formats):
    """Create video quality selection keyboard"""
    keyboard = []
    
    # Add storyboard formats (if any)
    storyboard_formats = [f for f in formats if f.get('format_note') == 'storyboard']
    for fmt in storyboard_formats[:3]:  # Limit to 3 storyboard formats
        keyboard.append([InlineKeyboardButton(
            f"storyboard [ MHTML ] [ none {fmt.get('fps', 'unknown')} ]",
            callback_data=f"quality_{fmt['format_id']}"
        )])
    
    # Add video formats
    video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('height')]
    seen_qualities = set()
    
    for fmt in sorted(video_formats, key=lambda x: x.get('height', 0)):
        height = fmt.get('height')
        if not height or height in seen_qualities:
            continue
        seen_qualities.add(height)
        
        ext = fmt.get('ext', 'unknown').upper()
        filesize = fmt.get('filesize') or fmt.get('filesize_approx', 0)
        filesize_str = f"{filesize / (1024*1024):.2f} MiB" if filesize else "unknown size"
        vcodec = fmt.get('vcodec', 'unknown')
        fps = fmt.get('fps', 30)
        
        button_text = f"{height}p [ {ext} ] {filesize_str} [ {vcodec} {fps} ]"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"quality_{fmt['format_id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Go Back", callback_data="go_back")])
    return InlineKeyboardMarkup(keyboard)

def get_audio_quality_keyboard(formats):
    """Create audio quality selection keyboard"""
    keyboard = []
    
    # Filter audio formats
    audio_formats = [f for f in formats if f.get('acodec') != 'none' and not f.get('vcodec')]
    
    for fmt in sorted(audio_formats, key=lambda x: x.get('abr', 0), reverse=True):
        abr = fmt.get('abr', 'unknown')
        ext = fmt.get('ext', 'unknown').upper()
        filesize = fmt.get('filesize') or fmt.get('filesize_approx', 0)
        filesize_str = f"{filesize / (1024*1024):.2f} MiB" if filesize else "unknown size"
        acodec = fmt.get('acodec', 'unknown')
        
        button_text = f"🎵 {abr}kbps [ {ext} ] {filesize_str} [ {acodec} ]"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"quality_{fmt['format_id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Go Back", callback_data="go_back")])
    return InlineKeyboardMarkup(keyboard)

def get_subtitle_keyboard(subtitles):
    """Create subtitle selection keyboard"""
    keyboard = []
    
    if subtitles:
        for lang_code, sub_formats in subtitles.items():
            for sub_format in sub_formats:
                if sub_format.get('ext'):
                    lang_name = sub_format.get('name', lang_code)
                    ext = sub_format.get('ext').upper()
                    button_text = f"📝 {lang_name} [{ext}]"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"subtitle_{lang_code}_{ext.lower()}")])
    else:
        keyboard.append([InlineKeyboardButton("❌ No subtitles available", callback_data="no_subtitles")])
    
    keyboard.append([InlineKeyboardButton("🔙 Go Back", callback_data="go_back")])
    return InlineKeyboardMarkup(keyboard)

def get_animation_quality_keyboard(formats):
    """Create animation/GIF quality selection keyboard"""
    keyboard = []
    
    # Filter for video formats suitable for animation
    video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('height')]
    
    for fmt in sorted(video_formats, key=lambda x: x.get('height', 0)):
        height = fmt.get('height')
        ext = fmt.get('ext', 'unknown').upper()
        filesize = fmt.get('filesize') or fmt.get('filesize_approx', 0)
        filesize_str = f"{filesize / (1024*1024):.2f} MiB" if filesize else "unknown size"
        
        button_text = f"🎭 {height}p [ {ext} ] {filesize_str}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"quality_{fmt['format_id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Go Back", callback_data="go_back")])
    return InlineKeyboardMarkup(keyboard)

def get_download_options_keyboard():
    """Create download options keyboard after format selection"""
    keyboard = [
        [InlineKeyboardButton("✅ Get TG File", callback_data="download_file")],
        [InlineKeyboardButton("✂️ trim video 🎮", callback_data="trim_video")],
        [InlineKeyboardButton("🔙 Go Back", callback_data="select_quality")]
    ]
    return InlineKeyboardMarkup(keyboard)

def check_ffmpeg():
    """Check if FFmpeg is available - should work on Railway with Dockerfile"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

@app.on_message(filters.command("start"))
async def start_command(client, message):
    # Clean up temp files on start
    cleanup_temp_files()
    
    await message.reply_text(
        "🎬 **YouTube Downloader Bot**\n\n"
        "Send me a YouTube URL to get started!\n\n"
        "🚀 *Running on Railway Cloud*",
        reply_markup=None
    )

@app.on_message(filters.text & filters.regex(r'^\d{2}:\d{2}:\d{2}$'))
async def handle_time_input(client, message):
    user_id = message.from_user.id
    
    if user_id not in user_sessions:
        return
    
    session = user_sessions[user_id]
    
    if session.get('awaiting_trim_start'):
        session['trim_start'] = message.text
        session['awaiting_trim_start'] = False
        session['awaiting_trim_end'] = True
        
        await message.reply_text(
            f"✅ Start time set: `{message.text}`\n\n"
            "Now enter the **end time** in format: `HH:MM:SS`\n"
            "Example: `00:03:00` for 3 minutes"
        )
    
    elif session.get('awaiting_trim_end'):
        session['trim_end'] = message.text
        session['awaiting_trim_end'] = False
        
        await message.reply_text(
            f"✂️ **Trimming Settings:**\n"
            f"Start: `{session['trim_start']}`\n"
            f"End: `{message.text}`\n\n"
            "🔄 Processing trimmed video..."
        )
        
        await trim_and_send_video(message, session)

@app.on_message(filters.text & ~filters.command(["start"]) & ~filters.regex(r'^\d{2}:\d{2}:\d{2}$'))
async def handle_url(client, message):
    url = message.text.strip()
    
    # Basic YouTube URL validation
    if not ("youtube.com" in url or "youtu.be" in url):
        await message.reply_text("❌ Please send a valid YouTube URL!")
        return
    
    status_msg = await message.reply_text("🔍 Analyzing video...")
    
    try:
        video_info = get_video_info(url)
        if not video_info:
            await status_msg.edit_text("❌ Failed to analyze video. Please check the URL.")
            return
        
        user_sessions[message.from_user.id] = {
            'url': url,
            'video_info': video_info,
            'selected_format': None,
            'selected_quality': None
        }
        
        await status_msg.edit_text(
            f"🎬 **{video_info.get('title', 'Unknown Title')}**\n\n"
            f"⏱ Duration: {format_duration(video_info.get('duration', 0))}\n"
            f"👁 Views: {video_info.get('view_count', 'Unknown'):,}\n\n"
            "please select, required format: 😬",
            reply_markup=get_format_keyboard()
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

@app.on_callback_query()
async def handle_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Answer callback query first to prevent timeout
    try:
        await callback_query.answer()
    except Exception:
        pass  # Ignore if already answered or expired
    
    if user_id not in user_sessions:
        try:
            await callback_query.edit_message_text("❌ Session expired. Please send the URL again.")
        except Exception:
            await callback_query.message.reply_text("❌ Session expired. Please send the URL again.")
        return
    
    session = user_sessions[user_id]
    
    try:
        if data == "format_video":
            formats = session['video_info'].get('formats', [])
            session['selected_format'] = 'video'
            
            await callback_query.edit_message_text(
                "please select your required quality / format 🦾",
                reply_markup=get_video_quality_keyboard(formats)
            )
        
        elif data == "format_audio":
            formats = session['video_info'].get('formats', [])
            session['selected_format'] = 'audio'
            
            await callback_query.edit_message_text(
                "🎵 **Audio Download**\n\nplease select your required quality / format 🦾",
                reply_markup=get_audio_quality_keyboard(formats)
            )
        
        elif data == "format_info":
            session['selected_format'] = 'info'
            video_info = session['video_info']
            
            info_text = f"ℹ️ **Video Information**\n\n"
            info_text += f"📝 **Title:** {video_info.get('title', 'Unknown')}\n"
            info_text += f"👤 **Uploader:** {video_info.get('uploader', 'Unknown')}\n"
            info_text += f"⏱ **Duration:** {format_duration(video_info.get('duration', 0))}\n"
            info_text += f"👁 **Views:** {video_info.get('view_count', 'Unknown'):,}\n"
            info_text += f"👍 **Likes:** {video_info.get('like_count', 'Unknown'):,}\n"
            info_text += f"📅 **Upload Date:** {video_info.get('upload_date', 'Unknown')}\n"
            info_text += f"📋 **Description:** {video_info.get('description', 'No description')[:200]}...\n"
            info_text += f"🔗 **URL:** {session['url']}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Go Back", callback_data="go_back")]]
            
            await callback_query.edit_message_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "format_subtitle":
            subtitles = session['video_info'].get('subtitles', {})
            auto_captions = session['video_info'].get('automatic_captions', {})
            all_subtitles = {**subtitles, **auto_captions}
            session['selected_format'] = 'subtitle'
            
            await callback_query.edit_message_text(
                "📝 **Subtitle Download**\n\nplease select your required language / format 🦾",
                reply_markup=get_subtitle_keyboard(all_subtitles)
            )
        
        elif data == "format_animation":
            formats = session['video_info'].get('formats', [])
            session['selected_format'] = 'animation'
            
            await callback_query.edit_message_text(
                "🎭 **Animation Download**\n\nplease select your required quality / format 🦾",
                reply_markup=get_animation_quality_keyboard(formats)
            )
        
        elif data == "format_document":
            session['selected_format'] = 'document'
            formats = session['video_info'].get('formats', [])
            
            await callback_query.edit_message_text(
                "📄 **Document Download**\n\nplease select your required quality / format 🦾",
                reply_markup=get_video_quality_keyboard(formats)
            )
        
        elif data.startswith("quality_"):
            format_id = data.split("_", 1)[1]
            session['selected_quality'] = format_id
            
            # Find the selected format
            selected_fmt = None
            for fmt in session['video_info']['formats']:
                if fmt['format_id'] == format_id:
                    selected_fmt = fmt
                    break
            
            if selected_fmt:
                height = selected_fmt.get('height', 'unknown')
                ext = selected_fmt.get('ext', 'unknown').upper()
                filesize = selected_fmt.get('filesize') or selected_fmt.get('filesize_approx', 0)
                filesize_str = f"{filesize / (1024*1024):.2f} MiB" if filesize else "unknown size"
                vcodec = selected_fmt.get('vcodec', 'unknown')
                fps = selected_fmt.get('fps', 30)
                duration = session['video_info'].get('duration', 0)
                
                format_text = f"{height}p [ {ext} ] {filesize_str} [ {vcodec} {fps} ]"
                
                # Add file size warning for large files
                warning_text = ""
                if filesize > 2000 * 1024 * 1024:  # > 2GB
                    warning_text = "\n⚠️ **Large File Warning**: This file is over 2GB. Consider compression or splitting."
                elif filesize > 50 * 1024 * 1024:  # > 50MB
                    warning_text = "\n⚠️ **Note**: Large file - upload may take time."
                
                await callback_query.edit_message_text(
                    f"**Selected Format:** {format_text}\n"
                    f"**Upload Type:** {session['selected_format'].title()}\n"
                    f"**YouTube Duration:** {format_duration(duration)}\n{warning_text}",
                    reply_markup=get_download_options_keyboard()
                )
        
        elif data.startswith("subtitle_"):
            parts = data.split("_")
            lang_code = parts[1]
            sub_format = parts[2]
            session['selected_quality'] = f"{lang_code}_{sub_format}"
            
            await callback_query.edit_message_text(
                f"**Selected Format:** Subtitle - {lang_code.upper()} [{sub_format.upper()}]\n"
                f"**Upload Type:** Document\n\n"
                f"**YouTube Duration:** {format_duration(session['video_info'].get('duration', 0))}\n",
                reply_markup=get_download_options_keyboard()
            )
        
        elif data == "download_file":
            await callback_query.edit_message_text("🔄 contacting YouTube to get 🕹 download details")
            await download_and_send(callback_query, session)
        
        elif data == "trim_video":
            # Check if FFmpeg is available
            if not check_ffmpeg():
                await callback_query.edit_message_text(
                    "❌ **FFmpeg not found!**\n\n"
                    "Video trimming requires FFmpeg to be installed.\n\n"
                    "**Installation Instructions:**\n"
                    "1. Download FFmpeg from: https://ffmpeg.org/download.html\n"
                    "2. Extract and add to system PATH\n"
                    "3. Restart the bot\n\n"
                    "Or use **Get TG File** to download without trimming.",
                    reply_markup=get_download_options_keyboard()
                )
                return
            
            session['awaiting_trim_start'] = True
            await callback_query.edit_message_text(
                "✂️ **Video Trimming**\n\n"
                "Please enter the **start time** in format: `HH:MM:SS`\n"
                "Example: `00:01:30` for 1 minute 30 seconds"
            )
        
        elif data == "go_back":
            await callback_query.edit_message_text(
                "please select, required format: 😬",
                reply_markup=get_format_keyboard()
            )
        
        elif data == "select_quality":
            formats = session['video_info'].get('formats', [])
            await callback_query.edit_message_text(
                "please select your required quality / format 🦾",
                reply_markup=get_video_quality_keyboard(formats)
            )
            
    except Exception as e:
        # If editing fails, send a new message
        try:
            await callback_query.message.reply_text(f"❌ Error: {str(e)}")
        except Exception:
            pass

async def download_and_send(callback_query, session):
    """Download and send the video file"""
    try:
        url = session['url']
        format_id = session['selected_quality']
        selected_format = session['selected_format']
        
        # Use temp directory
        download_dir = DOWNLOAD_DIR
        
        # Clean up before download
        cleanup_temp_files()
        
        if selected_format == 'subtitle':
            # Handle subtitle download
            lang_code, sub_format = format_id.split('_')
            
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [lang_code],
                'subtitlesformat': sub_format,
                'skip_download': True,
                'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
            # Find subtitle file
            subtitle_file = None
            for file in os.listdir(download_dir):
                if file.endswith(f'.{lang_code}.{sub_format}'):
                    subtitle_file = os.path.join(download_dir, file)
                    break
            
            if subtitle_file and os.path.exists(subtitle_file):
                try:
                    await callback_query.edit_message_text("📤 Uploading subtitle file...")
                except Exception:
                    pass
                
                with open(subtitle_file, 'rb') as sub_file:
                    await callback_query.message.reply_document(
                        sub_file,
                        caption=f"📝 Subtitle: {info.get('title', 'Video')}\n🌐 Language: {lang_code.upper()}\n🚀 *Downloaded via Railway*"
                    )
                
                os.remove(subtitle_file)
                try:
                    await callback_query.edit_message_text("✅ Subtitle download completed!")
                except Exception:
                    await callback_query.message.reply_text("✅ Subtitle download completed!")
            else:
                try:
                    await callback_query.edit_message_text("❌ Subtitle download failed!")
                except Exception:
                    await callback_query.message.reply_text("❌ Subtitle download failed!")
        
        elif selected_format == 'audio':
            # Handle audio download
            ydl_opts = {
                'format': format_id,
                'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                try:
                    await callback_query.edit_message_text("📤 Uploading audio file...")
                except Exception:
                    pass
                
                with open(filename, 'rb') as audio_file:
                    await callback_query.message.reply_audio(
                        audio_file,
                        caption=f"🎵 {info.get('title', 'Audio')}\n⏱ Duration: {format_duration(info.get('duration', 0))}\n🚀 *Downloaded via Railway*",
                        title=info.get('title', 'Audio'),
                        performer=info.get('uploader', 'Unknown')
                    )
                
                os.remove(filename)
                try:
                    await callback_query.edit_message_text("✅ Audio download completed!")
                except Exception:
                    await callback_query.message.reply_text("✅ Audio download completed!")
            else:
                try:
                    await callback_query.edit_message_text("❌ Audio download failed!")
                except Exception:
                    await callback_query.message.reply_text("❌ Audio download failed!")
        
        elif selected_format in ['animation', 'document']:
            # Handle animation/document download
            ydl_opts = {
                'format': format_id,
                'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                try:
                    await callback_query.edit_message_text("📤 Uploading file...")
                except Exception:
                    pass
                
                with open(filename, 'rb') as file:
                    if selected_format == 'animation':
                        await callback_query.message.reply_animation(
                            file,
                            caption=f"🎭 {info.get('title', 'Animation')}\n⏱ Duration: {format_duration(info.get('duration', 0))}\n🚀 *Downloaded via Railway*"
                        )
                    else:  # document
                        await callback_query.message.reply_document(
                            file,
                            caption=f"📄 {info.get('title', 'Document')}\n⏱ Duration: {format_duration(info.get('duration', 0))}\n🚀 *Downloaded via Railway*"
                        )
                
                os.remove(filename)
                try:
                    await callback_query.edit_message_text("✅ Download completed!")
                except Exception:
                    await callback_query.message.reply_text("✅ Download completed!")
            else:
                try:
                    await callback_query.edit_message_text("❌ Download failed!")
                except Exception:
                    await callback_query.message.reply_text("❌ Download failed!")
        
        else:
            # Handle video download
            ydl_opts = {
                'format': format_id,
                'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                try:
                    await callback_query.edit_message_text("📤 Uploading file...")
                except Exception:
                    pass
                
                with open(filename, 'rb') as video_file:
                    await callback_query.message.reply_video(
                        video_file,
                        caption=f"🎬 {info.get('title', 'Video')}\n⏱ Duration: {format_duration(info.get('duration', 0))}\n🚀 *Downloaded via Railway*"
                    )
                
                os.remove(filename)
                try:
                    await callback_query.edit_message_text("✅ Download completed!")
                except Exception:
                    await callback_query.message.reply_text("✅ Download completed!")
            else:
                try:
                    await callback_query.edit_message_text("❌ Download failed!")
                except Exception:
                    await callback_query.message.reply_text("❌ Download failed!")
            
    except Exception as e:
        try:
            await callback_query.edit_message_text(f"❌ Error: {str(e)}")
        except Exception:
            await callback_query.message.reply_text(f"❌ Error: {str(e)}")

@app.on_message(filters.text & filters.regex(r'^\d{2}:\d{2}:\d{2}$'))
async def handle_time_input(client, message):
    user_id = message.from_user.id
    
    if user_id not in user_sessions:
        return
    
    session = user_sessions[user_id]
    
    if session.get('awaiting_trim_start'):
        session['trim_start'] = message.text
        session['awaiting_trim_start'] = False
        session['awaiting_trim_end'] = True
        
        await message.reply_text(
            f"✅ Start time set: `{message.text}`\n\n"
            "Now enter the **end time** in format: `HH:MM:SS`\n"
            "Example: `00:03:00` for 3 minutes"
        )
    
    elif session.get('awaiting_trim_end'):
        session['trim_end'] = message.text
        session['awaiting_trim_end'] = False
        
        await message.reply_text(
            f"✂️ **Trimming Settings:**\n"
            f"Start: `{session['trim_start']}`\n"
            f"End: `{message.text}`\n\n"
            "🔄 Processing trimmed video..."
        )
        
        await trim_and_send_video(message, session)

async def trim_and_send_video(message, session):
    """Trim and send the video"""
    try:
        # Double-check FFmpeg availability
        if not check_ffmpeg():
            await message.reply_text(
                "❌ **FFmpeg not found!**\n\n"
                "Please install FFmpeg and restart the bot to use video trimming."
            )
            return
        
        url = session['url']
        format_id = session['selected_quality']
        start_time = session['trim_start']
        end_time = session['trim_end']
        
        # Create download directory
        download_dir = DOWNLOAD_DIR
        
        # Download the video
        status_msg = await message.reply_text("📥 Downloading video...")
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            input_filename = ydl.prepare_filename(info)
        
        if not os.path.exists(input_filename):
            await status_msg.edit_text("❌ Failed to download video!")
            return
        
        # Update status
        await status_msg.edit_text("✂️ Trimming video...")
        
        # Trim the video using ffmpeg
        output_filename = input_filename.replace('.', '_trimmed.')
        
        cmd = [
            'ffmpeg', '-i', input_filename,
            '-ss', start_time, '-to', end_time,
            '-c', 'copy', output_filename, '-y'
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown FFmpeg error"
                await status_msg.edit_text(f"❌ FFmpeg error: {error_msg[:200]}...")
                # Clean up
                if os.path.exists(input_filename):
                    os.remove(input_filename)
                return
                
        except Exception as e:
            await status_msg.edit_text(f"❌ FFmpeg execution error: {str(e)}")
            # Clean up
            if os.path.exists(input_filename):
                os.remove(input_filename)
            return
        
        if os.path.exists(output_filename):
            # Update status
            await status_msg.edit_text("📤 Uploading trimmed video...")
            
            # Send the trimmed file
            try:
                with open(output_filename, 'rb') as video_file:
                    await message.reply_video(
                        video_file,
                        caption=f"✂️ Trimmed: {info.get('title', 'Video')}\n"
                               f"⏱ From: {start_time} To: {end_time}"
                    )
                
                await status_msg.edit_text("✅ Trimmed video sent!")
                
            except Exception as e:
                await status_msg.edit_text(f"❌ Upload error: {str(e)}")
            
            # Clean up
            try:
                if os.path.exists(input_filename):
                    os.remove(input_filename)
                if os.path.exists(output_filename):
                    os.remove(output_filename)
            except Exception:
                pass
        else:
            await status_msg.edit_text("❌ Trimming failed - output file not created!")
            # Clean up
            if os.path.exists(input_filename):
                os.remove(input_filename)
            
    except Exception as e:
        await message.reply_text(f"❌ Trimming error: {str(e)}")

if __name__ == "__main__":
    print("🚀 YouTube Downloader Bot starting on Railway...")
    print(f"📁 Using temp directory: {DOWNLOAD_DIR}")  
    print(f"🔧 FFmpeg available: {check_ffmpeg()}")
    print(f"🌐 Health server will start on port {PORT}")
    
    # Start health check server in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Give health server a moment to start
    time.sleep(2)
    
    # Clean up on startup
    cleanup_temp_files()
    
    print("✅ Starting Telegram bot...")
    # Start the bot
    app.run()