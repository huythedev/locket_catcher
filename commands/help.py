from telegram.ext import ContextTypes
from telegram import Update
import logging

async def help_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command to list all available commands and their usage."""
    chat_id = update.effective_chat.id
    try:
        help_text = (
            "📋 *Available Commands:*\n\n"
            "`/fetchfriends` - Fetch the list of friends from Locket.\n"
            "`/list` - List all known friends.\n"
            "`/allow <user_id>` - Allow notifications for a specific user ID.\n"
            "`/disallow <user_id>` - Disallow notifications for a specific user ID.\n"
            "`/allowlist` - Display all user IDs in the allow list.\n"
            "`/clearallowlist` - Clear all user IDs from the allow list.\n"
            "`/rename <user_id> <new_name>` - Rename a user in the local mapping.\n"
            "`/changeInfo` - Change your Locket account's first and last name (interactive).\n"
            "`/changeEmail <email>` - Change your Locket account's email.\n"
            "`/changePhoneNumber <phone>` - Change your Locket account's phone number.\n"
            "`/sendMessage <user_id> <message>` - Send a message to a Locket user.\n"
            "`/help` - Show this help message."
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=help_text,
            parse_mode="Markdown"
        )
        logging.info(f"Help command executed for chat {chat_id}")
    except Exception as e:
        logging.error(f"Error displaying help: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to display help: {str(e)}",
            parse_mode="Markdown"
        )