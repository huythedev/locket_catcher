from telegram.ext import ContextTypes
from telegram import Update
import logging

async def help_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command to list all available commands and their usage."""
    chat_id = update.effective_chat.id
    try:
        help_text = (
            "📋 *Available Commands:*\n\n"
            "*👁️ Whitelist Mode (watch specific users):*\n"
            "`/watch <id> [id2] ...` - Watch user(s), only get their notifications\n"
            "`/unwatch <id> [id2] ...` - Stop watching user(s)\n"
            "`/watchlist` - Show watched users\n"
            "`/clearwatchlist` - Clear watch list (switch to blacklist mode)\n\n"
            "*🚫 Blacklist Mode (block specific users):*\n"
            "`/deny <id> [id2] ...` - Block user(s)\n"
            "`/allow <id> [id2] ...` - Unblock user(s)\n"
            "`/allowlist` - Show blocked users\n"
            "`/clearallowlist` - Unblock all users\n\n"
            "*👥 Friends & Settings:*\n"
            "`/fetchfriends` - Fetch friends from Locket\n"
            "`/list` - List all known friends\n"
            "`/rename <user_id> <name>` - Rename a user\n"
            "`/sendMessage <user_id> <msg>` - Send a message\n"
            "`/changeInfo` - Change your Locket name\n"
            "`/changeEmail <email>` - Change email\n"
            "`/changePhoneNumber <phone>` - Change phone\n"
            "`/help` - Show this help"
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