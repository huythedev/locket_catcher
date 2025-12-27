from telegram.ext import ContextTypes
from telegram import Update
import main
from filelock import FileLock
import logging

async def clearallowlist_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /clearallowlist command to unblock all users."""
    chat_id = update.effective_chat.id
    try:
        count = len(main.BLOCKED_USER_IDS)
        main.BLOCKED_USER_IDS.clear()
        with FileLock(main.BLOCKED_USERS_FILE + ".lock"):
            with open(main.BLOCKED_USERS_FILE, "w", encoding="utf-8") as f:
                f.truncate(0)  # Clear file contents
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Unblocked all users ({count} total). You will now receive notifications from everyone.",
            parse_mode="Markdown"
        )
        logging.info(f"Blocked users list cleared by chat {chat_id}")
    except Exception as e:
        logging.error(f"Error clearing blocked users list: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to clear blocked users list: {str(e)}",
            parse_mode="Markdown"
        )