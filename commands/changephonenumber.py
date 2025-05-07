from telegram.ext import ContextTypes
from telegram import Update
import main
import asyncio

async def change_phone_number_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /changePhoneNumber command to update the user's phone number."""
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage: /changePhoneNumber <new_phone_number>",
            parse_mode="Markdown"
        )
        return
    new_phone_number = context.args[0]
    try:
        await asyncio.to_thread(main.api.changePhoneNumber, new_phone_number)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Phone number change initiated. Please check for verification code.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Failed to change phone number: {str(e)}",
            parse_mode="Markdown"
        )