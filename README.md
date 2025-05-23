# Instagram AI Assistant Bot - Raphael

## 🤖 Description

Raphael is a sophisticated and autonomous digital assistant designed to operate within an Instagram environment. It uses the `instagrapi` library to interact with Instagram DMs and Google's Generative AI (Gemini Pro) to understand messages and generate intelligent, context-aware responses. Its primary role is to assist users effectively while serving the interests of its owner.

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
*   **Configurable:** Prompts, API keys, and bot behavior parameters can be configured.
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

4.  **Set Up Environment Variables:**
    *   Copy the example `.env.example` file to a new file named `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Open the `.env` file and fill in your details:
        *   `API_KEY`: Your Google Generative AI API key.
        *   `SESSION_ID`: Your Instagram session ID.
            *   **Note on obtaining SESSION_ID:** You can get this by logging into Instagram in a web browser and inspecting the cookies for the `sessionid` value. This is a sensitive credential; keep it secure.
        *   `OWNER_USERNAME`: The Instagram username of the bot's owner (this user will have access to restricted functions).

## 🔧 Configuration

Beyond the environment variables in `.env`, additional bot parameters are located in `config.py`:

*   `BOT_NAME`: The name of the bot (e.g., "raphael").
*   `PROMPT_FIRST_TEMPLATE`, `PROMPT_SECOND_TEMPLATE`: The core prompt templates used for generating AI responses. These can be customized if needed.
*   `THREAD_FETCH_AMOUNT`: Number of recent threads to fetch in each cycle.
*   `MESSAGE_FETCH_AMOUNT`: Number of recent messages to fetch from a thread.
*   `MIN_SLEEP_TIME`, `MAX_SLEEP_TIME`: Minimum and maximum time (in seconds) the bot waits between checking for new messages.

## ▶️ Running the Bot

Once setup and configuration are complete, run the bot using:

```bash
python Main.py
```

The bot will log in and start monitoring for new messages. To stop the bot, press `Ctrl+C` in the terminal.

## 🛠️ Built With

*   [instagrapi](https://github.com/adw0rd/instagrapi) - For Instagram interaction.
*   [google-generativeai](https://github.com/google/generative-ai-python) - For AI-powered responses.

## 👤 Creator

This bot, Raphael, was conceptualized and developed by Animesh Varma.
