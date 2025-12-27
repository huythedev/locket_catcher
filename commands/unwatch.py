from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def unwatch_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /unwatch command to remove user ID(s) from the watch list."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /unwatch <LocketUserID> [LocketUserID2] ...\nRemoves user(s) from your watch list.\nExample: /unwatch user1 user2",
            parse_mode="Markdown"
        )
        return

    removed = []
    not_found = []
    invalid = []
    errors = []

    for user_id in args:
        user_id = user_id.strip()
        if not user_id or any(c in user_id for c in "\n:"):
            invalid.append(user_id)
            continue

        try:
            if user_id not in main.WATCHED_USER_IDS:
                not_found.append(user_id)
            else:
                main.WATCHED_USER_IDS.remove(user_id)
                removed.append(user_id)
                logging.info(f"Removed user ID {user_id} from watch list")
        except Exception as e:
            logging.error(f"Error removing user ID {user_id} from watch list: {e}")
            errors.append(user_id)

    # Save only if we removed any users
    if removed:
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
    if removed:
        if len(removed) == 1:
            response_parts.append(f"✅ Stopped watching `{removed[0]}`.")
        else:
            response_parts.append(f"✅ Stopped watching {len(removed)} user(s):\n" + "\n".join(f"  • `{uid}`" for uid in removed))
    if not_found:
        if len(not_found) == 1:
            response_parts.append(f"ℹ️ `{not_found[0]}` was not in your watch list.")
        else:
            response_parts.append(f"ℹ️ {len(not_found)} user(s) were not in watch list:\n" + "\n".join(f"  • `{uid}`" for uid in not_found))
    if invalid:
        response_parts.append(f"❌ Invalid user ID(s): {', '.join(f'`{uid}`' for uid in invalid)}")
    if errors:
        response_parts.append(f"❌ Failed to remove: {', '.join(f'`{uid}`' for uid in errors)}")
    
    # Add mode notice
    if main.WATCHED_USER_IDS:
        response_parts.append(f"\n⚠️ *Whitelist mode active*: You only receive notifications from {len(main.WATCHED_USER_IDS)} watched user(s).")
    else:
        response_parts.append(f"\n✅ *Blacklist mode active*: You receive notifications from everyone (except blocked users).")

    await context.bot.send_message(
        chat_id=chat_id,
        text="\n\n".join(response_parts) if response_parts else "No changes made.",
        parse_mode="Markdown"
    )
