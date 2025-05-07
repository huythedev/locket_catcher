from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def disallow_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /disallow command to remove a user ID from allow_list.txt."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args or len(args) != 1:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /disallow <LocketUserID>\nExample: /disallow BXcfLO4HaYWcUVz6Eduu9IzGeCl2",
            parse_mode="Markdown"
        )
        return

    user_id = args[0].strip()
    if not user_id or any(c in user_id for c in "\n:"):
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Invalid user ID. It must be non-empty and cannot contain newlines or colons.",
            parse_mode="Markdown"
        )
        return

    try:
        if user_id not in main.ALLOWED_USER_IDS:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ User ID `{user_id}` is not in the allow list.",
                parse_mode="Markdown"
            )
            return

        main.ALLOWED_USER_IDS.remove(user_id)
        main.save_allow_list(main.ALLOW_LIST_FILE, main.ALLOWED_USER_IDS)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Successfully removed user ID `{user_id}` from the allow list.",
            parse_mode="Markdown"
        )
        logging.info(f"Removed user ID {user_id} from allow_list.txt")
    except Exception as e:
        logging.error(f"Error removing user ID {user_id} from allow list: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to remove user ID `{user_id}` from allow list: {str(e)}",
            parse_mode="Markdown"
        )