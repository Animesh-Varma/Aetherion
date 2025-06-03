# Project Aetherion

## Description

Raphael (default name) is a sophisticated and autonomous digital assistant designed to operate within an Instagram environment. It uses `uiautomator2` for UI automation to interact with the Instagram app and Google's Generative AI (Gemini Pro) to understand messages and generate intelligent, context-aware responses. Its primary role is to assist users effectively while serving the interests of its owner. It's worth noting that with the advent of Meta AI integrated directly within Instagram, some of the bot's current Instagram-focused functionalities might seem redundant. However, Aetherion's vision extends far beyond this initial scope.

## ✨ Features

*   **Automatic Message Responding:** Monitors new DMs and provides automated responses via UI interaction.
*   **Intelligent Conversation:** Leverages Google's Generative AI for natural and relevant replies.
*   **Function Calling:** Can perform actions based on user requests or specific triggers:
    *   `notify_owner`: Alert the owner about important messages or situations.
    *   `send_message`: Send a message to a user or thread via UI interaction.
*   **Configurable:** Most operational parameters, API keys, and bot behavior parameters are configured via environment variables or directly in the script.
*   **Owner Controls:** Specific functions are restricted to the bot owner for security and control. (Awaiting implementation)
*   **Graceful Error Handling:** Designed to handle common issues and continue operation.

## Planned Features

*   `pause_auto_response`: Temporarily stop automatic replies for a specific chat.
*   `resume_auto_response`: Resume automatic replies for a chat.
*   `target_thread`: (Owner only) Focus the bot's attention on a specific DM thread.
*   `list_threads`: (Owner only) List all active DM threads.
*   `view_dms`: (Owner only) View past DMs in a thread.
*   `fetch_followers_followings`: Fetch followers and followings for an Instagram account (UI-Intensive).

## Future Vision
The long-term goal for Aetherion is to evolve beyond Instagram and become a comprehensive, device-wide automaton service. I envision a powerful assistant capable of:

*   **Interacting with various communication platforms:** Seamlessly manage conversations and tasks across WhatsApp and SMS.
*   **Handling calls:** Potentially assisting with call management or transcription.
*   **Local AI Processing:** Integrating with technologies like Ollama to run AI models locally on Android devices. This is a significant step towards greater privacy, personalization, and offline capabilities, though it's a feature that will require substantial development effort.

This broader scope aims to make Aetherion an indispensable tool for managing digital interactions and tasks across your entire mobile experience.

## 📋 Prerequisites

Before you begin, ensure you have the following installed and configured:

*   **Python:** Version 3.12.0 or higher.
*   **ADB (Android Debug Bridge):** Installed and added to your system's PATH. You can get this with [SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) (as part of SDK Platform Tools) or as a standalone download.
*   **Android Device/Emulator:**
    *   An Android device or emulator running.
    *   Developer Options enabled on the device/emulator.
    *   USB Debugging enabled within Developer Options.
    *   Install app via USB enabled within Developer Options.
*   **Instagram App:**
    *   The official Instagram application installed on the target Android device/emulator.
    *   The Instagram account intended for the bot must be logged into the app on this device.
*   **Google Generative AI API Key:** You'll need an API key from [Google AI Studio](https://aistudio.google.com/apikey) for Gemini API access.

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
    *   Open the `.env` file and fill in your details for **all** the following variables (for more detail check .env.example):
        *   `API_KEY`: Your Google Generative AI API key.
        *   `OWNER_USERNAME`: The Instagram username of the bot's owner (this user will have access to restricted functions).
        *   `BOT_DISPLAY_NAME`: The name the bot will use in its messages (e.g., "Raphael").
        *   `BOT_INSTAGRAM_USERNAME`: The actual Instagram username of the bot account.
        *   `BLUE_DOT_CHECK_INTERVAL`: Time (in seconds) to wait between checking for unread DMs if none were found previously (e.g., 10).
        *   `DEVICE_IDENTIFIER`: IP address for your mobile device to connect adb or the device id if connecting with usb.

5.  **Prompt Templates (`config.py`):**
    *   The core AI prompt templates (`PROMPT_FIRST_TEMPLATE` and `PROMPT_SECOND_TEMPLATE`) are defined in `config.py`.
    *   While these can be inspected or even modified by advanced users wanting to significantly alter the bot's personality or core logic, most users will not need to change them for standard operation.

## ▶️ Running the Bot

1.  **Ensure Target Device is Ready:**
    *   Your Android device or emulator must be running and accessible via ADB.
    *   The `atx-agent` for `uiautomator2` must be initialized on the device (run `python -m uiautomator2 init --serial YOUR_DEVICE_ID` if needed). 
    *   The Instagram app must be installed.
2.  **Run the Script:**
    *   Once setup and configuration (primarily through the `.env` file) are complete, run the bot using:
    ```bash
    python Main.py
    ```
The bot will attempt to connect to the device, open Instagram, and start monitoring for new messages via UI interactions. To stop the bot, press `Ctrl+C` in the terminal.

## 🛠️ Built With

*   [uiautomator2](https://github.com/openatx/uiautomator2) - For Android UI Automation.
*   google-generativeai - For AI-powered responses.

## 👤 Creator

This bot was conceptualized and developed by Animesh Varma.

> ⚠️ **Disclaimer:** This project includes content generated or assisted by AI tools (e.g., Jules and Gemini 2.5 Pro). Rest assured the generated content was edited and entirely reviewed by me.
