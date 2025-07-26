#!/usr/bin/env python3
"""
Cookie setup utility for YouTube Downloader Bot
This script helps you manually set up cookies to bypass YouTube bot detection.
"""

import os
import requests

def create_sample_cookies():
    """Create a sample cookies file with instructions"""
    cookies_content = """# Netscape HTTP Cookie File
# This is a generated file! Do not edit.

# Instructions:
# 1. Go to youtube.com in your browser
# 2. Log in to your account
# 3. Use a browser extension like "Get cookies.txt LOCALLY" to export cookies
# 4. Replace this file content with the exported cookies
# 5. Make sure the file is named exactly "youtube_cookies.txt"

# Example format (replace with real cookies):
# .youtube.com	TRUE	/	FALSE	1234567890	session_token	your_session_token_here
# .youtube.com	TRUE	/	FALSE	1234567890	VISITOR_INFO1_LIVE	your_visitor_info_here
"""
    
    cookies_path = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')
    
    with open(cookies_path, 'w') as f:
        f.write(cookies_content)
    
    print(f"✅ Sample cookies file created at: {cookies_path}")
    print("\n📝 Instructions:")
    print("1. Install 'Get cookies.txt LOCALLY' browser extension")
    print("2. Go to youtube.com and login")
    print("3. Export cookies using the extension")
    print("4. Replace the content of youtube_cookies.txt with exported cookies")
    print("5. Restart the bot")

def test_cookies():
    """Test if cookies file exists and is valid"""
    cookies_path = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')
    
    if not os.path.exists(cookies_path):
        print("❌ Cookies file not found!")
        return False
    
    with open(cookies_path, 'r') as f:
        content = f.read()
    
    if 'your_session_token_here' in content or len(content) < 100:
        print("❌ Cookies file contains sample data. Please add real cookies.")
        return False
    
    print("✅ Cookies file appears to be valid!")
    return True

if __name__ == "__main__":
    print("🍪 YouTube Cookies Setup Utility")
    print("=" * 40)
    
    choice = input("Choose an option:\n1. Create sample cookies file\n2. Test existing cookies\nEnter choice (1 or 2): ")
    
    if choice == "1":
        create_sample_cookies()
    elif choice == "2":
        test_cookies()
    else:
        print("Invalid choice!")
