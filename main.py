import requests
import os
import time
import telegram
from locket import Auth, LocketAPI
import json
from dotenv import load_dotenv
import logging
import asyncio
import io
from PIL import Image
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Dictionary to track which message is expecting a name for which user ID
awaiting_rename_responses = {}

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
ALLOW_LIST_FILE = "allow_list.txt"

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
    allowed_users = set()
    if os.path.exists(filepath):
        try:
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

USER_ID_TO_NAME = load_user_info(USER_INFO_FILE)
ALLOWED_USER_IDS = load_allow_list(ALLOW_LIST_FILE)

# --- Download Helper Functions ---
def download_video_file_sync(url, save_path):
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
    except Exception as e:
        logging.error(f"Failed to process image from {url} for saving to {save_path}: {e}")
        raise

# --- Telegram Command Handlers ---
async def rename_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /rename command to update a user's display name."""
    global USER_ID_TO_NAME
    
    command_text = update.message.text if update.message else "N/A"
    args_received = context.args if context.args else []
    logging.info(f"/rename command received from user {update.effective_user.id}. Full command: '{command_text}'. Args: {args_received}")

    chat_id = update.effective_chat.id

    if not context.args or len(context.args) < 2:
        logging.warning(f"/rename command: Incorrect arguments. User: {update.effective_user.id}, Args: {args_received}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /rename <LocketUserID> <NewDisplayName>\nExample: /rename BXcfLO4HaYWcUVz6Eduu9IzGeCl2 MyFriendName"
        )
        return

    locket_user_id = context.args[0]
    new_name = " ".join(context.args[1:])

    if not locket_user_id or not new_name:
        logging.warning(f"/rename command: Missing LocketUserID or NewDisplayName. User: {update.effective_user.id}, LocketUserID: '{locket_user_id}', NewName: '{new_name}'")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Error: Both Locket User ID and New Display Name must be provided.\nUsage: /rename <LocketUserID> <NewDisplayName>"
        )
        return

    try:
        current_user_map_from_file = load_user_info(USER_INFO_FILE)
        old_name = current_user_map_from_file.get(locket_user_id, "this user (ID not previously known)")
        current_user_map_from_file[locket_user_id] = new_name
        save_user_info(USER_INFO_FILE, current_user_map_from_file)
        USER_ID_TO_NAME = current_user_map_from_file
        logging.info(f"User {update.effective_user.id} renamed Locket user {locket_user_id} from '{old_name}' to '{new_name}' via /rename command.")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Successfully updated display name for Locket User ID '{locket_user_id}' to '{new_name}'."
        )
    except Exception as e:
        logging.error(f"Error processing /rename command for user {locket_user_id} to '{new_name}': {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"An error occurred while trying to rename user {locket_user_id}: {str(e)}"
        )

# --- Telegram Button Callback Handler ---
async def rename_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the inline button press to rename a Locket user."""
    query = update.callback_query
    
    # Try to answer the callback query, but continue even if it fails
    try:
        await query.answer()  # Acknowledge the button press
    except telegram.error.BadRequest as e:
        # If the query is too old, just log it and continue
        if "Query is too old" in str(e) or "query id is invalid" in str(e):
            logging.warning(f"Couldn't answer callback query: {e}")
        else:
            # For other BadRequest errors, re-raise
            raise
    
    # The callback data should be in format "rename:USER_ID"
    data_parts = query.data.split(":")
    if len(data_parts) != 2 or data_parts[0] != "rename":
        await query.message.reply_text("Invalid button data. Please try again.")
        return
    
    user_id = data_parts[1]
    current_name = USER_ID_TO_NAME.get(user_id, user_id)
    
    # Ask user to provide a new name
    response_message = await query.message.reply_text(
        f"Current name for user {user_id} is '{current_name}'.\n\n"
        f"Please reply to this message with the new display name you want to use.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Cancel", callback_data=f"cancel_rename:{user_id}")
        ]])
    )
    
    # Store the message ID and user ID to track the expected reply
    awaiting_rename_responses[response_message.message_id] = user_id
    
    logging.info(f"Waiting for rename reply for user {user_id} on message {response_message.message_id}")

# --- Cancel Rename Button Handler ---
async def cancel_rename_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancellation of the rename operation."""
    query = update.callback_query
    
    # Try to answer the callback query, but continue even if it fails
    try:
        await query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "query id is invalid" in str(e):
            logging.warning(f"Couldn't answer callback query: {e}")
        else:
            raise
    
    data_parts = query.data.split(":")
    if len(data_parts) != 2 or data_parts[0] != "cancel_rename":
        return
    
    user_id = data_parts[1]
    
    # Remove the message from our tracking dict
    # Find the message ID in awaiting_rename_responses where the value is user_id
    message_ids_to_remove = [
        msg_id for msg_id, uid in awaiting_rename_responses.items() if uid == user_id
    ]
    
    for msg_id in message_ids_to_remove:
        if msg_id in awaiting_rename_responses:
            del awaiting_rename_responses[msg_id]
    
    await query.message.edit_text(f"Renaming cancelled.")

# --- Reply Message Handler ---
async def handle_rename_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle replies to our rename request messages."""
    # Check if this is a reply to one of our tracked messages
    if not update.message or not update.message.reply_to_message:
        return
    
    reply_to_message_id = update.message.reply_to_message.message_id
    
    if reply_to_message_id in awaiting_rename_responses:
        user_id = awaiting_rename_responses[reply_to_message_id]
        new_name = update.message.text.strip()
        
        if not new_name:
            await update.message.reply_text("The new name cannot be empty. Please try again.")
            return
        
        # Update the name in our mapping
        old_name = USER_ID_TO_NAME.get(user_id, user_id)
        USER_ID_TO_NAME[user_id] = new_name
        
        # Save the updated mapping
        save_user_info(USER_INFO_FILE, USER_ID_TO_NAME)
        
        await update.message.reply_text(
            f"Successfully updated name for user {user_id} from '{old_name}' to '{new_name}'."
        )
        
        # Clean up our tracking dict
        del awaiting_rename_responses[reply_to_message_id]
        
        # Edit the original message to indicate completion
        try:
            await update.message.reply_to_message.edit_text(
                update.message.reply_to_message.text.split("\n\n")[0] + "\n\nName updated successfully!",
                reply_markup=None
            )
        except Exception as e:
            logging.error(f"Failed to edit the message: {e}")
        
        logging.info(f"User {update.effective_user.id} renamed Locket user {user_id} from '{old_name}' to '{new_name}' via inline button.")

# --- Token Refresh Function ---
async def refresh_token_periodically(auth_instance, api_instance):
    while True:
        try:
            logging.info("Attempting to refresh Locket API token...")
            new_token = await asyncio.to_thread(auth_instance.get_token)
            api_instance.token = new_token
            api_instance.headers['Authorization'] = f'Bearer {new_token}'
            logging.info("Successfully refreshed Locket API token.")
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
        await asyncio.sleep(1800)

# --- Locket Monitoring Loop ---
async def locket_monitor_loop(DOWNLOAD_DIR):
    global USER_ID_TO_NAME
    logging.info("Starting Locket monitoring loop...")
    while True:
        try:
            USER_ID_TO_NAME = load_user_info(USER_INFO_FILE)
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
                                    elif thumbnail_url:
                                        media_type = "png"
                                        final_media_path = png_path
                                        await asyncio.to_thread(download_and_convert_image_to_png_sync, thumbnail_url, png_path)
                                    else:
                                        logging.warning(f"No video_url or thumbnail_url for moment {moment_id}. Skipping download.")
                                        continue

                                    logging.info(f"Downloaded and saved {media_type.upper()} to: {final_media_path}")

                                    message = f"✨ New Locket from: {display_name}\n"
                                    message += f"💬 Caption: {caption}\n"
                                    message += f"🆔 Moment ID: {moment_id}"
                                    
                                    # Create inline keyboard with rename button only
                                    keyboard = [
                                        [InlineKeyboardButton("✏️ Rename User", callback_data=f"rename:{user_id}")]
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
    
    # Start background tasks
    token_refresh_task = asyncio.create_task(refresh_token_periodically(auth, api))
    locket_monitor_task = asyncio.create_task(locket_monitor_loop(DOWNLOAD_DIR))
    
    # Create the application but don't start it with run_polling
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("rename", rename_command_handler))
    
    # Add handlers for button clicks and replies - removed refresh and info handlers
    application.add_handler(CallbackQueryHandler(rename_button_handler, pattern="^rename:"))
    application.add_handler(CallbackQueryHandler(cancel_rename_handler, pattern="^cancel_rename:"))
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT & ~filters.COMMAND, handle_rename_reply))
    
    # Try to initialize the application with retries for network issues
    initialized = False
    max_retries = 5
    retry_count = 0
    
    while not initialized and retry_count < max_retries:
        try:
            logging.info(f"Attempting to initialize application (try {retry_count+1}/{max_retries})...")
            # Increase timeout for API requests
            telegram.request.HTTPXRequest.DEFAULT_READ_TIMEOUT = 60.0
            telegram.request.HTTPXRequest.DEFAULT_CONNECT_TIMEOUT = 60.0
            
            await application.initialize()
            # Get the application's own bot instance which is properly initialized
            app_bot = application.bot
            
            try:
                await app_bot.initialize()
                initialized = True
                logging.info("Application initialized successfully.")
            except telegram.error.TimedOut:
                logging.warning("Bot initialization timed out, but continuing anyway...")
                # We'll continue even if bot.initialize() times out
                app_bot = bot  # Fall back to our original bot instance
                initialized = True
                
        except Exception as e:
            retry_count += 1
            backoff_time = min(2 ** retry_count, 30)  # Exponential backoff, max 30s
            logging.error(f"Failed to initialize application: {e}. Retrying in {backoff_time}s...")
            await asyncio.sleep(backoff_time)
    
    if not initialized:
        logging.error("Failed to initialize application after multiple attempts. Continuing with limited functionality.")
        app_bot = bot  # Fall back to our original bot instance
    
    await application.start()
    
    # For v20.x, we can use the application's bot instance directly for updates
    offset = 0
    logging.info("Starting manual Telegram polling...")
    
    try:
        while True:
            try:
                # Get updates directly using the bot instance
                updates = await app_bot.get_updates(offset=offset, timeout=30)
                
                # Process each update through the application
                for update in updates:
                    offset = update.update_id + 1
                    
                    # Process update through the application
                    try:
                        await application.process_update(update)
                    except Exception as update_error:
                        logging.error(f"Error processing update: {update_error}")
                    
                # Small sleep to prevent excessive polling
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logging.error(f"Error in Telegram polling: {e}")
                await asyncio.sleep(5)  # Wait a bit before retrying
                
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutdown signal received.")
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}", exc_info=True)
    finally:
        logging.info("Stopping tasks...")
        
        # Stop the application gracefully
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

# Run the async main function
if __name__ == "__main__":
    try:
        # Manual event loop management
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