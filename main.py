import requests
import os
import time
import telegram
from locket import Auth, LocketAPI
import json
from dotenv import load_dotenv
import logging
import asyncio
from PIL import Image
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

Email = os.getenv("EMAIL")
Password = os.getenv("PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not all([Email, Password, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    logging.error("Missing environment variables. Please check your .env file.")
    exit(1)

# Initialize Telegram Bot
try:
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    logging.info("Telegram bot initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Telegram bot: {e}")
    exit(1)

# --- Authentication ---
try:
    auth = Auth(Email, Password)
    token = auth.get_token()
    api = LocketAPI(token)
    logging.info("Locket authentication successful.")
except Exception as e:
    logging.error(f"Locket authentication failed: {e}")
    exit(1)

# --- Load user info mapping ---
USER_INFO_FILE = "users_info.txt"
ALLOW_LIST_FILE = "allow_list.txt"  # New constant for the allow list file

def load_user_info(filepath):
    user_map = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                try:
                    userid, name = line.split(":", 1)
                    userid = userid.strip().strip('"').strip("'")
                    name = name.strip().strip('"').strip("'")
                    if userid and name:
                        user_map[userid] = name
                except Exception:
                    continue
    return user_map

def save_user_info(filepath, user_map):
    with open(filepath, "w", encoding="utf-8") as f:
        for userid, name in user_map.items():
            f.write(f"{userid}:{name}\n")

def load_allow_list(filepath):
    """Loads the allow list from the specified file."""
    allowed_users = set()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):  # Ignore empty lines and comments
                        allowed_users.add(line)
            logging.info(f"Loaded {len(allowed_users)} user(s) from allow list: {filepath}")
        except Exception as e:
            logging.error(f"Error loading allow list from {filepath}: {e}")
    else:
        logging.info(f"Allow list file not found: {filepath}. Notifications will be sent for all users.")
    return allowed_users

USER_ID_TO_NAME = load_user_info(USER_INFO_FILE)
ALLOWED_USER_IDS = load_allow_list(ALLOW_LIST_FILE)  # Load the allow list

# --- New Download Helper Functions ---
def download_video_file_sync(url, save_path):
    """Downloads a video file directly from a URL and saves it."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Successfully downloaded video to {save_path}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download video from {url}: {e}")
        raise
    except IOError as e:
        logging.error(f"Failed to save video to {save_path}: {e}")
        raise

def download_and_convert_image_to_png_sync(url, save_path):
    """Downloads an image, converts it to PNG, and saves it."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        img_bytes = io.BytesIO(response.content)
        img = Image.open(img_bytes)
        img.convert("RGB").save(save_path, "PNG")
        logging.info(f"Successfully downloaded and converted image to PNG: {save_path}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download image from {url}: {e}")
        raise
    except IOError as e:
        logging.error(f"Failed to save image to {save_path}: {e}")
        raise
    except Exception as e:  # Catch PIL errors
        logging.error(f"Failed to process image from {url} for saving to {save_path}: {e}")
        raise

# --- Telegram Handler State ---
RENAME_STATE = {}  # user_id: telegram_user_id -> locket_user_id being renamed

# --- Telegram Callback Handlers ---
async def rename_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    locket_user_id = query.data.split(":")[1]
    telegram_user_id = query.from_user.id
    RENAME_STATE[telegram_user_id] = locket_user_id
    await query.message.reply_text(f"Send the new name for user ID {locket_user_id}:")

async def handle_rename_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id
    if telegram_user_id in RENAME_STATE:
        locket_user_id = RENAME_STATE.pop(telegram_user_id)
        new_name = update.message.text.strip()
        # Reload user info to avoid overwriting
        user_map = load_user_info(USER_INFO_FILE)
        user_map[locket_user_id] = new_name
        save_user_info(USER_INFO_FILE, user_map)
        await update.message.reply_text(f"Updated name for user {locket_user_id} to '{new_name}'.")
    else:
        # Not in rename state, ignore or handle as normal
        pass

# --- Token Refresh Function ---
async def refresh_token_periodically(auth_instance, api_instance):
    while True:
        try:
            logging.info("Attempting to refresh Locket API token...")
            # Run synchronous auth.get_token in a thread
            new_token = await asyncio.to_thread(auth_instance.get_token)
            # Update the API instance with the new token
            api_instance.token = new_token
            # Update the Authorization header as well
            api_instance.headers['Authorization'] = f'Bearer {new_token}'
            logging.info("Successfully refreshed Locket API token.")
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            # Continue running to avoid stopping the refresh loop
        # Wait for 30 minutes (1800 seconds)
        await asyncio.sleep(1800)

# --- Locket Monitoring Loop ---
async def locket_monitor_loop(DOWNLOAD_DIR):
    global USER_ID_TO_NAME
    logging.info("Starting Locket monitoring loop...")
    while True:
        try:
            # Reload user info mapping every loop to keep up to date
            USER_ID_TO_NAME = load_user_info(USER_INFO_FILE)

            # Run synchronous LocketAPI call in a thread
            moment_response = await asyncio.to_thread(api.getLastMoment)
            # print(f"API Response: {moment_response}")  # Add this line to print the API response

            if moment_response.get('result', {}).get('status') == 200:
                data = moment_response.get('result', {}).get('data', [])
                if data:
                    logging.info(f"Received {len(data)} moment(s) from API.")
                    for moment in data:
                        moment_id = moment.get('canonical_uid')
                        user_id = moment.get('user')
                        thumbnail_url = moment.get('thumbnail_url')
                        video_url = moment.get('video_url')  # Get video_url
                        caption = moment.get('caption', 'No caption')
                        moment_date_seconds = moment.get('date', {}).get('_seconds', 'N/A')

                        print(f"\n--- Processing Moment ---")
                        print(f"  ID: {moment_id}")
                        print(f"  User: {user_id}")
                        print(f"  Caption: {caption}")
                        print(f"  Timestamp: {moment_date_seconds}")
                        print(f"-------------------------")

                        if moment_id and user_id and (thumbnail_url or video_url):
                            # Check against allow list
                            if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
                                logging.info(f"User {user_id} is not in the allow list. Skipping notification for moment {moment_id}.")
                                continue

                            user_dir = os.path.join(DOWNLOAD_DIR, user_id)
                            await asyncio.to_thread(os.makedirs, user_dir, exist_ok=True)
                            png_filename = f"{moment_id}.png"
                            mp4_filename = f"{moment_id}.mp4"
                            png_path = os.path.join(user_dir, png_filename)
                            mp4_path = os.path.join(user_dir, mp4_filename)

                            display_name = USER_ID_TO_NAME.get(user_id, user_id)

                            image_exists = await asyncio.to_thread(os.path.exists, png_path)
                            video_exists = await asyncio.to_thread(os.path.exists, mp4_path)
                            if not image_exists and not video_exists:
                                logging.info(f"Moment {moment_id} from user {user_id} not found locally. Downloading...")
                                media_type = None
                                final_media_path = None

                                try:
                                    if video_url:
                                        media_type = "mp4"
                                        final_media_path = mp4_path
                                        await asyncio.to_thread(download_video_file_sync, video_url, mp4_path)
                                    elif thumbnail_url:  # Fallback to thumbnail if no video_url
                                        media_type = "png"
                                        final_media_path = png_path
                                        await asyncio.to_thread(download_and_convert_image_to_png_sync, thumbnail_url, png_path)
                                    else:
                                        logging.warning(f"No video_url or thumbnail_url for moment {moment_id}. Skipping download.")
                                        continue  # Skip if no URL to download

                                    logging.info(f"Downloaded and saved {media_type.upper()} to: {final_media_path}")

                                    message = f"✨ New Locket Downloaded from User: {display_name}\n"
                                    message += f"💬 Caption: {caption}\n"
                                    message += f"🆔 Moment ID: {moment_id}"
                                    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Rename", callback_data=f"rename:{user_id}")]])
                                    try:
                                        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

                                        if media_type == "mp4":
                                            def read_video_sync():
                                                with open(mp4_path, 'rb') as video_file:  # Use mp4_path
                                                    return video_file.read()
                                            video_data = await asyncio.to_thread(read_video_sync)
                                            await bot.send_video(chat_id=TELEGRAM_CHAT_ID, video=video_data, caption=f"Animated image from {display_name}", reply_markup=keyboard)
                                        elif media_type == "png":  # Check for png
                                            def read_photo_sync():
                                                with open(png_path, 'rb') as photo_file:  # Use png_path
                                                    return photo_file.read()
                                            photo_data = await asyncio.to_thread(read_photo_sync)
                                            await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo_data, caption=f"Image from {display_name}", reply_markup=keyboard)

                                        logging.info(f"Sent notification for {moment_id} to Telegram chat ID: {TELEGRAM_CHAT_ID}")
                                    except telegram.error.TelegramError as tg_err:
                                        logging.error(f"Failed to send Telegram notification for {moment_id}: {tg_err}")
                                    except Exception as send_err:
                                        logging.error(f"An unexpected error occurred sending Telegram for {moment_id}: {send_err}")

                                except requests.exceptions.RequestException as req_err:
                                    logging.error(f"Failed to download media for {moment_id}: {req_err}")
                                except IOError as io_err:
                                    logging.error(f"Failed to save media for {moment_id}: {io_err}")
                                except Exception as dl_err:
                                    logging.error(f"An unexpected error occurred during download/saving for {moment_id}: {dl_err}")
                            else:
                                logging.info(f"Moment {moment_id} from user {user_id} already downloaded. Skipping.")
                        else:
                            logging.warning(f"Received moment data missing required fields (moment_id, user_id, or URLs). Moment data: {moment}")
                else:
                    logging.info("No moment data found in the API response this cycle.")
            else:
                logging.warning(f"API call did not return status 200. Response: {moment_response}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error during API call: {e}")
            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"An error occurred in the Locket monitor loop: {e}", exc_info=True)
            await asyncio.sleep(10)

        logging.info("Waiting for 1 second before next Locket check...")
        await asyncio.sleep(1)

# --- Main Async Function ---
async def main():
    DOWNLOAD_DIR = "locket_downloads"
    await asyncio.to_thread(os.makedirs, DOWNLOAD_DIR, exist_ok=True)

    # --- Setup Telegram application for callback handling ---
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CallbackQueryHandler(rename_button_callback, pattern=r"^rename:"))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_rename_message))

    # Start background tasks
    token_refresh_task = asyncio.create_task(refresh_token_periodically(auth, api))
    locket_monitor_task = asyncio.create_task(locket_monitor_loop(DOWNLOAD_DIR))

    try:
        logging.info("Initializing Telegram application...")
        await application.initialize()
        logging.info("Starting Telegram application polling...")
        await application.start()

        await asyncio.gather(token_refresh_task, locket_monitor_task)

    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutdown signal received.")
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}", exc_info=True)
    finally:
        logging.info("Stopping Telegram application...")
        if application.running:
            await application.stop()
        logging.info("Shutting down Telegram application...")
        await application.shutdown()

        if not token_refresh_task.done():
            token_refresh_task.cancel()
        if not locket_monitor_task.done():
            locket_monitor_task.cancel()

        try:
            await asyncio.gather(token_refresh_task, locket_monitor_task, return_exceptions=True)
        except asyncio.CancelledError:
            logging.info("Background tasks cancelled.")

        logging.info("Script finished.")

# Run the async main function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Script stopped by user.")
    except Exception as e:
        logging.critical(f"Script crashed: {e}", exc_info=True)