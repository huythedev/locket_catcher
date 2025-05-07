from telegram.ext import ContextTypes
from telegram import Update
import main
import asyncio

async def change_email_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /changeEmail command to update the user's email."""
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage: /changeEmail <new_email>",
            parse_mode="Markdown"
        )
        return
    new_email = context.args[0]
    try:
        await asyncio.to_thread(main.api.changeEmail, new_email)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Email changed successfully.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Failed to change email: {str(e)}",
            parse_mode="Markdown"
        )