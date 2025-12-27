from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def watchlist_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /watchlist command to display all watched user IDs."""
    chat_id = update.effective_chat.id

    if not main.WATCHED_USER_IDS:
        await context.bot.send_message(
            chat_id=chat_id,
            text="👁️ *Watch list is empty.*\n\n✅ *Blacklist mode active*: You receive notifications from everyone (except blocked users).\n\nUse `/watch <user_id>` to switch to whitelist mode.",
            parse_mode="Markdown"
        )
        return

    # Prepare the watched users list in chunks
    user_ids = sorted(main.WATCHED_USER_IDS)
    messages = []
    current_message = [f"👁️ *Watched Users ({len(user_ids)}):*\n⚠️ _Whitelist mode: Only these users' notifications are received._"]
    current_length = len(current_message[0]) + 2

    for i, user_id in enumerate(user_ids, 1):
        entry = f"{i}. `{user_id}`"
        entry_length = len(entry) + 1

        if current_length + entry_length > 4000:
            messages.append(current_message)
            current_message = ["*👁️ Watched Users (continued):*"]
            current_length = len(current_message[0]) + 2

        current_message.append(entry)
        current_length += entry_length

    if len(current_message) > 1:
        messages.append(current_message)

    for message_lines in messages:
        message = "\n".join(message_lines)
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown"
        )

    logging.info(f"Sent watch list to chat {chat_id}. Total watched: {len(main.WATCHED_USER_IDS)}")
