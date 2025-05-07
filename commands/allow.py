from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def allow_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /allow command to add a user ID to allow_list.txt."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args or len(args) != 1:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /allow <LocketUserID>\nExample: /allow BXcfLO4HaYWcUVz6Eduu9IzGeCl2",
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
        if user_id in main.ALLOWED_USER_IDS:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ User ID `{user_id}` is already in the allow list.",
                parse_mode="Markdown"
            )
            return

        main.ALLOWED_USER_IDS.add(user_id)
        main.save_allow_list(main.ALLOW_LIST_FILE, main.ALLOWED_USER_IDS)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Successfully added user ID `{user_id}` to the allow list.",
            parse_mode="Markdown"
        )
        logging.info(f"Added user ID {user_id} to allow_list.txt")
    except Exception as e:
        logging.error(f"Error adding user ID {user_id} to allow list: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to add user ID `{user_id}` to allow list: {str(e)}",
            parse_mode="Markdown"
        )