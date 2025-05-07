import asyncio
import logging
from telegram.ext import ContextTypes
from telegram import Update
import main

async def fetch_friends_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /fetchfriends command to fetch the list of friends."""
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Fetching friends list, please wait...")
    
    excluded_users = []
    main.FRIENDS_LIST.clear()
    logging.info("Starting to fetch friends list via /fetchfriends...")
    
    while True:
        try:
            # Pass excluded_users as a list to the API
            moment_response = await asyncio.to_thread(main.api.getLastMoment, excluded_users=excluded_users)
            if moment_response.get('result', {}).get('status') == 200:
                data = moment_response.get('result', {}).get('data', [])
                if not data:
                    logging.info("No more users found in getLastMoment response.")
                    break
                
                new_users = set()
                for moment in data:
                    user_id = moment.get('user')
                    if user_id and user_id not in excluded_users:
                        new_users.add(user_id)
                        main.FRIENDS_LIST.add(user_id)
                
                if not new_users:
                    logging.info("No new users found in this iteration.")
                    break
                
                # Add new users to excluded_users for the next iteration
                excluded_users.extend(new_users)
                logging.info(f"Fetched {len(new_users)} new user(s). Total friends: {len(main.FRIENDS_LIST)}. Excluded users: {len(excluded_users)}")
                
                # Update user names for new users
                for user_id in new_users:
                    if user_id not in main.USER_ID_TO_NAME:
                        try:
                            user_info_response = await asyncio.to_thread(main.api.getUserinfo, user_id)
                            if user_info_response.get('result', {}).get('status') == 200:
                                user_data = user_info_response.get('result', {}).get('data', {})
                                first_name = user_data.get('first_name', '')
                                last_name = user_data.get('last_name', '')
                                fetched_name = f"{first_name} {last_name}".strip()
                                if fetched_name:
                                    main.USER_ID_TO_NAME[user_id] = fetched_name
                                    main.save_user_info(main.USER_INFO_FILE, main.USER_ID_TO_NAME)
                                    logging.info(f"Fetched and saved name for {user_id}: {fetched_name}")
                                else:
                                    main.USER_ID_TO_NAME[user_id] = user_id
                                    main.save_user_info(main.USER_INFO_FILE, main.USER_ID_TO_NAME)
                                    logging.info(f"No name provided for {user_id}, using user ID")
                            else:
                                main.USER_ID_TO_NAME[user_id] = user_id
                                main.save_user_info(main.USER_INFO_FILE, main.USER_ID_TO_NAME)
                                logging.warning(f"Failed to fetch user info for {user_id}. Status: {user_info_response.get('result', {}).get('status')}")
                        except Exception as e:
                            main.USER_ID_TO_NAME[user_id] = user_id
                            main.save_user_info(main.USER_INFO_FILE, main.USER_ID_TO_NAME)
                            logging.error(f"Error fetching user info for {user_id}: {e}")
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
            else:
                logging.warning(f"getLastMoment API call failed. Status: {moment_response.get('result', {}).get('status')}")
                await context.bot.send_message(chat_id=chat_id, text="Failed to fetch friends list due to API error.")
                return
        except Exception as e:
            logging.error(f"Error fetching friends list: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"Error fetching friends list: {str(e)}")
            return
    
    # Send a concise summary message
    if main.FRIENDS_LIST:
        message = (
            f"✅ Successfully fetched friends list.\n"
            f"📊 Found {len(main.FRIENDS_LIST)} friends.\n"
            f"🔍 Use /list to view the detailed friend list."
        )
        logging.info(f"Completed fetching friends list. Total friends: {len(main.FRIENDS_LIST)}")
    else:
        message = "❌ No friends found."
        logging.info("No friends found in /fetchfriends.")
    
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")