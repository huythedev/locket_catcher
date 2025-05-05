import requests
import os
import time
import telegram
from locket import Auth, LocketAPI
import json
from dotenv import load_dotenv
import logging
import asyncio # Import asyncio
from PIL import Image # <-- Add this import

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
    # Bot initialization remains synchronous
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    logging.info("Telegram bot initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Telegram bot: {e}")
    exit(1)

# --- Authentication ---
try:
    # Auth remains synchronous
    auth = Auth(Email, Password)
    token = auth.get_token()
    api = LocketAPI(token)
    logging.info("Locket authentication successful.")
except Exception as e:
    logging.error(f"Locket authentication failed: {e}")
    exit(1)

# --- Load user info mapping ---
USER_INFO_FILE = "users_info.txt"
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

USER_ID_TO_NAME = load_user_info(USER_INFO_FILE)

# --- Main Async Function ---
async def main(): # Make the main logic async
    DOWNLOAD_DIR = "locket_downloads"
    await asyncio.to_thread(os.makedirs, DOWNLOAD_DIR, exist_ok=True)

    logging.info("Starting Locket monitoring loop...")

    while True:
        try:
            # Run synchronous LocketAPI call in a thread
            moment_response = await asyncio.to_thread(api.getLastMoment)

            if moment_response.get('result', {}).get('status') == 200:
                data = moment_response.get('result', {}).get('data', [])
                if data:
                    logging.info(f"Received {len(data)} moment(s) from API.")
                    # Iterate through ALL moments in the response
                    for moment in data: # <--- Loop through all moments
                        moment_id = moment.get('canonical_uid')
                        user_id = moment.get('user')
                        thumbnail_url = moment.get('thumbnail_url')
                        caption = moment.get('caption', 'No caption')
                        moment_date_seconds = moment.get('date', {}).get('_seconds', 'N/A')

                        # Print details for each moment to terminal
                        print(f"\n--- Processing Moment ---")
                        print(f"  ID: {moment_id}")
                        print(f"  User: {user_id}")
                        print(f"  Caption: {caption}")
                        print(f"  Timestamp: {moment_date_seconds}")
                        print(f"-------------------------")

                        if moment_id and user_id and thumbnail_url:
                            user_dir = os.path.join(DOWNLOAD_DIR, user_id)
                            await asyncio.to_thread(os.makedirs, user_dir, exist_ok=True)
                            png_filename = f"{moment_id}.png"
                            png_path = os.path.join(user_dir, png_filename)

                            # Use custom name if available, else keep userid
                            display_name = USER_ID_TO_NAME[user_id] if user_id in USER_ID_TO_NAME else user_id

                            # Check existence for *this specific* moment (PNG only)
                            image_exists = await asyncio.to_thread(os.path.exists, png_path)
                            if not image_exists:
                                logging.info(f"Moment {moment_id} from user {user_id} not found locally. Downloading...")
                                try:
                                    # Download image to memory, convert to PNG, and save PNG
                                    def download_and_save_png(url, save_path):
                                        import io
                                        from PIL import Image
                                        import requests
                                        response = requests.get(url, stream=True)
                                        response.raise_for_status()
                                        img = Image.open(io.BytesIO(response.content)).convert("RGB")
                                        img.save(save_path, "png")
                                    await asyncio.to_thread(download_and_save_png, thumbnail_url, png_path)

                                    logging.info(f"Downloaded and saved PNG image to: {png_path}")

                                    # --- Send Telegram Notification (Async) ---
                                    message = f"✨ New Locket Downloaded from User: {display_name}\n"
                                    message += f"💬 Caption: {caption}\n"
                                    message += f"🆔 Moment ID: {moment_id}"
                                    try:
                                        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

                                        # Read PNG and send to Telegram
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
                                # Log skipping for this specific moment
                                logging.info(f"Moment {moment_id} from user {user_id} already downloaded. Skipping.")
                        else:
                            logging.warning(f"Received moment data missing required fields (moment_id, user_id, or thumbnail_url). Moment data: {moment}") # Log the problematic moment data
                    # End of loop for moments in data
                else:
                    # Changed log message slightly for clarity
                    logging.info("No moment data found in the API response this cycle.")
            else:
                logging.warning(f"API call did not return status 200. Response: {moment_response}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error during API call: {e}")
            await asyncio.sleep(60) # Use asyncio.sleep
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}", exc_info=True) # Add traceback

        logging.info("Waiting for 10 seconds before next check...")
        await asyncio.sleep(10) # Use asyncio.sleep

# Run the async main function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Script stopped by user.")
    except Exception as e:
        logging.critical(f"Script crashed: {e}", exc_info=True) # Log critical errors