from telegram.ext import ContextTypes
from telegram import Update
import main
from filelock import FileLock
import logging

async def clearwatchlist_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /clearwatchlist command to clear the watch list and switch to blacklist mode."""
    chat_id = update.effective_chat.id
    try:
        count = len(main.WATCHED_USER_IDS)
        if count == 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text="ℹ️ Watch list is already empty. You're in blacklist mode.",
                parse_mode="Markdown"
            )
            return
            
        main.WATCHED_USER_IDS.clear()
        with FileLock(main.WATCHED_USERS_FILE + ".lock"):
            with open(main.WATCHED_USERS_FILE, "w", encoding="utf-8") as f:
                f.truncate(0)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Cleared watch list ({count} user(s)).\n\n✅ *Blacklist mode active*: You now receive notifications from everyone (except blocked users).",
            parse_mode="Markdown"
        )
        logging.info(f"Watch list cleared by chat {chat_id}")
    except Exception as e:
        logging.error(f"Error clearing watch list: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to clear watch list: {str(e)}",
            parse_mode="Markdown"
        )
