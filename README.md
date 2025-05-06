# Locket Catcher

Downloads new Locket moments from your friends and sends notifications with the image to a Telegram chat. It also saves the images locally, converting them to PNG format.

## Features

*   Downloads Locket moments: videos are saved as MP4 if a direct video URL is provided by the API, otherwise images (from thumbnails) are saved as PNG.
*   Sends downloaded media (MP4 videos or PNG images) to Telegram.
*   User allow-list and user-friendly notifications.
*   Each media message in Telegram now has a "Rename" button.  
    *   Click "Rename" to set a display name for the user who posted the moment.
    *   After clicking, reply with the new name.  
    *   The mapping in `users_info.txt` is updated and reloaded automatically.

## Requirements

*   Python 3.8+
*   See `requirements.txt` for dependencies.

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

5.  **(Optional) Create `allow_list.txt`:**
    To receive notifications only for specific Locket users, create a file named `allow_list.txt` in the root directory of the project.
    Add one Locket User ID per line in this file. For example:
    ```
    user_id_1_to_allow
    another_user_id_to_allow
    ```
    If this file is empty or does not exist, you will receive notifications for all users.
    An example file `allow_list.txt.example` is provided to show the format.

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
