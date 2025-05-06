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
from moviepy.editor import ImageSequenceClip  # Add this import

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

# --- Main Async Function ---
async def main():
    DOWNLOAD_DIR = "locket_downloads"
    await asyncio.to_thread(os.makedirs, DOWNLOAD_DIR, exist_ok=True)

    # Start the token refresh task
    asyncio.create_task(refresh_token_periodically(auth, api))

    logging.info("Starting Locket monitoring loop...")

    while True:
        try:
            # Run synchronous LocketAPI call in a thread
            moment_response = await asyncio.to_thread(api.getLastMoment)

            if moment_response.get('result', {}).get('status') == 200:
                data = moment_response.get('result', {}).get('data', [])
                if data:
                    logging.info(f"Received {len(data)} moment(s) from API.")
                    for moment in data:
                        moment_id = moment.get('canonical_uid')
                        user_id = moment.get('user')
                        thumbnail_url = moment.get('thumbnail_url')
                        caption = moment.get('caption', 'No caption')
                        moment_date_seconds = moment.get('date', {}).get('_seconds', 'N/A')

                        print(f"\n--- Processing Moment ---")
                        print(f"  ID: {moment_id}")
                        print(f"  User: {user_id}")
                        print(f"  Caption: {caption}")
                        print(f"  Timestamp: {moment_date_seconds}")
                        print(f"-------------------------")

                        if moment_id and user_id and thumbnail_url:
                            # Check against allow list
                            if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
                                logging.info(f"User {user_id} is not in the allow list. Skipping notification for moment {moment_id}.")
                                continue  # Skip to the next moment

                            user_dir = os.path.join(DOWNLOAD_DIR, user_id)
                            await asyncio.to_thread(os.makedirs, user_dir, exist_ok=True)
                            png_filename = f"{moment_id}.png"
                            mp4_filename = f"{moment_id}.mp4"
                            png_path = os.path.join(user_dir, png_filename)
                            mp4_path = os.path.join(user_dir, mp4_filename)

                            display_name = USER_ID_TO_NAME[user_id] if user_id in USER_ID_TO_NAME else user_id

                            # Check if either png or mp4 exists
                            image_exists = await asyncio.to_thread(os.path.exists, png_path)
                            video_exists = await asyncio.to_thread(os.path.exists, mp4_path)
                            if not image_exists and not video_exists:
                                logging.info(f"Moment {moment_id} from user {user_id} not found locally. Downloading...")
                                try:
                                    def download_and_save_media(url, png_save_path, mp4_save_path):
                                        import requests
                                        from PIL import Image
                                        import io
                                        from moviepy.editor import ImageSequenceClip
                                        response = requests.get(url, stream=True)
                                        response.raise_for_status()
                                        img_bytes = io.BytesIO(response.content)
                                        img = Image.open(img_bytes)
                                        if getattr(img, "is_animated", False) and img.format.lower() == "webp":
                                            # Animated webp: convert to mp4
                                            frames = []
                                            durations = []
                                            for frame in range(img.n_frames):
                                                img.seek(frame)
                                                frames.append(img.convert("RGB"))
                                                durations.append(img.info.get('duration', 100))
                                            # Convert PIL images to numpy arrays
                                            import numpy as np
                                            np_frames = [np.array(f) for f in frames]
                                            # Calculate fps from average duration
                                            avg_duration = sum(durations) / len(durations)
                                            fps = 1000.0 / avg_duration if avg_duration > 0 else 10
                                            clip = ImageSequenceClip(np_frames, fps=fps)
                                            clip.write_videofile(mp4_save_path, codec="libx264", audio=False, verbose=False, logger=None)
                                            return "mp4"
                                        else:
                                            # Static image: save as png
                                            img.convert("RGB").save(png_save_path, "png")
                                            return "png"
                                    media_type = await asyncio.to_thread(download_and_save_media, thumbnail_url, png_path, mp4_path)

                                    logging.info(f"Downloaded and saved {media_type.upper()} to: {mp4_path if media_type == 'mp4' else png_path}")

                                    message = f"✨ New Locket Downloaded from User: {display_name}\n"
                                    message += f"💬 Caption: {caption}\n"
                                    message += f"🆔 Moment ID: {moment_id}"
                                    try:
                                        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

                                        if media_type == "mp4":
                                            def read_video_sync():
                                                with open(mp4_path, 'rb') as video_file:
                                                    return video_file.read()
                                            video_data = await asyncio.to_thread(read_video_sync)
                                            await bot.send_video(chat_id=TELEGRAM_CHAT_ID, video=video_data, caption=f"Animated image from {display_name}")
                                        else:
                                            def read_photo_sync():
                                                with open(png_path, 'rb') as photo_file:
                                                    return photo_file.read()
                                            photo_data = await asyncio.to_thread(read_photo_sync)
                                            await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo_data, caption=f"Image from {display_name}")

                                        logging.info(f"Sent notification for {moment_id} to Telegram chat ID: {TELEGRAM_CHAT_ID}")
                                    except telegram.error.TelegramError as tg_err:
                                        logging.error(f"Failed to send Telegram notification for {moment_id}: {tg_err}")
                                    except Exception as send_err:
                                        logging.error(f"An unexpected error occurred sending Telegram for {moment_id}: {send_err}")

                                except requests.exceptions.RequestException as req_err:
                                    logging.error(f"Failed to download image {thumbnail_url} for {moment_id}: {req_err}")
                                except IOError as io_err:
                                    logging.error(f"Failed to save image to {png_path} for {moment_id}: {io_err}")
                                except Exception as dl_err:
                                    logging.error(f"An unexpected error occurred during download/saving for {moment_id}: {dl_err}")
                            else:
                                logging.info(f"Moment {moment_id} from user {user_id} already downloaded. Skipping.")
                        else:
                            logging.warning(f"Received moment data missing required fields (moment_id, user_id, or thumbnail_url). Moment data: {moment}")
                else:
                    logging.info("No moment data found in the API response this cycle.")
            else:
                logging.warning(f"API call did not return status 200. Response: {moment_response}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error during API call: {e}")
            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}", exc_info=True)

        logging.info("Waiting for 1 second before next check...")
        await asyncio.sleep(1)

# Run the async main function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Script stopped by user.")
    except Exception as e:
        logging.critical(f"Script crashed: {e}", exc_info)