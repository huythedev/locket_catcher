import os
import telegram
from locket import Auth, LocketAPI
from dotenv import load_dotenv
import logging
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from commands import (
    fetchfriends, list, allow, disallow, allowlist, rename,
    changeinfo, changeemail, changephonenumber, sendmessage,
    help, clearallowlist
)
from utils.token import refresh_token_periodically
from utils.download import download_video_file_sync, download_and_convert_image_to_png_sync
from handlers.buttons import rename_button_handler, send_message_button_handler, cancel_rename_handler
from filelock import FileLock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Shared state
awaiting_rename_responses = {}
user_states = {}
FRIENDS_LIST = set()
USER_INFO_FILE = "users_info.txt"
ALLOW_LIST_FILE = "allow_list.txt"
USER_ID_TO_NAME = {}
ALLOWED_USER_IDS = set()

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
def load_user_info(filepath):
    user_map = {}
    if os.path.exists(filepath):
        with FileLock(filepath + ".lock"):
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
    with FileLock(filepath + ".lock"):
        with open(filepath, "w", encoding="utf-8") as f:
            for userid, name in user_map.items():
                f.write(f"{userid}:{name}\n")

def load_allow_list(filepath):
    allowed_users = set()
    if os.path.exists(filepath):
        try:
            with FileLock(filepath + ".lock"):
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            allowed_users.add(line)
            logging.info(f"Loaded {len(allowed_users)} user(s) from allow list: {filepath}")
        except Exception as e:
            logging.error(f"Error loading allow list from {filepath}: {e}")
    else:
        logging.info(f"Allow list file not found: {filepath}. Notifications will be sent for all users.")
    return allowed_users

def save_allow_list(filepath, allowed_users):
    try:
        with FileLock(filepath + ".lock"):
            with open(filepath, "w", encoding="utf-8") as f:
                for userid in allowed_users:
                    f.write(f"{userid}\n")
        logging.info(f"Saved {len(allowed_users)} user(s) to allow list: {filepath}")
    except Exception as e:
        logging.error(f"Error saving allow list to {filepath}: {e}")
        raise

USER_ID_TO_NAME.update(load_user_info(USER_INFO_FILE))
ALLOWED_USER_IDS.update(load_allow_list(ALLOW_LIST_FILE))

# --- Message Handler ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages, including replies and state-based inputs."""
    chat_id = update.effective_chat.id
    
    # Skip if the message is part of a conversation (e.g., /changeInfo)
    if context.user_data.get('_conversation'):
        return

    user_state = user_states.get(chat_id, {})
    state = user_state.get("state")

    if update.message.reply_to_message:
        reply_to_id = update.message.reply_to_message.message_id
        if reply_to_id in awaiting_rename_responses:
            user_id = awaiting_rename_responses[reply_to_id]
            new_name = update.message.text.strip()
            if not new_name:
                await update.message.reply_text(
                    "❌ The new name cannot be empty. Please try again.",
                    parse_mode="Markdown"
                )
                return
            old_name = USER_ID_TO_NAME.get(user_id, user_id)
            USER_ID_TO_NAME[user_id] = new_name
            save_user_info(USER_INFO_FILE, USER_ID_TO_NAME)
            await update.message.reply_text(
                f"✅ Successfully updated name for user `{user_id}` from *{old_name}* to *{new_name}*.",
                parse_mode="Markdown"
            )
            del awaiting_rename_responses[reply_to_id]
            try:
                await update.message.reply_to_message.edit_text(
                    update.message.reply_to_message.text.split("\n\n")[0] + "\n\n*Name updated successfully!*",
                    parse_mode="Markdown",
                    reply_markup=None
                )
            except Exception as e:
                logging.error(f"Failed to edit the message: {e}")
            return

    if state == "awaiting_send_message":
        message = update.message.text.strip()
        if not message:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Message cannot be empty. Please try again.",
                parse_mode="Markdown"
            )
            return
        receiver_uid = user_state["receiver_uid"]
        moment_uid = user_state["moment_uid"]
        try:
            await asyncio.to_thread(api.sendChatMessage, receiver_uid, api.token, message, moment_uid)
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ Message sent successfully.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Failed to send message: {str(e)}",
                parse_mode="Markdown"
            )
        finally:
            del user_states[chat_id]

# --- Locket Monitoring Loop ---
async def locket_monitor_loop(DOWNLOAD_DIR):
    global USER_ID_TO_NAME, ALLOWED_USER_IDS
    logging.info("Starting Locket monitoring loop...")
    
    while True:
        try:
            # Reload user info and allow list
            USER_ID_TO_NAME.update(load_user_info(USER_INFO_FILE))
            ALLOWED_USER_IDS.clear()
            ALLOWED_USER_IDS.update(load_allow_list(ALLOW_LIST_FILE))
            logging.debug("Reloaded allow list in locket_monitor_loop")

            moment_response = await asyncio.to_thread(api.getLastMoment)
            if moment_response.get('result', {}).get('status') == 200:
                data = moment_response.get('result', {}).get('data', [])
                if data:
                    logging.info(f"Received {len(data)} moment(s) from API.")
                    for moment in data:
                        moment_id = moment.get('canonical_uid')
                        user_id = moment.get('user')
                        thumbnail_url = moment.get('thumbnail_url')
                        video_url = moment.get('video_url')
                        caption = moment.get('caption', 'No caption')
                        moment_date_seconds = moment.get('date', {}).get('_seconds', 'N/A')

                        if moment_id and user_id and (thumbnail_url or video_url):
                            if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
                                logging.info(f"User {user_id} is not in the allow list. Skipping notification for moment {moment_id}.")
                                continue

                            user_dir = os.path.join(DOWNLOAD_DIR, user_id)
                            await asyncio.to_thread(os.makedirs, user_dir, exist_ok=True)
                            png_filename = f"{moment_id}.png"
                            mp4_filename = f"{moment_id}.mp4"
                            png_path = os.path.join(user_dir, png_filename)
                            mp4_path = os.path.join(user_dir, mp4_filename)

                            display_name = USER_ID_TO_NAME.get(user_id)
                            if not display_name:
                                logging.info(f"User ID {user_id} not found in users_info.txt. Fetching from API...")
                                try:
                                    user_info_response = await asyncio.to_thread(api.getUserinfo, user_id)
                                    if user_info_response.get('result', {}).get('status') == 200:
                                        user_data = user_info_response.get('result', {}).get('data', {})
                                        first_name = user_data.get('first_name', '')
                                        last_name = user_data.get('last_name', '')
                                        fetched_name = f"{first_name} {last_name}".strip()
                                        if fetched_name:
                                            display_name = fetched_name
                                            USER_ID_TO_NAME[user_id] = display_name
                                            save_user_info(USER_INFO_FILE, USER_ID_TO_NAME)
                                            logging.info(f"Fetched and saved name for {user_id}: {display_name}")
                                        else:
                                            display_name = user_id
                                            USER_ID_TO_NAME[user_id] = display_name
                                            save_user_info(USER_INFO_FILE, USER_ID_TO_NAME)
                                    else:
                                        display_name = user_id
                                        USER_ID_TO_NAME[user_id] = display_name
                                        save_user_info(USER_INFO_FILE, USER_ID_TO_NAME)
                                except Exception as e_user_info:
                                    logging.error(f"Error fetching user info for {user_id}: {e_user_info}. Using User ID.")
                                    display_name = user_id
                                    USER_ID_TO_NAME[user_id] = display_name
                                    save_user_info(USER_INFO_FILE, USER_ID_TO_NAME)

                            if not display_name:
                                display_name = user_id

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
                                    elif thumbnail_url:
                                        media_type = "png"
                                        final_media_path = png_path
                                        await asyncio.to_thread(download_and_convert_image_to_png_sync, thumbnail_url, png_path)
                                    else:
                                        logging.warning(f"No video_url or thumbnail_url for moment {moment_id}. Skipping download.")
                                        continue

                                    logging.info(f"Downloaded and saved {media_type.upper()} to: {final_media_path}")

                                    message = f"*✨ {display_name}*\n💬 {caption}\n"

                                    keyboard = [
                                        [
                                            InlineKeyboardButton("✏️ Rename User", callback_data=f"rename:{user_id}"),
                                            InlineKeyboardButton("💬 Send Message", callback_data=f"send_message:{user_id}:{moment_id}")
                                        ]
                                    ]
                                    reply_markup = InlineKeyboardMarkup(keyboard)

                                    try:
                                        if media_type == "mp4":
                                            def read_video_sync():
                                                with open(mp4_path, 'rb') as video_file:
                                                    return video_file.read()
                                            video_data = await asyncio.to_thread(read_video_sync)
                                            await bot.send_video(
                                                chat_id=TELEGRAM_CHAT_ID,
                                                video=video_data,
                                                caption=message,
                                                parse_mode="Markdown",
                                                reply_markup=reply_markup
                                            )
                                        elif media_type == "png":
                                            def read_photo_sync():
                                                with open(png_path, 'rb') as photo_file:
                                                    return photo_file.read()
                                            photo_data = await asyncio.to_thread(read_photo_sync)
                                            await bot.send_photo(
                                                chat_id=TELEGRAM_CHAT_ID,
                                                photo=photo_data,
                                                caption=message,
                                                parse_mode="Markdown",
                                                reply_markup=reply_markup
                                            )
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
    
    token_refresh_task = asyncio.create_task(refresh_token_periodically(auth, api))
    locket_monitor_task = asyncio.create_task(locket_monitor_loop(DOWNLOAD_DIR))
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("fetchfriends", fetchfriends.fetch_friends_command_handler))
    application.add_handler(CommandHandler("list", list.list_friends_command_handler))
    application.add_handler(CommandHandler("allow", allow.allow_command_handler))
    application.add_handler(CommandHandler("disallow", disallow.disallow_command_handler))
    application.add_handler(CommandHandler("allowlist", allowlist.allowlist_command_handler))
    application.add_handler(CommandHandler("rename", rename.rename_command_handler))
    application.add_handler(changeinfo.conversation_handler)
    application.add_handler(CommandHandler("changeEmail", changeemail.change_email_command_handler))
    application.add_handler(CommandHandler("changePhoneNumber", changephonenumber.change_phone_number_command_handler))
    application.add_handler(CommandHandler("sendMessage", sendmessage.send_message_command_handler))
    application.add_handler(CommandHandler("help", help.help_command_handler))
    application.add_handler(CommandHandler("clearallowlist", clearallowlist.clearallowlist_command_handler))
    application.add_handler(rename_button_handler)
    application.add_handler(send_message_button_handler)
    application.add_handler(cancel_rename_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    initialized = False
    max_retries = 5
    retry_count = 0
    
    while not initialized and retry_count < max_retries:
        try:
            logging.info(f"Attempting to initialize application (try {retry_count+1}/{max_retries})...")
            telegram.request.HTTPXRequest.DEFAULT_READ_TIMEOUT = 60.0
            telegram.request.HTTPXRequest.DEFAULT_CONNECT_TIMEOUT = 60.0
            await application.initialize()
            app_bot = application.bot
            try:
                await app_bot.initialize()
                initialized = True
                logging.info("Application initialized successfully.")
            except telegram.error.TimedOut:
                logging.warning("Bot initialization timed out, but continuing anyway...")
                app_bot = bot
                initialized = True
        except Exception as e:
            retry_count += 1
            backoff_time = min(2 ** retry_count, 30)
            logging.error(f"Failed to initialize application: {e}. Retrying in {backoff_time}s...")
            await asyncio.sleep(backoff_time)
    
    if not initialized:
        logging.error("Failed to initialize application after multiple attempts. Continuing with limited functionality.")
        app_bot = bot
    
    await application.start()
    
    offset = 0
    logging.info("Starting manual Telegram polling...")
    
    try:
        while True:
            try:
                updates = await app_bot.get_updates(offset=offset, timeout=30)
                for update in updates:
                    offset = update.update_id + 1
                    try:
                        await application.process_update(update)
                    except Exception as update_error:
                        logging.error(f"Error processing update: {update_error}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logging.error(f"Error in Telegram polling: {e}")
                await asyncio.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutdown signal received.")
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}", exc_info=True)
    finally:
        logging.info("Stopping tasks...")
        await application.stop()
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

if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        finally:
            loop.close()
    except KeyboardInterrupt:
        logging.info("Script stopped by user.")
    except Exception as e:
        logging.critical(f"Script crashed: {e}", exc_info=True)