from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def allow_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /allow command to unblock user ID(s) - remove from blocked_users.txt."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /allow <LocketUserID> [LocketUserID2] ...\nUnblocks user(s) so you receive their notifications.\nExample: /allow user1 user2",
            parse_mode="Markdown"
        )
        return

    unblocked = []
    not_blocked = []
    invalid = []
    errors = []

    for user_id in args:
        user_id = user_id.strip()
        if not user_id or any(c in user_id for c in "\n:"):
            invalid.append(user_id)
            continue

        try:
            if user_id not in main.BLOCKED_USER_IDS:
                not_blocked.append(user_id)
            else:
                main.BLOCKED_USER_IDS.remove(user_id)
                unblocked.append(user_id)
                logging.info(f"Unblocked user ID {user_id}")
        except Exception as e:
            logging.error(f"Error unblocking user ID {user_id}: {e}")
            errors.append(user_id)

    # Save only if we unblocked any users
    if unblocked:
        try:
            main.save_blocked_users(main.BLOCKED_USERS_FILE, main.BLOCKED_USER_IDS)
        except Exception as e:
            logging.error(f"Error saving blocked users list: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Failed to save blocked users list: {str(e)}",
                parse_mode="Markdown"
            )
            return

    # Build response message
    response_parts = []
    if unblocked:
        if len(unblocked) == 1:
            response_parts.append(f"✅ Unblocked `{unblocked[0]}`. You will now receive their notifications.")
        else:
            response_parts.append(f"✅ Unblocked {len(unblocked)} user(s):\n" + "\n".join(f"  • `{uid}`" for uid in unblocked))
    if not_blocked:
        if len(not_blocked) == 1:
            response_parts.append(f"ℹ️ `{not_blocked[0]}` was not blocked.")
        else:
            response_parts.append(f"ℹ️ {len(not_blocked)} user(s) were not blocked:\n" + "\n".join(f"  • `{uid}`" for uid in not_blocked))
    if invalid:
        response_parts.append(f"❌ Invalid user ID(s): {', '.join(f'`{uid}`' for uid in invalid)}")
    if errors:
        response_parts.append(f"❌ Failed to unblock: {', '.join(f'`{uid}`' for uid in errors)}")

    await context.bot.send_message(
        chat_id=chat_id,
        text="\n\n".join(response_parts) if response_parts else "No changes made.",
        parse_mode="Markdown"
    )