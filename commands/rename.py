from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def rename_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /rename command to update a user's display name."""
    command_text = update.message.text if update.message else "N/A"
    args_received = context.args if context.args else []
    logging.info(f"/rename command received from user {update.effective_user.id}. Full command: '{command_text}'. Args: {args_received}")

    chat_id = update.effective_chat.id

    if not context.args or len(context.args) < 2:
        logging.warning(f"/rename command: Incorrect arguments. User: {update.effective_user.id}, Args: {args_received}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /rename <LocketUserID> <NewDisplayName>\nExample: /rename BXcfLO4HaYWcUVz6Eduu9IzGeCl2 MyFriendName",
            parse_mode="Markdown"
        )
        return

    locket_user_id = context.args[0]
    new_name = " ".join(context.args[1:])

    if not locket_user_id or not new_name:
        logging.warning(f"/rename command: Missing LocketUserID or NewDisplayName. User: {update.effective_user.id}, LocketUserID: '{locket_user_id}', NewName: '{new_name}'")
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Error: Both Locket User ID and New Display Name must be provided.\nUsage: /rename <LocketUserID> <NewDisplayName>",
            parse_mode="Markdown"
        )
        return

    try:
        current_user_map_from_file = main.load_user_info(main.USER_INFO_FILE)
        old_name = current_user_map_from_file.get(locket_user_id, "this user (ID not previously known)")
        current_user_map_from_file[locket_user_id] = new_name
        main.save_user_info(main.USER_INFO_FILE, current_user_map_from_file)
        main.USER_ID_TO_NAME.update(current_user_map_from_file)
        logging.info(f"User {update.effective_user.id} renamed Locket user {locket_user_id} from '{old_name}' to '{new_name}' via /rename command.")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Successfully updated display name for Locket User ID '{locket_user_id}' to '{new_name}'.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error processing /rename command for user {locket_user_id} to '{new_name}': {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ An error occurred while trying to rename user {locket_user_id}: {str(e)}",
            parse_mode="Markdown"
        )