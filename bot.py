import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
import yt_dlp
from dotenv import load_dotenv
import subprocess
import json

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("youtube_dl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Storage for user sessions
user_sessions = {}

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

def get_download_options_keyboard():
    """Create download options keyboard after format selection"""
    keyboard = [
        [InlineKeyboardButton("✅ Get TG File", callback_data="download_file")],
        [InlineKeyboardButton("✂️ trim video 🎮", callback_data="trim_video")],
        [InlineKeyboardButton("🔙 Go Back", callback_data="select_quality")]
    ]
    return InlineKeyboardMarkup(keyboard)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text(
        "🎬 **YouTube Downloader Bot**\n\n"
        "Send me a YouTube URL to get started!",
        reply_markup=None
    )

@app.on_message(filters.text & ~filters.command(["start"]))
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
                
                await callback_query.edit_message_text(
                    f"**Selected Format:** {format_text}\n"
                    f"**Upload Type:** Video\n\n"
                    f"**YouTube Duration:** {format_duration(duration)}\n",
                    reply_markup=get_download_options_keyboard()
                )
        
        elif data == "download_file":
            await callback_query.edit_message_text("🔄 contacting YouTube to get 🕹 download details")
            await download_and_send(callback_query, session)
        
        elif data == "trim_video":
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
        
        # Create download directory
        download_dir = "downloads"
        os.makedirs(download_dir, exist_ok=True)
        
        # Download the video
        ydl_opts = {
            'format': format_id,
            'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        if os.path.exists(filename):
            # Send the file
            try:
                await callback_query.edit_message_text("📤 Uploading file...")
            except Exception:
                pass
            
            with open(filename, 'rb') as video_file:
                await callback_query.message.reply_video(
                    video_file,
                    caption=f"🎬 {info.get('title', 'Video')}\n⏱ Duration: {format_duration(info.get('duration', 0))}"
                )
            
            # Clean up
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
        url = session['url']
        format_id = session['selected_quality']
        start_time = session['trim_start']
        end_time = session['trim_end']
        
        # Create download directory
        download_dir = "downloads"
        os.makedirs(download_dir, exist_ok=True)
        
        # Download the video
        ydl_opts = {
            'format': format_id,
            'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            input_filename = ydl.prepare_filename(info)
        
        # Trim the video using ffmpeg
        output_filename = input_filename.replace('.', '_trimmed.')
        
        cmd = [
            'ffmpeg', '-i', input_filename,
            '-ss', start_time, '-to', end_time,
            '-c', 'copy', output_filename, '-y'
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if os.path.exists(output_filename):
            # Send the trimmed file
            with open(output_filename, 'rb') as video_file:
                await message.reply_video(
                    video_file,
                    caption=f"✂️ Trimmed: {info.get('title', 'Video')}\n"
                           f"⏱ From: {start_time} To: {end_time}"
                )
            
            # Clean up
            os.remove(input_filename)
            os.remove(output_filename)
            
            await message.reply_text("✅ Trimmed video sent!")
        else:
            await message.reply_text("❌ Trimming failed!")
            
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🚀 Bot starting...")
    app.run()
