import os
import requests
from bs4 import BeautifulSoup
import moviepy.editor as mp
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import threading
import time

# --- Environment Variables ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")          # Telegram Bot Token
CHAT_ID = os.environ.get("CHAT_ID")              # Telegram chat/channel ID
ANIME_NAME = "Automata"                          # Anime to auto-download
CHECK_INTERVAL = 3600                            # Check interval in seconds (1 hour)

bot = Bot(token=BOT_TOKEN)
processed_episodes = set()  # Track downloaded episodes

# =====================
# Original Bot Features
# =====================

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! Bot is running.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("Commands:\n/start - Start bot\n/help - Show commands")

# Example original bot feature: send a custom video
def send_custom_video(update: Update, context: CallbackContext):
    video_path = "example_video.mp4"  # Replace with your logic
    if os.path.exists(video_path):
        update.message.reply_video(open(video_path, "rb"))
    else:
        update.message.reply_text("Video not found.")

# =====================
# Automata Auto-Download
# =====================

def get_latest_episode_url(anime_name=ANIME_NAME):
    base_url = "https://subsplease.org/"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Find anime page link
    anime_link = None
    for a in soup.find_all("a"):
        if anime_name.lower() in a.text.lower():
            anime_link = a['href']
            break
    if not anime_link:
        print(f"{anime_name} not found on SubsPlease")
        return None

    # Visit anime page to get latest episode link
    anime_page = requests.get(anime_link)
    anime_soup = BeautifulSoup(anime_page.content, "html.parser")
    
    # Find latest 720p download link
    download_link = None
    for a in anime_soup.find_all("a"):
        if "720p" in a.text:
            download_link = a['href']
            break
    
    return download_link

def download_episode(url, output_path):
    print(f"Downloading episode from {url}")
    response = requests.get(url, stream=True)
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return output_path

def encode_video(input_path, output_path, target_resolution=(1280,720), bitrate="1500k"):
    print(f"Encoding video {input_path} to 720p...")
    clip = mp.VideoFileClip(input_path)
    clip_resized = clip.resize(newsize=target_resolution)
    clip_resized.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        bitrate=bitrate,
        threads=4,
        preset="medium"
    )
    clip.close()
    return output_path

def send_video_to_telegram(video_path):
    print(f"Sending {video_path} to Telegram...")
    with open(video_path, "rb") as f:
        bot.send_video(chat_id=CHAT_ID, video=f)
    print("Upload complete.")

# Background loop to auto-download and encode episodes
def automata_loop():
    global processed_episodes
    while True:
        try:
            url = get_latest_episode_url()
            if url and url not in processed_episodes:
                raw_file = "episode_temp.mkv"
                encoded_file = "episode_720p.mp4"
                download_episode(url, raw_file)
                encode_video(raw_file, encoded_file)
                send_video_to_telegram(encoded_file)
                os.remove(raw_file)
                os.remove(encoded_file)
                processed_episodes.add(url)
            else:
                print("No new episode found.")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(CHECK_INTERVAL)

# =====================
# Main Bot Setup
# =====================

def main():
    # Start the background thread for auto-download
    threading.Thread(target=automata_loop, daemon=True).start()
    
    # Start the original bot
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("sendvideo", send_custom_video))
    
    # Start polling
    updater.start_polling()
    print("Bot is running...")
    updater.idle()

if __name__ == "__main__":
    main()
