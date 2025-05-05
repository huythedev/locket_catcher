# Locket Catcher

Downloads new Locket moments from your friends and sends notifications with the image to a Telegram chat. It also saves the images locally, converting them to PNG format. 

## Features

*   Monitors Locket for new moments.
*   Downloads new moments automatically.
*   Converts downloaded WebP images to PNG.
*   Saves images locally, organized by user ID.
*   Sends notifications (message + image) to a specified Telegram chat.
*   Allows mapping user IDs to custom names for notifications using `users_info.txt`.
*   Uses asynchronous operations for better performance.

## Prerequisites

*   Python 3.7+
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

3.  **Create `.env` file:**
    Copy the example file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and fill in your actual credentials:
    *   `EMAIL`: Your Locket account email.
    *   `PASSWORD`: Your Locket account password.
    *   `TELEGRAM_BOT_TOKEN`: Your Telegram Bot token (get from BotFather).
    *   `TELEGRAM_CHAT_ID`: The ID of the Telegram chat where notifications should be sent.
        *   **How to find your Chat ID:**
            *   **For a private chat with the bot:** Send the `/start` command to your bot. Then, visit `https://api.telegram.org/bot<YourBOTToken>/getUpdates` (replace `<YourBOTToken>` with your actual bot token). Look for the `"chat":{"id": ...}` value in the JSON response. This is your chat ID (usually the same as your user ID).
            *   **For a group chat:** Add your bot to the group. Send any message in the group (e.g., `/my_id @your_bot_username`). Then, visit the `getUpdates` URL as described above. Find the message you sent in the response, and look for the `"chat":{"id": ...}` value. Group chat IDs are typically negative numbers.
            *   **Alternatively:** You can use bots like `@userinfobot` or `@getmyid_bot`. Add them to your chat or send them a message, and they will tell you the chat ID.

4.  **(Optional) Create `users_info.txt`:**
    If you want to display custom names instead of user IDs in Telegram messages, create a file named `users_info.txt` in the same directory. Add entries in the following format, one per line:
    ```
    "user_id_string":"Custom Name"
    "another_user_id":"Another Name"
    ```
    Replace `user_id_string` with the actual Locket user ID and `Custom Name` with the desired display name.

## Usage

Run the script from your terminal:

```bash
python main.py
```

The script will start monitoring for new Locket moments. When a new moment is detected, it will be downloaded to the `locket_downloads` directory (organized by user ID), converted to PNG, and a notification will be sent to your specified Telegram chat.

Press `Ctrl+C` to stop the script.

## Disclaimer

This script interacts with the Locket API, which might be against their terms of service. Use at your own risk. Authentication methods might change, breaking the script.
