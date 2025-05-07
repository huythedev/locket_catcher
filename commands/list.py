from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def list_friends_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /list command to display the friend list from users_info.txt."""
    chat_id = update.effective_chat.id
    
    if not main.USER_ID_TO_NAME:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ No friends found in users_info.txt. Please run /fetchfriends to populate the list.",
            parse_mode="Markdown"
        )
        return
    
    # Prepare the friend list in chunks
    friends = sorted(main.USER_ID_TO_NAME.items(), key=lambda x: x[0])  # Sort by user_id
    chunk_size = 20  # Number of friends per message
    messages = []
    current_message = ["*Friend List:*"]
    current_length = len(current_message[0]) + 2  # Account for Markdown and newline
    
    for i, (user_id, display_name) in enumerate(friends, 1):
        # Format each friend entry
        entry = f"{i}. *{display_name}* (`{user_id}`)"
        entry_length = len(entry) + 1  # Account for newline
        
        # Check if adding this entry exceeds the Telegram message limit
        if current_length + entry_length > 4000:
            messages.append(current_message)
            current_message = ["*Friend List (continued):*"]
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
    
    logging.info(f"Sent friend list from users_info.txt to chat {chat_id}. Total friends: {len(main.USER_ID_TO_NAME)}")