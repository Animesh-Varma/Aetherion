# Project Aetherion

## 🤖 Description

Raphael (default name) is a sophisticated and autonomous digital assistant designed to operate within an Instagram environment. It uses `uiautomator2` for UI automation to interact with the Instagram app and Google's Generative AI (Gemini Pro) to understand messages and generate intelligent, context-aware responses. Its primary role is to assist users effectively while serving the interests of its owner.

## ✨ Features

*   **Automatic Message Responding:** Monitors new DMs and provides automated responses via UI interaction.
*   **Intelligent Conversation:** Leverages Google's Generative AI for natural and relevant replies.
*   **Function Calling:** Can perform actions based on user requests or specific triggers:
    *   `notify_owner`: Alert the owner about important messages or situations.
    *   `send_message`: Send a message to a user or thread via UI interaction.
*   **Configurable:** Most operational parameters, API keys, and bot behavior parameters are configured via environment variables or directly in the script.
*   **Owner Controls:** Specific functions are restricted to the bot owner for security and control.
*   **Graceful Error Handling:** Designed to handle common issues and continue operation.

## Planned Features

*   `pause_auto_response`: Temporarily stop automatic replies for a specific chat.
*   `resume_auto_response`: Resume automatic replies for a chat.
*   `target_thread`: (Owner only) Focus the bot's attention on a specific DM thread.
*   `list_threads`: (Owner only) List all active DM threads.
*   `view_dms`: (Owner only) View past DMs in a thread.
*   `fetch_followers_followings`: Fetch followers and followings for an Instagram account (UI-Intensive).


## ⚙️ Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Animesh-Varma/Aetherion
    cd Aetherion
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables (`.env` file):**
    *   This is the **primary method for configuring the bot**.
    *   Copy the example `.env.example` file to a new file named `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Open the `.env` file and fill in your details for **all** the following variables:
        *   `API_KEY`: Your Google Generative AI API key.
        *   `OWNER_USERNAME`: The Instagram username of the bot's owner (this user will have access to restricted functions).
        *   `BOT_DISPLAY_NAME`: The name the bot will use in its messages (e.g., "Raphael").
        *   `BOT_INSTAGRAM_USERNAME`: The actual Instagram username of the bot account.
        *   `MESSAGE_FETCH_AMOUNT`: Number of recent messages to fetch from a thread (e.g., 10-20, UI dependent).
        *   `MIN_SLEEP_TIME`: Minimum time (in seconds) the bot waits between error recovery attempts (e.g., 5).
        *   `MAX_SLEEP_TIME`: Maximum time (in seconds) the bot waits between error recovery attempts (e.g., 15).
        *   `BLUE_DOT_CHECK_INTERVAL`: Time (in seconds) to wait between checking for unread DMs if none were found previously (e.g., 10).
        *   `THREAD_FETCH_AMOUNT`: (Currently unused) Number of recent threads to fetch (e.g., 10-20, UI dependent).
        *   `NOTIFICATION_CHECK_INTERVAL`: (Currently unused) Time (in seconds) to wait between checking notifications (e.g., 30).
        *   `DM_LIST_CHECK_INTERVAL`: (Currently unused) Time (in seconds) to wait between full DM list scans (e.g., 60).
        *   `device_ip`: IP address for your mobile device to connect adb

5.  **Prompt Templates (`config.py`):**
    *   The core AI prompt templates (`PROMPT_FIRST_TEMPLATE` and `PROMPT_SECOND_TEMPLATE`) are defined in `config.py`.
    *   While these can be inspected or even modified by advanced users wanting to significantly alter the bot's personality or core logic, most users will not need to change them for standard operation.

## ▶️ Running the Bot

1.  **Ensure Target Device is Ready:**
    *   Your Android device or emulator must be running and accessible via ADB.
    *   The `atx-agent` for `uiautomator2` must be initialized on the device (run `python -m uiautomator2 init --serial YOUR_DEVICE_ID` if needed).
    *   The Instagram app must be installed.
2.  **Set Device Identifier:**
    *   Update `d_device_identifier` in `Main.py` to your device's ID (e.g., from `adb devices`).
3.  **Run the Script:**
    *   Once setup and configuration (primarily through the `.env` file and `d_device_identifier` in `Main.py`) are complete, run the bot using:
    ```bash
    python Main.py
    ```
The bot will attempt to connect to the device, open Instagram, and start monitoring for new messages via UI interactions. To stop the bot, press `Ctrl+C` in the terminal.

## 🛠️ Built With

*   [uiautomator2](https://github.com/openatx/uiautomator2) - For Android UI Automation.
*   google-generativeai - For AI-powered responses.

## 👤 Creator

This bot was conceptualized and developed by Animesh Varma.
