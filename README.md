# Project Aetherion

## 🤖 Description

Raphael (default name) is a sophisticated and autonomous digital assistant designed to operate within an Instagram environment. It uses the `instagrapi` library to interact with Instagram DMs and Google's Generative AI (Gemini Pro) to understand messages and generate intelligent, context-aware responses. Its primary role is to assist users effectively while serving the interests of its owner.

## ✨ Features

*   **Automatic Message Responding:** Monitors new DMs and provides automated responses.
*   **Intelligent Conversation:** Leverages Google's Generative AI for natural and relevant replies.
*   **Function Calling:** Can perform actions based on user requests or specific triggers:
    *   `notify_owner`: Alert the owner about important messages or situations.
    *   `pause_auto_response`: Temporarily stop automatic replies for a specific chat.
    *   `resume_auto_response`: Resume automatic replies for a chat.
    *   `target_thread`: (Owner only) Focus the bot's attention on a specific DM thread.
    *   `send_message`: Send a message to a user or thread.
    *   `list_threads`: (Owner only) List all active DM threads.
    *   `view_dms`: (Owner only) View past DMs in a thread.
    *   `fetch_followers_followings`: Fetch followers and followings for an Instagram account.
*   **Configurable:** Most operational parameters, API keys, and bot behavior parameters are configured via environment variables.
*   **Owner Controls:** Specific functions are restricted to the bot owner for security and control.
*   **Graceful Error Handling:** Designed to handle common issues and continue operation.

## ⚙️ Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/yourusername/your-repo-name
    cd your-repo-name
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
        *   `SESSION_ID`: Your Instagram session ID.
            *   **Note on obtaining SESSION_ID:** You can get this by logging into Instagram in a web browser and inspecting the cookies for the `sessionid` value. This is a sensitive credential; keep it secure.
        *   `OWNER_USERNAME`: The Instagram username of the bot's owner (this user will have access to restricted functions).
        *   `BOT_NAME`: The name the bot will use (e.g., "raphael").
        *   `THREAD_FETCH_AMOUNT`: Number of recent threads to fetch (e.g., 20).
        *   `MESSAGE_FETCH_AMOUNT`: Number of recent messages to fetch from a thread (e.g., 50).
        *   `MIN_SLEEP_TIME`: Minimum time (in seconds) the bot waits between checking for new messages (e.g., 1).
        *   `MAX_SLEEP_TIME`: Maximum time (in seconds) the bot waits between checking for new messages (e.g., 6).

## 🔧 Configuration

Primary configuration is managed through environment variables as described in the "Setup Instructions" section.

1.  **Environment Variables (`.env` file):**
    *   Ensure you have copied `.env.example` to `.env` and filled it out. This file controls essential credentials and operational parameters:
        *   `API_KEY`: Your Google Generative AI API key.
        *   `SESSION_ID`: Your Instagram session ID.
        *   `OWNER_USERNAME`: The Instagram username of the bot's owner.
        *   `BOT_NAME`: The name the bot will use (default: "raphael" if not set in `.env`).
        *   `THREAD_FETCH_AMOUNT`: Number of recent threads to fetch (default: 20 if not set in `.env`).
        *   `MESSAGE_FETCH_AMOUNT`: Number of recent messages to fetch from a thread (default: 50 if not set in `.env`).
        *   `MIN_SLEEP_TIME`: Minimum time (seconds) bot waits between checks (default: 1 if not set in `.env`).
        *   `MAX_SLEEP_TIME`: Maximum time (seconds) bot waits between checks (default: 6 if not set in `.env`).

2.  **Prompt Templates (`config.py`):**
    *   The core AI prompt templates (`PROMPT_FIRST_TEMPLATE` and `PROMPT_SECOND_TEMPLATE`) are defined in `config.py`.
    *   While these can be inspected or even modified by advanced users wanting to significantly alter the bot's personality or core logic, most users will not need to change them for standard operation.

## ▶️ Running the Bot

Once setup and configuration (primarily through the `.env` file) are complete, run the bot using:

```bash
python Main.py
```

The bot will log in and start monitoring for new messages. To stop the bot, press `Ctrl+C` in the terminal.

## 🛠️ Built With

*   [instagrapi](https://github.com/adw0rd/instagrapi) - For Instagram interaction.
*   [google-generativeai](https://github.com/google/generative-ai-python) - For AI-powered responses.

## 👤 Creator

This bot was conceptualized and developed by Animesh Varma.
