from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def disallow_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /disallow command to block a user ID - add to blocked_users.txt."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args or len(args) != 1:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /disallow <LocketUserID>\nBlocks a user so you won't receive their notifications.\nExample: /disallow BXcfLO4HaYWcUVz6Eduu9IzGeCl2",
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
        if user_id in main.BLOCKED_USER_IDS:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"ℹ️ User ID `{user_id}` is already blocked.",
                parse_mode="Markdown"
            )
            return

        main.BLOCKED_USER_IDS.add(user_id)
        main.save_blocked_users(main.BLOCKED_USERS_FILE, main.BLOCKED_USER_IDS)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚫 Blocked `{user_id}`. You won't receive their notifications.",
            parse_mode="Markdown"
        )
        logging.info(f"Blocked user ID {user_id} via /disallow")
    except Exception as e:
        logging.error(f"Error blocking user ID {user_id}: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to block user ID `{user_id}`: {str(e)}",
            parse_mode="Markdown"
        )