from telegram.ext import ContextTypes
from telegram import Update
import main
import asyncio

async def send_message_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /sendMessage command to send a chat message."""
    args = context.args
    if len(args) < 2:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage: /sendMessage <receiver_uid> <message>\nExample: /sendMessage uid123 Hello there",
            parse_mode="Markdown"
        )
        return
    receiver_uid = args[0]
    message = " ".join(args[1:])
    try:
        await asyncio.to_thread(main.api.sendChatMessage, receiver_uid, main.api.token, message, moment_uid=None)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Message sent successfully.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Failed to send message: {str(e)}",
            parse_mode="Markdown"
        )