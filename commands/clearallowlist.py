from telegram.ext import ContextTypes
from telegram import Update
import main
from filelock import FileLock
import logging

async def clearallowlist_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /clearallowlist command to clear all user IDs from the allow list."""
    chat_id = update.effective_chat.id
    try:
        main.ALLOWED_USER_IDS.clear()
        with FileLock(main.ALLOW_LIST_FILE + ".lock"):
            with open(main.ALLOW_LIST_FILE, "w", encoding="utf-8") as f:
                f.truncate(0)  # Clear file contents
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Allow list cleared successfully.",
            parse_mode="Markdown"
        )
        logging.info(f"Allow list cleared by chat {chat_id}")
    except Exception as e:
        logging.error(f"Error clearing allow list: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to clear allow list: {str(e)}",
            parse_mode="Markdown"
        )