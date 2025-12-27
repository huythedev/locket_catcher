# Locket Catcher

Downloads new Locket moments from your friends and sends notifications with the image to a Telegram chat. It also saves the images locally, converting them to PNG format.

## Features

*   **Downloads Locket moments**: Videos are saved as MP4 if a direct video URL is provided by the API; otherwise, images (from thumbnails) are saved as PNG.
*   **Sends media to Telegram**: Downloaded MP4 videos or PNG images are sent to your specified Telegram chat.
*   **Flexible notification filtering**: Choose between two modes:
    *   **Whitelist mode**: Use `/watch` to only receive notifications from specific users (great if you only care about a few people)
    *   **Blacklist mode** (default): Use `/deny` to block specific users (great if you want everyone except a few)
*   **User-friendly notifications**: Each notification includes the user's display name and an inline "✏️ Rename User" button for easy renaming.
*   **User Name Management**:
    *   Rename Locket users for display in notifications via the `/rename <LocketUserID> <NewDisplayName>` command.
    *   Inline "✏️ Rename User" button under each notification for quick renaming.
    *   **Automatic User Name Fetching**: When a new Locket User ID is detected, the bot fetches the user's first and last name from the Locket API and saves it to `users_info.txt` automatically.
*   **Send Chat Message**: Send a chat message to a Locket user directly from Telegram using the `/sendChatMessage` command.
*   **Change Account Info**: Change your Locket account's name, email, or phone number via Telegram commands.

## Commands Usage

* Type `/help` and send to the bot, it'll list all available commands.

## Prerequisites

*   Python 3.8+
*   Pip (Python package installer)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/huythedev/locket_catcher.git
    cd locket_catcher
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Run the setup script:
    ```bash
    python setup.py
    ```
    This script will check if a `.env` file exists. If not, it will prompt you to enter the required information and create the file for you.

    The required variables are:
    *   `EMAIL`: Your Locket account email.
    *   `PASSWORD`: Your Locket account password.
    *   `TELEGRAM_BOT_TOKEN`: Your Telegram Bot token (get from BotFather).
    *   `TELEGRAM_CHAT_ID`: The ID of the Telegram chat where notifications should be sent.
        *   **How to find your Chat ID:**
            *   **For a private chat with the bot:** Send the `/start` command to your bot. Then, visit `https://api.telegram.org/bot<YourBOTToken>/getUpdates` (replace `<YourBOTToken>` with your actual bot token). Look for the `"chat":{"id": ...}` value in the JSON response. This is your chat ID (usually the same as your user ID).
            *   **For a group chat:** Add your bot to the group. Send any message in the group (e.g., `/my_id @your_bot_username`). Then, visit the `getUpdates` URL as described above. Find the message you sent in the response, and look for the `"chat":{"id": ...}` value. Group chat IDs are typically negative numbers.
            *   **Alternatively:** You can use bots like `@userinfobot` or `@getmyid_bot`. Add them to your chat or send them a message, and they will tell you the chat ID.

    If the `.env` file already exists, the script will let you know and check if all required variables seem to be present.

4.  **(Optional) Create `users_info.txt`:**
    If you want to display custom names instead of user IDs in Telegram messages, create a file named `users_info.txt` in the same directory. Add entries in the following format, one per line:
    ```
    "user_id_string":"Custom Name"
    "another_user_id":"Another Name"
    ```
    Replace `user_id_string` with the actual Locket user ID and `Custom Name` with the desired display name.

5.  **(Optional) Configure notification filtering:**
    
    **Whitelist mode** - Only receive from specific users (use `/watch` command or create `watched_users.txt`):
    ```
    user_id_to_watch
    another_user_id_to_watch
    ```
    
    **Blacklist mode** (default) - Block specific users (use `/deny` command or create `blocked_users.txt`):
    ```
    user_id_to_block
    another_user_id_to_block
    ```
    
    If watch list has entries, whitelist mode is active. Otherwise, blacklist mode is used.

### User Info (`users_info.txt`)

This file stores a mapping of Locket User IDs to custom display names. The format is `LocketUserID:DisplayName` per line.

Example:

```
BXcfLO4HaYWcUVz6Eduu9IzGeCl2:My Friend
fbop9326KApSjhF16DCc:Another Friend
```

If a user ID is not found in this file, the bot will now attempt to fetch the user's name (first name + last name) from the Locket API automatically and save it to this file. You can still use the rename features to override this fetched name.

## Usage

Run the script from your terminal:

```bash
python main.py
```

The script will start monitoring for new Locket moments. When a new moment is detected, it will be downloaded to the `locket_downloads` directory (organized by user ID). Videos are saved as MP4s if a direct video URL is available; otherwise, images are saved as PNGs from the thumbnail URL. A notification with the media will be sent to your specified Telegram chat.

When a new moment is posted, you'll see a "Rename" button under the media in Telegram. Click "Rename" and reply with the desired display name for that user. The mapping in `users_info.txt` is updated and reloaded automatically.

Press `Ctrl+C` to stop the script.

## Disclaimer

This script interacts with the Locket API, which might be against their terms of service. Use at your own risk. Authentication methods might change, breaking the script.
