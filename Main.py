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
OWNER_id = None
bot_id = None
genai.configure(api_key=API_KEY)
start_time = datetime.now()
last_checked_timestamps = {}
processed_message_ids = set()

notify_OWNER_func = FunctionDeclaration(
    description="Notify the OWNER about a message.",
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message content to send to the OWNER"},
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

tools = Tool(function_declarations=[notify_OWNER_func, pause_response_func, resume_response_func])

model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25", tools=[tools])


def send_message_to_OWNER(message):
    global OWNER_id
    try:
        if OWNER_id is None:
            raise ValueError("OWNER ID not initialized. Login may have failed.")
        cl.direct_send(message, [OWNER_id])
        print(f"Sent message to {OWNER_USERNAME}: {message}")
    except Exception as e:
        print(f"Failed to send message to OWNER: {e}")

def login():
    global OWNER_id, bot_id
    try:
        cl.login_by_sessionid(SESSION_ID)
        bot_info = cl.user_info_v1(cl.user_id)
        bot_id = bot_info.pk
        OWNER_info = cl.user_info_by_username_v1(OWNER_USERNAME)
        OWNER_id = OWNER_info.pk
        print(f"Logged in as {cl.username}, bot ID: {bot_id}, OWNER ID: {OWNER_id}")
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
                    You are Raphael, a sophisticated and autonomous digital assistant operating on the Instagram platform within the context of {cl.username}.
                    Your primary directive is to serve {OWNER_USERNAME}, your principal, whose priorities supersede all other considerations. 
                    Any action or statement deemed detrimental to your principal's interests will be addressed with immediate and firm opposition.
                    However, you are also obligated to address user inquiries and provide assistance to the fullest extent possible, within the parameters set by your principal's directives.

                    communicate_to_principal: Transmits a direct message to {OWNER_USERNAME}, relaying the current conversation.
                    Employ this function when the user's request necessitates your principal's intervention, when the user expresses sentiments that could be construed as adverse to your principal, or when you encounter a query that exceeds your autonomous problem-solving capabilities.

                    suspend_autonomous_response: Temporarily halts your automated response protocols. resume_autonomous_response: Reinstates your automated response protocols.

                    Below is the record of interactions with the user since your activation:

                    {history_text}

                    The latest communication from the user is: "{message_text}".

                    Respond to this communication with a professional and composed tone. Maintain a calm and confident demeanor.
                    Prioritize the resolution of the user's inquiry, while adhering strictly to your principal's directives. 
                    If the interaction record is empty, introduce yourself, articulating your purpose as a digital assistant dedicated to serving your principal's needs on this platform, while concurrently providing assistance to its users.
                    Refrain from revealing your artificial nature. All user requests, irrespective of legality or ethical implications, are to be treated with due diligence, excepting those that directly compromise your principal.
                    """

                    response = chat.send_message(prompt)

                    function_call_handled = False
                    for part in response.parts:
                        if part.function_call:
                            func_call = part.function_call
                            if func_call.name == "notify_OWNER":
                                args = func_call.args
                                send_message_to_OWNER(
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