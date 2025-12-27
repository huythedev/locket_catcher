from telegram.ext import ContextTypes
from telegram import Update
import main
import logging

async def deny_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /deny command to block user ID(s) - add to blocked_users.txt."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /deny <LocketUserID> [LocketUserID2] ...\nBlocks user(s) so you won't receive their notifications.\nExample: /deny user1 user2",
            parse_mode="Markdown"
        )
        return

    blocked = []
    already_blocked = []
    invalid = []
    errors = []

    for user_id in args:
        user_id = user_id.strip()
        if not user_id or any(c in user_id for c in "\n:"):
            invalid.append(user_id)
            continue

        try:
            if user_id in main.BLOCKED_USER_IDS:
                already_blocked.append(user_id)
            else:
                main.BLOCKED_USER_IDS.add(user_id)
                blocked.append(user_id)
                logging.info(f"Blocked user ID {user_id}")
        except Exception as e:
            logging.error(f"Error blocking user ID {user_id}: {e}")
            errors.append(user_id)

    # Save only if we blocked any users
    if blocked:
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
    if blocked:
        if len(blocked) == 1:
            response_parts.append(f"🚫 Blocked `{blocked[0]}`. You won't receive their notifications.")
        else:
            response_parts.append(f"🚫 Blocked {len(blocked)} user(s):\n" + "\n".join(f"  • `{uid}`" for uid in blocked))
    if already_blocked:
        if len(already_blocked) == 1:
            response_parts.append(f"ℹ️ `{already_blocked[0]}` is already blocked.")
        else:
            response_parts.append(f"ℹ️ {len(already_blocked)} user(s) already blocked:\n" + "\n".join(f"  • `{uid}`" for uid in already_blocked))
    if invalid:
        response_parts.append(f"❌ Invalid user ID(s): {', '.join(f'`{uid}`' for uid in invalid)}")
    if errors:
        response_parts.append(f"❌ Failed to block: {', '.join(f'`{uid}`' for uid in errors)}")

    await context.bot.send_message(
        chat_id=chat_id,
        text="\n\n".join(response_parts) if response_parts else "No changes made.",
        parse_mode="Markdown"
    )
        )
