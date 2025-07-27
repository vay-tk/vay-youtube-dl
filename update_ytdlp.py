#!/usr/bin/env python3
"""
yt-dlp Update Utility for YouTube Downloader Bot
This script helps update yt-dlp and test YouTube access
"""

import subprocess
import sys
import os
import yt_dlp

def update_ytdlp():
    """Update yt-dlp to the latest version"""
    print("🔄 Updating yt-dlp to latest version...")
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-U', 'yt-dlp'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ yt-dlp updated successfully!")
            print(f"📦 Output: {result.stdout}")
        else:
            print(f"❌ Update failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Update error: {e}")
        return False
    return True

def check_ytdlp_version():
    """Check current yt-dlp version"""
    try:
        version = yt_dlp.version.__version__
        print(f"📋 Current yt-dlp version: {version}")
        return version
    except Exception as e:
        print(f"❌ Could not get version: {e}")
        return None

def test_youtube_access():
    """Test YouTube access with different strategies"""
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - usually works
    
    strategies = [
        ("Standard", {}),
        ("Android Client", {
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            }
        }),
        ("iOS Client", {
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios'],
                }
            }
        })
    ]
    
    print(f"🧪 Testing YouTube access with URL: {test_url}")
    
    for name, opts in strategies:
        print(f"\n🔍 Testing {name}...")
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                **opts
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                print(f"✅ {name}: SUCCESS - '{title}' ({duration}s)")
                return True
                
        except Exception as e:
            error_msg = str(e)
            if 'player response' in error_msg.lower():
                print(f"❌ {name}: FAILED - Player response error")
            elif '403' in error_msg:
                print(f"❌ {name}: FAILED - 403 Forbidden")
            else:
                print(f"❌ {name}: FAILED - {error_msg[:100]}...")
    
    return False

def main():
    print("🛠️  yt-dlp Maintenance Utility")
    print("=" * 40)
    
    # Check current version
    check_ytdlp_version()
    
    choice = input("\nChoose an option:\n1. Update yt-dlp\n2. Test YouTube access\n3. Both\nEnter choice (1, 2, or 3): ")
    
    if choice in ["1", "3"]:
        print("\n" + "="*40)
        if update_ytdlp():
            print("✅ Update completed!")
            check_ytdlp_version()
        else:
            print("❌ Update failed!")
    
    if choice in ["2", "3"]:
        print("\n" + "="*40)
        if test_youtube_access():
            print("\n✅ YouTube access is working!")
        else:
            print("\n❌ YouTube access is blocked. Solutions:")
            print("🍪 Setup cookies from a real browser")
            print("⏰ Wait and try again later")
            print("🌐 Try using a VPN")

if __name__ == "__main__":
    main()
