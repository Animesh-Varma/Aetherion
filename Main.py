from instagrapi import Client
import time
import signal
from datetime import datetime
from config import API_KEY, SESSION_ID, OWNER_USERNAME
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

cl = Client()
BOT_NAME = "raphael"
auto_responding = True
owner_id = None
bot_id = None
genai.configure(api_key=API_KEY)
start_time = datetime.now()
last_checked_timestamps = {}
processed_message_ids = set()

notify_owner_func = FunctionDeclaration(
    name="notify_owner",
    description="Notify the owner about a message.",
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message content to send to the owner"},
            "thread_id": {"type": "string", "description": "Thread ID where the message originated"}
        },
        "required": ["message", "thread_id"]
    }
)

pause_response_func = FunctionDeclaration(
    name="pause_auto_response",
    description="Pause the auto-response feature.",
)

resume_response_func = FunctionDeclaration(
    name="resume_auto_response",
    description="Resume the auto-response feature.",
)

tools = Tool(function_declarations=[notify_owner_func, pause_response_func, resume_response_func])

model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25", tools=[tools])


def send_message_to_owner(message):
    global owner_id
    try:
        if owner_id is None:
            raise ValueError("Owner ID not initialized. Login may have failed.")
        cl.direct_send(message, [owner_id])
        print(f"Sent message to {OWNER_USERNAME}: {message}")
    except Exception as e:
        print(f"Failed to send message to owner: {e}")

def login():
    global owner_id, bot_id
    try:
        cl.login_by_sessionid(SESSION_ID)
        bot_info = cl.user_info_v1(cl.user_id)
        bot_id = bot_info.pk
        owner_info = cl.user_info_by_username_v1(OWNER_USERNAME)
        owner_id = owner_info.pk
        print(f"Logged in as {cl.username}, bot ID: {bot_id}, owner ID: {owner_id}")
        return True
    except Exception as e:
        print(f"Login failed: {e}")
        return False

def print_user_info():
    try:
        user_info = cl.user_info_v1(cl.user_id)
        print(f"Username: {user_info.username}")
        print(f"Full Name: {user_info.full_name}")
        print(f"Biography: {user_info.biography}")
        print(f"Followers: {user_info.follower_count}")
    except Exception as e:
        print(f"Failed to retrieve user info: {e}")


def auto_respond():
    global auto_responding, last_checked_timestamps, processed_message_ids
    chat = model.start_chat(history=[])
    while True:
        try:
            threads = cl.direct_threads(amount=20)
            for thread in threads:
                thread_id = thread.id
                last_timestamp = last_checked_timestamps.get(thread_id, start_time)

                messages = cl.direct_messages(thread_id, amount=50)
                new_messages = [msg for msg in messages if msg.timestamp > last_timestamp]

                if not new_messages:
                    print(f"No new messages in thread {thread_id}")
                    continue

                for message in new_messages:
                    message_id = message.id
                    if message_id in processed_message_ids:
                        print(f"Skipping already processed message {message_id} in thread {thread_id}")
                        continue

                    if str(message.user_id) == str(bot_id):
                        print(f"Ignoring bot's own message {message_id} in thread {thread_id}: {message.text}")
                        continue

                    message_text = message.text
                    sender_id = message.user_id

                    if not auto_responding:
                        print(
                            f"{time.ctime()} - Auto-response paused, checking for resume command in thread {thread_id}")
                        if message_text and any(keyword in message_text.lower() for keyword in
                                                ["resume", "start", "enable", "unpause"]):
                            auto_responding = True
                            cl.direct_send("Auto-response resumed.", [thread.users[0].pk])
                            print(f"Auto-response resumed in thread {thread_id}")
                            processed_message_ids.add(message_id)
                        continue

                    print(f"New DM in thread {thread_id} from {sender_id}: {message_text}")

                    cl.direct_send("request acknowledged. Please wait for Raphael to respond....", [thread.users[0].pk])
                    print(f"Sent acknowledgment to {thread.users[0].pk} in thread {thread_id}")

                    conversation_history = []
                    for msg in messages:
                        if msg.timestamp > start_time and (msg.user_id == sender_id or str(msg.user_id) == str(bot_id)):
                            role = "User" if msg.user_id == sender_id else "Raphael"
                            conversation_history.append(f"{role}: {msg.text}")

                    history_text = "\n".join(conversation_history)
                    prompt = f"""
                    You are Raphael, an autonomous agent on Instagram running on {cl.username}.
                    Your owner is {OWNER_USERNAME}. Below is the conversation history with the user since I started:


                    {history_text}


                    The latest message from the user is: "{message_text}".
                    Respond to this message appropriately based on the history.
                    Use available tools (notify_owner, pause_auto_response, resume_auto_response) when appropriate.
                    Keep responses concise and natural.
                    If meeting the user for the first time, introduce yourself.
                    """

                    response = chat.send_message(prompt)

                    function_call_handled = False
                    for part in response.parts:
                        if part.function_call:
                            func_call = part.function_call
                            if func_call.name == "notify_owner":
                                args = func_call.args
                                send_message_to_owner(
                                    f"Raphael was triggered in thread {args['thread_id']}: '{args['message']}'")
                                cl.direct_send(f"Notified {OWNER_USERNAME}.", [thread.users[0].pk])
                                print(f"Elevated awareness in thread {thread_id}")
                            elif func_call.name == "pause_auto_response":
                                auto_responding = False
                                cl.direct_send("Auto-response paused.", [thread.users[0].pk])
                                print(f"Auto-response paused in thread {thread_id}")
                            elif func_call.name == "resume_auto_response":
                                auto_responding = True
                                cl.direct_send("Auto-response resumed.", [thread.users[0].pk])
                                print(f"Auto-response resumed in thread {thread_id}")
                            function_call_handled = True

                    if not function_call_handled and response.text:
                        reply = response.text.strip()
                        cl.direct_send(reply, [thread.users[0].pk])
                        print(f"Responded to {thread.users[0].pk} in thread {thread_id}")

                    processed_message_ids.add(message_id)

                if messages:
                    last_checked_timestamps[thread_id] = max(msg.timestamp for msg in messages)

        except Exception as e:
            print(f"Error in auto_respond: {e}")
        time.sleep(1)

def e_exit(signum, frame):
    print("\nShutting down...")
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, e_exit)
    if not login():
        exit()
    print_user_info()
    print("Starting auto-responder...")
    auto_respond()