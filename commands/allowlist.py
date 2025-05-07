from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def allowlist_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /allowlist command to display all user IDs in allow_list.txt."""
    chat_id = update.effective_chat.id

    if not main.ALLOWED_USER_IDS:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ No user IDs found in the allow list. Use /allow to add users.",
            parse_mode="Markdown"
        )
        return

    # Prepare the allow list in chunks
    user_ids = sorted(main.ALLOWED_USER_IDS)  # Sort for consistent display
    chunk_size = 20  # Number of user IDs per message
    messages = []
    current_message = ["*Allow List:*"]
    current_length = len(current_message[0]) + 2  # Account for Markdown and newline

    for i, user_id in enumerate(user_ids, 1):
        # Format each user ID entry
        entry = f"{i}. `{user_id}`"
        entry_length = len(entry) + 1  # Account for newline

        # Check if adding this entry exceeds the Telegram message limit
        if current_length + entry_length > 4000:
            messages.append(current_message)
            current_message = ["*Allow List (continued):*"]
            current_length = len(current_message[0]) + 2

        current_message.append(entry)
        current_length += entry_length

    # Append the last message if it has entries
    if len(current_message) > 1:
        messages.append(current_message)

    # Send the messages
    for message_lines in messages:
        message = "\n".join(message_lines)
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown"
        )

    logging.info(f"Sent allow list to chat {chat_id}. Total users: {len(main.ALLOWED_USER_IDS)}")