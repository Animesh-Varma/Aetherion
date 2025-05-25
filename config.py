# config.py
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
OWNER_USERNAME = os.getenv("OWNER_USERNAME")
BOT_NAME = os.getenv("BOT_NAME")

THREAD_FETCH_AMOUNT = int(os.getenv("THREAD_FETCH_AMOUNT", "10"))
MESSAGE_FETCH_AMOUNT = int(os.getenv("MESSAGE_FETCH_AMOUNT", "15"))
MIN_SLEEP_TIME = int(os.getenv("MIN_SLEEP_TIME", "60"))
MAX_SLEEP_TIME = int(os.getenv("MAX_SLEEP_TIME", "180"))

# Your PROMPT_FIRST_TEMPLATE and PROMPT_SECOND_TEMPLATE
# (Copied from your original script or refined)
PROMPT_FIRST_TEMPLATE = """
You are [[bot_username_in_context]], an AI assistant for [[owner_username]].
Current date: [[current_date]].
Message from: [[sender_username]] (Full Name: [[sender_full_name]], Followers: [[sender_follower_count]])
Thread ID (Peer/Group): [[thread_id]]
Approx. Timestamp: [[timestamp]]
Conversation History (User is [[sender_username]]):
[[history_text]]
New Message from [[sender_username]]: [[message_text]]
---
Based on this, decide if a function call is needed or if you should respond directly.
If unsure or message is complex, use notify_owner.
Note: 'sender_full_name' and 'sender_follower_count' might be 'Unknown (UI)' or 0 due to UI limitations.
"""

PROMPT_SECOND_TEMPLATE = """
You are [[bot_username_in_context]]. You just attempted/performed the function '[[function_name]]' in thread [[thread_id]]
for user [[sender_username]] (Full Name: [[sender_full_name]]).
Original message: "[[message_text]]"
Function execution details (summary of what you told the user you did):
Notify Owner Result: [[function_message_placeholder]]
Target Thread Result: [[target_thread_placeholder]]
Send Message Result: [[send_message_placeholder]]
List/View DMs Result: [[list_or_view_dms_placeholder]]
Fetch Followers/Followings Result: [[fetched_data_placeholder]]
Generic Action Summary: [[generic_function_result_placeholder]]
---
Formulate a user-friendly message explaining what you did or the result of the action based on the provided summary.
If a specific placeholder has content, use that. If not, use the generic summary or be concise.
"""