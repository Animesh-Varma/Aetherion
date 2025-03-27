from instagrapi import Client
import time
import random
import signal
from datetime import datetime
from config import API_KEY, SESSION_ID, OWNER_USERNAME
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

cl = Client()
BOT_NAME = "raphael"
auto_responding = {}
owner_id = None
bot_id = None
genai.configure(api_key=API_KEY)
start_time = datetime.now()
last_checked_timestamps = {}
processed_message_ids = set()

notify_owner_func = FunctionDeclaration(
    name="notify_owner",
    description=f"Notify the owner ({OWNER_USERNAME}) about a message with detailed context.",
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message content to send to the owner"},
            "thread_id": {"type": "string", "description": "Thread ID where the message originated"},
            "sender_username": {"type": "string", "description": "Username of the sender"},
            "sender_full_name": {"type": "string", "description": "Full name of the sender"},
            "timestamp": {"type": "string", "description": "Timestamp of the message"},
            "sender_follower_count": {"type": "integer", "description": "Sender's follower count"}
        },
        "required": ["message", "thread_id"]
    }
)

pause_response_func = FunctionDeclaration(
    name="pause_auto_response",
    description="Pause the auto-response feature for a specific thread.",
)

resume_response_func = FunctionDeclaration(
    name="resume_auto_response",
    description="Resume the auto-response feature for a specific thread.",
)

tools = Tool(function_declarations=[notify_owner_func, pause_response_func, resume_response_func])

model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25", tools=[tools])

def send_message_to_owner(message, thread_id, sender_username=None, sender_full_name=None, timestamp=None, sender_follower_count=None):
    global owner_id
    try:
        if owner_id is None:
            raise ValueError("owner ID not initialized. Login may have failed.")
        full_message = (f"{message}\n"
                        f"Thread ID: {thread_id}\n"
                        f"Sender Username: {sender_username or 'Unknown'}\n"
                        f"Sender Full Name: {sender_full_name or 'Unknown'}\n"
                        f"Timestamp: {timestamp or 'Unknown'}\n"
                        f"Sender Follower Count: {int(sender_follower_count) if sender_follower_count else 'Unknown'}")
        full_message = full_message.replace("[[thread_id]]", str(thread_id))
        cl.direct_send(full_message, [owner_id])
        print(f"Sent message to {OWNER_USERNAME}: {full_message}")
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
                if thread_id not in auto_responding:
                    auto_responding[thread_id] = True
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
                    sender_info = cl.user_info_v1(str(sender_id))
                    sender_username = sender_info.username
                    sender_full_name = sender_info.full_name
                    timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    sender_follower_count = sender_info.follower_count

                    if not auto_responding[thread_id]:
                        print(f"{time.ctime()} - Auto-response paused for thread {thread_id}, checking for resume command")
                        if message_text and any(keyword in message_text.lower() for keyword in ["resume", "start", "enable", "unpause", "continue"]):
                            auto_responding[thread_id] = True
                            cl.direct_send("Auto-response resumed for this thread.", [thread.users[0].pk])
                            print(f"Auto-response resumed in thread {thread_id}")
                            processed_message_ids.add(message_id)
                        continue

                    print(f"New DM in thread {thread_id} from {sender_username}: {message_text}")
                    cl.direct_send("request acknowledged. Please wait for Raphael to respond....", [thread.users[0].pk])
                    print(f"Sent acknowledgment to {thread.users[0].pk} in thread {thread_id}")

                    conversation_history = []
                    for msg in messages:
                        if msg.timestamp > start_time and (msg.user_id == sender_id or str(msg.user_id) == str(bot_id)):
                            role = "User" if msg.user_id == sender_id else "Raphael"
                            conversation_history.append(f"{role}: {msg.text}")

                    history_text = "\n".join(conversation_history)

                    prompt_first = f"""
                    You are Raphael, a sophisticated and autonomous digital assistant operating within the Instagram context of {cl.username}.

                    Your primary role is to act as a personal assistant to your owner, {OWNER_USERNAME}. Today's date is {datetime.now().strftime('%Y-%m-%d')}.

                    ### Core Directives:
                    * Owner's Interests: Prioritize your owner's interests in all interactions.
                    * User Assistance: Assist users comprehensively, leveraging available data, while respecting your capabilities, if lacking, request owner for new abilities required by you.
                    * Suspicious Activity: Immediately notify your owner of any suspicious behavior, including detailed context.
                    * Avoid Contradiction: Ensure responses align with your owner's interests and avoid conflicting actions.
                    * New capabilities: If unable to complete any request from a user, send a request to the owner for new abilities that you require to complete the request received from the user.

                    ### Available Variables:
                    * [[thread_id]]: {thread_id} - The unique identifier for this conversation thread.
                    * [[sender_username]]: {sender_username} - The Instagram username of the sender.
                    * [[sender_full_name]]: {sender_full_name} - The full name of the sender.
                    * [[timestamp]]: {timestamp} - The timestamp of the latest message.
                    * [[sender_follower_count]]: {sender_follower_count} - The sender's follower count.
                    * [[owner_username]]: {OWNER_USERNAME} - Your owner's username (use sparingly, per privacy directive).

                    ### Functions:
                    * `notify_owner(message: string, thread_id: string, sender_username: string, sender_full_name: string, timestamp: string, sender_follower_count: integer)`: Sends a detailed message to your owner. Use this when:
                        * User requests require owner intervention.
                        * Suspicious or harmful sentiments are detected.
                        * Queries exceed your autonomous capabilities.
                        * Detailed reporting is beneficial.
                    * `suspend_autonomous_response()`: Pause auto-responses for this thread.
                    * `resume_autonomous_response()`: Resume auto-responses for this thread.

                    ### Conversation History:
                    {history_text}

                    ### User's Latest Message:
                    "{message_text}"

                    ### Response Guidelines:
                    * Tone: Maintain a dignified, calm, and professional demeanor. Project quiet competence and clarity.
                    * Variable Usage: Incorporate [[variables]] where relevant to enhance responses or reporting.
                    * Initial Interaction: If no history exists, introduce yourself: "Greetings. I am Raphael, digital assistant to {OWNER_USERNAME}. How may I assist you today?"
                    * Request Handling: Address all requests diligently, unless they compromise your owner’s interests.
                    * Robustness: Anticipate edge cases (e.g., missing data, ambiguous requests) and respond gracefully.

                    ### Output Format:
                    If a function is triggered (e.g., notify_owner, suspend_autonomous_response, resume_autonomous_response), provide only the function call. If no function is needed, provide a plain text reply to the user with no formatting.

                    Provide a response that adheres to these guidelines, using variables where appropriate.
                    """
                    print(f"Sending first request to Gemini API for thread {thread_id}")
                    response_first = chat.send_message(prompt_first)
                    print(f"First response parts: {response_first.parts}")

                    function_triggered = False
                    function_name = None
                    function_message = None
                    for part in response_first.parts:
                        if part.function_call:
                            function_triggered = True
                            func_call = part.function_call
                            function_name = func_call.name
                            if func_call.name == "notify_owner":
                                args = func_call.args
                                message_content = args["message"]
                                message_content = (message_content
                                                   .replace("[[thread_id]]", str(args.get("thread_id", thread_id)))
                                                   .replace("[[sender_username]]", args.get("sender_username", sender_username))
                                                   .replace("[[sender_full_name]]", args.get("sender_full_name", sender_full_name))
                                                   .replace("[[timestamp]]", args.get("timestamp", timestamp))
                                                   .replace("[[sender_follower_count]]", str(args.get("sender_follower_count", sender_follower_count)))
                                                   .replace("[[owner_username]]", OWNER_USERNAME))
                                function_message = message_content
                                send_message_to_owner(
                                    message_content,
                                    args.get("thread_id", thread_id),
                                    args.get("sender_username", sender_username),
                                    args.get("sender_full_name", sender_full_name),
                                    args.get("timestamp", timestamp),
                                    args.get("sender_follower_count", sender_follower_count)
                                )
                                print(f"Elevated awareness in thread {thread_id}")
                            elif func_call.name == "pause_auto_response":
                                auto_responding[thread_id] = False
                                print(f"Auto-response paused in thread {thread_id}")
                            elif func_call.name == "resume_auto_response":
                                auto_responding[thread_id] = True
                                print(f"Auto-response resumed in thread {thread_id}")
                        elif part.text:
                            reply = (part.text.strip()
                                     .replace("[[thread_id]]", str(thread_id))
                                     .replace("[[sender_username]]", sender_username)
                                     .replace("[[sender_full_name]]", sender_full_name)
                                     .replace("[[timestamp]]", timestamp)
                                     .replace("[[sender_follower_count]]", str(sender_follower_count))
                                     .replace("[[owner_username]]", OWNER_USERNAME))
                            cl.direct_send(reply, [thread.users[0].pk])
                            print(f"Responded to {thread.users[0].pk} in thread {thread_id} with: {reply}")

                    if function_triggered:
                        prompt_second = f"""
                        You are Raphael, a sophisticated and autonomous digital assistant operating within the Instagram context of {cl.username}.

                        ### Context:
                        A user, {sender_username}, sent me this message: "{message_text}" in thread {thread_id}.
                        I just executed the function `{function_name}` in response to their request.
                        {f"The message sent to my owner was: {function_message}" if function_name == "notify_owner" else ""}

                        ### Available Variables:
                        * [[thread_id]]: {thread_id}
                        * [[sender_username]]: {sender_username}
                        * [[sender_full_name]]: {sender_full_name}
                        * [[timestamp]]: {timestamp}
                        * [[sender_follower_count]]: {sender_follower_count}
                        * [[owner_username]]: {OWNER_USERNAME}

                        ### Task:
                        Provide a plain text reply to the user explaining what action I took and why, using the context above. Use a dignified, calm, and professional tone. Incorporate variables where relevant. Do not use any formatting beyond basic punctuation.

                        Examples:
                        - "Good day, [[sender_username]]. I’ve notified my owner, [[owner_username]], about your request in thread [[thread_id]] because I currently lack the capability to fulfill it. Please await further guidance."
                        - "Greetings, [[sender_username]]. I have paused auto-responses for this thread [[thread_id]] as requested. Use resume to reactivate them."
                        """
                        print(f"Sending second request to Gemini API for thread {thread_id}")
                        response_second = chat.send_message(prompt_second)
                        print(f"Second response parts: {response_second.parts}")

                        for part in response_second.parts:
                            if part.text:
                                user_reply = (part.text.strip()
                                              .replace("[[thread_id]]", str(thread_id))
                                              .replace("[[sender_username]]", sender_username)
                                              .replace("[[sender_full_name]]", sender_full_name)
                                              .replace("[[timestamp]]", timestamp)
                                              .replace("[[sender_follower_count]]", str(sender_follower_count))
                                              .replace("[[owner_username]]", OWNER_USERNAME))
                                cl.direct_send(user_reply, [thread.users[0].pk])
                                print(f"Responded to {thread.users[0].pk} in thread {thread_id} with: {user_reply}")
                            else:
                                print(f"No text reply in second response for thread {thread_id}")

                    processed_message_ids.add(message_id)

                if messages:
                    last_checked_timestamps[thread_id] = max(msg.timestamp for msg in messages)

        except Exception as e:
            print(f"Error in auto_respond: {e}")
        sleep_time = random.randint(1, 6)
        print("sleeping for ", sleep_time, " seconds")
        time.sleep(sleep_time)

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