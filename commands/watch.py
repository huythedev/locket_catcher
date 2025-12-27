from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def watch_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /watch command to add user ID(s) to the watch list (whitelist mode)."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /watch <LocketUserID> [LocketUserID2] ...\nAdds user(s) to your watch list. When watch list is active, you ONLY receive notifications from watched users.\nExample: /watch user1 user2",
            parse_mode="Markdown"
        )
        return

    added = []
    already_exists = []
    invalid = []
    errors = []

    for user_id in args:
        user_id = user_id.strip()
        if not user_id or any(c in user_id for c in "\n:"):
            invalid.append(user_id)
            continue

        try:
            if user_id in main.WATCHED_USER_IDS:
                already_exists.append(user_id)
            else:
                main.WATCHED_USER_IDS.add(user_id)
                added.append(user_id)
                logging.info(f"Added user ID {user_id} to watch list")
        except Exception as e:
            logging.error(f"Error adding user ID {user_id} to watch list: {e}")
            errors.append(user_id)

    # Save only if we added any users
    if added:
        try:
            main.save_watched_users(main.WATCHED_USERS_FILE, main.WATCHED_USER_IDS)
        except Exception as e:
            logging.error(f"Error saving watch list: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Failed to save watch list: {str(e)}",
                parse_mode="Markdown"
            )
            return

    # Build response message
    response_parts = []
    if added:
        if len(added) == 1:
            response_parts.append(f"👁️ Now watching `{added[0]}`.")
        else:
            response_parts.append(f"👁️ Now watching {len(added)} user(s):\n" + "\n".join(f"  • `{uid}`" for uid in added))
    if already_exists:
        if len(already_exists) == 1:
            response_parts.append(f"ℹ️ `{already_exists[0]}` is already in your watch list.")
        else:
            response_parts.append(f"ℹ️ {len(already_exists)} user(s) already in watch list:\n" + "\n".join(f"  • `{uid}`" for uid in already_exists))
    if invalid:
        response_parts.append(f"❌ Invalid user ID(s): {', '.join(f'`{uid}`' for uid in invalid)}")
    if errors:
        response_parts.append(f"❌ Failed to add: {', '.join(f'`{uid}`' for uid in errors)}")
    
    # Add mode notice
    if main.WATCHED_USER_IDS:
        response_parts.append(f"\n⚠️ *Whitelist mode active*: You only receive notifications from {len(main.WATCHED_USER_IDS)} watched user(s).")

    await context.bot.send_message(
        chat_id=chat_id,
        text="\n\n".join(response_parts) if response_parts else "No changes made.",
        parse_mode="Markdown"
    )
