import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram import Update
import main
import logging

async def rename_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the inline button press to rename a Locket user."""
    query = update.callback_query
    try:
        await query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "query id is invalid" in str(e):
            logging.warning(f"Couldn't answer callback query: {e}")
        else:
            raise
    data_parts = query.data.split(":")
    if len(data_parts) != 2 or data_parts[0] != "rename":
        await query.message.reply_text("❌ Invalid button data. Please try again.", parse_mode="Markdown")
        return
    user_id = data_parts[1]
    current_name = main.USER_ID_TO_NAME.get(user_id, user_id)
    response_message = await query.message.reply_text(
        f"Current name for user `{user_id}` is *{current_name}*.\n\n"
        f"Please reply to this message with the new display name you want to use.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"cancel_rename:{user_id}")]])
    )
    main.awaiting_rename_responses[response_message.message_id] = user_id
    logging.info(f"Waiting for rename reply for user {user_id} on message {response_message.message_id}")

async def send_message_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the inline button press to send a message to a Locket user."""
    query = update.callback_query
    try:
        await query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "query id is invalid" in str(e):
            logging.warning(f"Couldn't answer callback query: {e}")
        else:
            raise
    data_parts = query.data.split(":")
    if len(data_parts) != 3 or data_parts[0] != "send_message":
        await query.message.reply_text("❌ Invalid button data.", parse_mode="Markdown")
        return
    user_id = data_parts[1]
    moment_id = data_parts[2]
    chat_id = query.message.chat_id
    response_message = await query.message.reply_text(
        f"Please reply to this message with the message you want to send to user `{user_id}`.",
        parse_mode="Markdown"
    )
    main.user_states[chat_id] = {
        "state": "awaiting_send_message",
        "receiver_uid": user_id,
        "moment_uid": moment_id
    }

async def cancel_rename_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancellation of the rename operation."""
    query = update.callback_query
    try:
        await query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "query id is invalid" in str(e):
            logging.warning(f"Couldn't answer callback query: {e}")
        else:
            raise
    data_parts = query.data.split(":")
    if len(data_parts) != 2 or data_parts[0] != "cancel_rename":
        return
    user_id = data_parts[1]
    message_ids_to_remove = [msg_id for msg_id, uid in main.awaiting_rename_responses.items() if uid == user_id]
    for msg_id in message_ids_to_remove:
        if msg_id in main.awaiting_rename_responses:
            del main.awaiting_rename_responses[msg_id]
    await query.message.edit_text(f"✅ Renaming cancelled.", parse_mode="Markdown")

# Define CallbackQueryHandler instances
rename_button_handler = CallbackQueryHandler(rename_button_handler, pattern="^rename:")
send_message_button_handler = CallbackQueryHandler(send_message_button_handler, pattern="^send_message:")
cancel_rename_handler = CallbackQueryHandler(cancel_rename_handler, pattern="^cancel_rename:")