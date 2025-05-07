from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
import main
import asyncio
import logging

# States for the conversation
FIRST_NAME, LAST_NAME = range(2)

async def change_info_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiates the /changeInfo command to update the user's first and last name."""
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="Please enter your new first name:",
        parse_mode="Markdown"
    )
    return FIRST_NAME

async def handle_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the first name input and prompts for the last name."""
    chat_id = update.effective_chat.id
    first_name = update.message.text.strip()
    
    if not first_name:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ First name cannot be empty. Please enter your new first name:",
            parse_mode="Markdown"
        )
        return FIRST_NAME
    
    # Store first name in user_data
    context.user_data['first_name'] = first_name
    await context.bot.send_message(
        chat_id=chat_id,
        text="Please enter your new last name:",
        parse_mode="Markdown"
    )
    return LAST_NAME

async def handle_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the last name input and updates the user's name."""
    chat_id = update.effective_chat.id
    last_name = update.message.text.strip()
    
    if not last_name:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Last name cannot be empty. Please enter your new last name:",
            parse_mode="Markdown"
        )
        return LAST_NAME
    
    first_name = context.user_data.get('first_name')
    try:
        await asyncio.to_thread(main.api.changeInfo, last_name=last_name, first_name=first_name)
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Successfully changed your name.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Failed to change name for chat {chat_id}: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to change name: {str(e)}",
            parse_mode="Markdown"
        )
    finally:
        # Clear user_data
        context.user_data.clear()
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the /changeInfo conversation."""
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ Operation cancelled.",
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return ConversationHandler.END

# Define the ConversationHandler
conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("changeInfo", change_info_command_handler)],
    states={
        FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_first_name)],
        LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_last_name)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)