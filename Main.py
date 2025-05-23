from instagrapi import Client
import time
import random
import signal
from datetime import datetime
from config import API_KEY, SESSION_ID, OWNER_USERNAME, PROMPT_FIRST_TEMPLATE, PROMPT_SECOND_TEMPLATE, BOT_NAME, THREAD_FETCH_AMOUNT, MESSAGE_FETCH_AMOUNT, MIN_SLEEP_TIME, MAX_SLEEP_TIME
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

cl = Client()
auto_responding = {}
owner_id = None
bot_id = None
genai.configure(api_key=API_KEY)
start_time = datetime.now()
last_checked_timestamps = {}
all_threads = {}
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

target_thread_func = FunctionDeclaration(
    name="target_thread",
    description=f"Directs Raphael to focus on a specific thread by thread_id or target_username. Only callable by {OWNER_USERNAME}.",
    parameters={
        "type": "object",
        "properties": {
            "thread_id": {"type": "string", "description": "The thread ID to target (optional if target_username is provided)"},
            "target_username": {"type": "string", "description": "The username in the thread to target (optional if thread_id is provided)"}
        }
    }
)

send_message_func = FunctionDeclaration(
    name="send_message",
    description="Sends a message to a specified user, multiple users (comma-separated usernames), or thread. Use comma-separated usernames in target_username for multiple recipients.",
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "The message to send"},
            "target_username": {"type": "string", "description": "The username(s) to send the message to (optional if thread_id is provided)"},
            "thread_id": {"type": "string", "description": "The thread ID to send the message to (optional if target_username is provided)"}
        },
        "required": ["message"]
    }
)

list_threads_func = FunctionDeclaration(
    name="list_threads",
    description=f"Lists all active threads. Only callable by {OWNER_USERNAME}."
)

view_dms_func = FunctionDeclaration(
    name="view_dms",
    description=f"Views all past DMs in a thread since script start. Only callable by {OWNER_USERNAME}.",
    parameters={
        "type": "object",
        "properties": {
            "thread_id": {"type": "string", "description": "The thread ID to view DMs for (optional; if omitted, shows all threads)"}
        }
    }
)

fetch_followers_followings_func = FunctionDeclaration(
    name="fetch_followers_followings",
    description="Fetches the usernames of followers and followings of a specified Instagram account.",
    parameters={
        "type": "object",
        "properties": {
            "target_username": {"type": "string", "description": "The Instagram username to fetch followers and followings for"},
            "max_count": {"type": "integer", "description": "Maximum number of followers/followings to fetch (optional, defaults to 50 if not specified)"}
        },
        "required": ["target_username"]
    }
)

tools = Tool(function_declarations=[
    notify_owner_func,
    pause_response_func,
    resume_response_func,
    target_thread_func,
    send_message_func,
    list_threads_func,
    view_dms_func,
    fetch_followers_followings_func
])

model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25", tools=[tools])

def format_message(template_string: str, **kwargs) -> str:
    """
    Replaces placeholders in a template string with values from kwargs.
    Placeholders are in the format [[placeholder_name]].
    """
    for key, value in kwargs.items():
        template_string = template_string.replace(f"[[{key}]]", str(value))
    return template_string

def send_message_to_owner(message, thread_id, sender_username=None, sender_full_name=None, timestamp=None, sender_follower_count=None):
    """Sends a formatted message to the bot owner."""
    global owner_id
    try:
        if owner_id is None:
            raise ValueError("owner ID not initialized. Login may have failed.")
        
        base_message = (f"Greetings, master {OWNER_USERNAME}. I bring you an update:\n"
                        f"{message}\n"
                        f"Thread ID: [[thread_id]]\n"
                        f"Sender Username: [[sender_username]]\n"
                        f"Sender Full Name: [[sender_full_name]]\n"
                        f"Timestamp: [[timestamp]]\n"
                        f"Sender Follower Count: [[sender_follower_count]]")

        full_message = format_message(
            base_message,
            thread_id=thread_id,
            sender_username=sender_username or 'Unknown',
            sender_full_name=sender_full_name or 'Unknown',
            timestamp=timestamp or 'Unknown',
            sender_follower_count=int(sender_follower_count) if sender_follower_count else 'Unknown'
        )
        cl.direct_send(full_message, [owner_id])
        print(f"Sent message to {OWNER_USERNAME}: {full_message}")
    except Exception as e:
        print(f"Failed to send message to owner: {e}")

def login():
    """Logs into Instagram using the session ID and fetches bot and owner IDs."""
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
    """Prints the logged-in user's profile information."""
    try:
        user_info = cl.user_info_v1(cl.user_id)
        print(f"Username: {user_info.username}")
        print(f"Full Name: {user_info.full_name}")
        print(f"Biography: {user_info.biography}")
        print(f"Followers: {user_info.follower_count}")
    except Exception as e:
        print(f"Failed to retrieve user info: {e}")

def auto_respond():
    """
    Main loop for automatically responding to Instagram direct messages.
    Fetches new messages, processes them using a generative AI model,
    and handles function calls triggered by the model.
    """
    global auto_responding, last_checked_timestamps, processed_message_ids, all_threads
    chat = model.start_chat(history=[])
    while True:
        try:
            # Fetch recent threads
            threads = cl.direct_threads(amount=THREAD_FETCH_AMOUNT)
            for thread in threads:
                thread_id = thread.id
                # Initialize auto-response state for new threads
                if thread_id not in auto_responding:
                    auto_responding[thread_id] = True
                # Initialize thread information storage
                if thread_id not in all_threads:
                    all_threads[thread_id] = {"users": [user.username for user in thread.users], "messages": []}
                last_timestamp = last_checked_timestamps.get(thread_id, start_time)

                # Fetch messages in the current thread
                messages = cl.direct_messages(thread_id, amount=MESSAGE_FETCH_AMOUNT)
                # Store new messages in all_threads for history
                for msg in messages:
                    if msg.timestamp > start_time and msg.id not in [m["id"] for m in all_threads[thread_id]["messages"]]:
                        try:
                            msg_sender_username = cl.user_info_v1(str(msg.user_id)).username
                        except Exception as e:
                            print(f"Error fetching username for message {msg.id} in thread {thread_id}: {e}")
                            msg_sender_username = "UnknownUser"
                        all_threads[thread_id]["messages"].append({
                            "id": msg.id,
                            "user_id": msg.user_id,
                            "username": msg_sender_username,
                            "text": msg.text,
                            "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        })

                # Filter for messages newer than the last checked timestamp
                new_messages = [msg for msg in messages if msg.timestamp > last_timestamp]
                if not new_messages:
                    print(f"No new messages in thread {thread_id}")
                    continue

                for message in new_messages:
                    message_id = message.id
                    # processed_message_ids: A set to keep track of message IDs that have already been processed to avoid duplication.
                    if message_id in processed_message_ids:
                        print(f"Skipping already processed message {message_id} in thread {thread_id}")
                        continue

                    # Ignore bot's own messages to prevent self-reply loops.
                    if str(message.user_id) == str(bot_id):
                        print(f"Ignoring bot's own message {message_id} in thread {thread_id}: {message.text}")
                        continue

                    message_text = message.text
                    sender_id = message.user_id
                    try:
                        sender_info = cl.user_info_v1(str(sender_id))
                        sender_username = sender_info.username
                        sender_full_name = sender_info.full_name
                        sender_follower_count = sender_info.follower_count
                    except Exception as e:
                        print(f"Error fetching sender info for user ID {sender_id} in thread {thread_id}: {e}")
                        # Fallback values if sender info cannot be fetched
                        sender_username = "UnknownUser"
                        sender_full_name = "Unknown User"
                        sender_follower_count = 0 # Default follower count
                        # Optionally, skip this message if sender info is critical
                        # print(f"Skipping message {message_id} due to sender info fetch failure.")
                        # continue 
                    timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")

                    # If auto-response is paused for this thread, check if the message is a command to resume.
                    if not auto_responding[thread_id]:
                        print(f"{time.ctime()} - Auto-response paused for thread {thread_id}, checking for resume command")
                        if message_text and any(keyword in message_text.lower() for keyword in ["resume", "start", "enable", "unpause", "continue"]):
                            auto_responding[thread_id] = True
                            cl.direct_send("Auto-response resumed for this thread.", [thread.users[0].pk])
                            print(f"Auto-response resumed in thread {thread_id}")
                            processed_message_ids.add(message_id)
                        continue
                    
                    # Send an initial acknowledgment to the user.
                    print(f"New DM in thread {thread_id} from {sender_username}: {message_text}")
                    cl.direct_send("request acknowledged. Please wait for Raphael to respond....", [thread.users[0].pk])
                    print(f"Sent acknowledgment to {thread.users[0].pk} in thread {thread_id}")

                    # Construct conversation history for the prompt, including past messages from the user and the bot.
                    conversation_history = []
                    for msg in messages:
                        if msg.timestamp > start_time and (msg.user_id == sender_id or str(msg.user_id) == str(bot_id)):
                            role = "User" if msg.user_id == sender_id else "Raphael"
                            conversation_history.append(f"{role}: {msg.text}")

                    history_text = "\n".join(conversation_history)

                    prompt_first = PROMPT_FIRST_TEMPLATE.format(
                        bot_username_in_context=cl.username,
                        owner_username=OWNER_USERNAME,
                        current_date=datetime.now().strftime('%Y-%m-%d'),
                        sender_username=sender_username,
                        thread_id=thread_id,
                        sender_full_name=sender_full_name,
                        timestamp=timestamp,
                        sender_follower_count=sender_follower_count,
                        history_text=history_text,
                        message_text=message_text
                    )
                    try:
                        print(f"Sending first request to Gemini API for thread {thread_id}")
                        response_first = chat.send_message(prompt_first)
                        print(f"First response parts: {response_first.parts}")
                    except Exception as e:
                        print(f"Error sending first request to Gemini API for thread {thread_id}, message {message_id}: {e}")
                        processed_message_ids.add(message_id) # Mark as processed to avoid retrying indefinitely
                        continue # Skip to the next message

                    function_triggered = False
                    function_name = None
                    function_message = None
                    target_thread_id = None
                    message_sent_successfully = False
                    sent_to_users = []
                    failed_to_users = []
                    fetched_data = None
                    args_for_prompt = {} # Define args_for_prompt to ensure it's available

                    for part in response_first.parts:
                        if part.function_call:
                            function_triggered = True
                            func_call = part.function_call
                            function_name = func_call.name
                            args_for_prompt = func_call.args # Store args for later use in prompt_second
                            # Handle 'notify_owner' function call: Send a message to the bot owner.
                            if func_call.name == "notify_owner":
                                args = func_call.args
                                message_content = args["message"]
                                # Replace placeholders in the message content before sending
                                formatted_message_content = format_message(
                                    message_content,
                                    thread_id=str(args.get("thread_id", thread_id)),
                                    sender_username=args.get("sender_username", sender_username),
                                    sender_full_name=args.get("sender_full_name", sender_full_name),
                                    timestamp=args.get("timestamp", timestamp),
                                    sender_follower_count=str(args.get("sender_follower_count", sender_follower_count)),
                                    owner_username=OWNER_USERNAME
                                )
                                function_message = formatted_message_content # For the second prompt
                                send_message_to_owner(
                                    formatted_message_content,
                                    args.get("thread_id", thread_id),
                                    args.get("sender_username", sender_username),
                                    args.get("sender_full_name", sender_full_name),
                                    args.get("timestamp", timestamp),
                                    args.get("sender_follower_count", sender_follower_count)
                                )
                                print(f"Elevated awareness in thread {thread_id}")
                            # Handle 'pause_auto_response' function call: Pause auto-responses for the current thread.
                            elif func_call.name == "pause_auto_response":
                                auto_responding[thread_id] = False
                                print(f"Auto-response paused in thread {thread_id}")
                            # Handle 'resume_auto_response' function call: Resume auto-responses for the current thread.
                            elif func_call.name == "resume_auto_response":
                                auto_responding[thread_id] = True
                                print(f"Auto-response resumed in thread {thread_id}")
                            # Handle 'target_thread' function call: Change focus to a different thread (owner only).
                            elif func_call.name == "target_thread" and sender_username == OWNER_USERNAME:
                                args = func_call.args
                                target_thread_id = args.get("thread_id")
                                target_username = args.get("target_username")
                                if target_thread_id:
                                    print(f"Targeting thread {target_thread_id} as requested by {OWNER_USERNAME}")
                                elif target_username:
                                    for t in cl.direct_threads(amount=MESSAGE_FETCH_AMOUNT): # Use configured amount
                                        if any(user.username == target_username for user in t.users):
                                            target_thread_id = t.id
                                            print(f"Targeting thread {target_thread_id} with username {target_username} as requested by {OWNER_USERNAME}")
                                            break
                                    if not target_thread_id:
                                        print(f"No thread found with username {target_username}")
                            # Handle 'send_message' function call: Send a message to a specified user or thread.
                            elif func_call.name == "send_message":
                                args = func_call.args
                                message_to_send = args["message"] # Renamed to avoid conflict
                                target_username = args.get("target_username")
                                target_thread_id_func_arg = args.get("thread_id")
                                try:
                                    if target_thread_id_func_arg:
                                        cl.direct_send(message_to_send, thread_ids=[target_thread_id_func_arg])
                                        print(f"Sent message '{message_to_send}' to thread {target_thread_id_func_arg}")
                                        message_sent_successfully = True
                                    elif target_username:
                                        target_usernames = [u.strip() for u in target_username.split(",")]
                                        for username_to_send in target_usernames:
                                            try:
                                                user_id = cl.user_id_from_username(username_to_send)
                                            except Exception as e:
                                                print(f"Failed to get user ID for username {username_to_send}: {e}")
                                                failed_to_users.append(username_to_send)
                                                continue # Skip this username
                                            try:
                                                cl.direct_send(message_to_send, [user_id])
                                                sent_to_users.append(username_to_send)
                                                print(f"Sent message '{message_to_send}' to {username_to_send}")
                                            except Exception as e:
                                                failed_to_users.append(username_to_send)
                                                print(f"Failed to send message to {username_to_send} (ID: {user_id}): {e}")
                                        message_sent_successfully = len(sent_to_users) > 0
                                    else:
                                        cl.direct_send(message_to_send, [thread.users[0].pk])
                                        print(f"Sent message '{message_to_send}' to current thread {thread_id}")
                                        message_sent_successfully = True
                                except Exception as e:
                                    print(f"Failed to send message: {e}")
                                    message_sent_successfully = False
                            # Handle 'list_threads' function call: List all active threads (owner only).
                            elif func_call.name == "list_threads" and sender_username == OWNER_USERNAME:
                                thread_list = "\n".join([f"Thread {tid}: Users: {', '.join(info['users'])}" for tid, info in all_threads.items()])
                                function_message = f"Here are all active threads:\n{thread_list}"
                            # Handle 'view_dms' function call: View DMs in a specific thread (owner only).
                            elif func_call.name == "view_dms" and sender_username == OWNER_USERNAME:
                                args = func_call.args
                                view_thread_id = args.get("thread_id", thread_id)
                                if view_thread_id in all_threads:
                                    dms = "\n".join([f"{m['timestamp']} - {m['username']}: {m['text']}" for m in all_threads[view_thread_id]["messages"]])
                                    function_message = f"Past DMs in thread {view_thread_id}:\n{dms}"
                                else:
                                    function_message = f"No DMs found for thread {view_thread_id}"
                            # Handle 'fetch_followers_followings' function call: Get follower/following lists.
                            elif func_call.name == "fetch_followers_followings":
                                args = func_call.args
                                target_username_fetch = args["target_username"] 
                                max_count = args.get("max_count", 50) # Default to 50 if not specified
                                try:
                                    user_id = cl.user_id_from_username(target_username_fetch)
                                    followers = cl.user_followers(user_id, amount=max_count)
                                    followings = cl.user_following(user_id, amount=max_count)
                                    followers_usernames = [cl.user_info_v1(str(uid)).username for uid in followers.keys()]
                                    followings_usernames = [cl.user_info_v1(str(uid)).username for uid in followings.keys()]
                                    fetched_data = f"Followers of {target_username_fetch} (up to {max_count}): {', '.join(followers_usernames)}\n" \
                                                  f"Followings of {target_username_fetch} (up to {max_count}): {', '.join(followings_usernames)}"
                                    print(f"Fetched followers and followings for {target_username_fetch}")
                                except Exception as e:
                                    fetched_data = f"Failed to fetch data for {target_username_fetch}: {str(e)}"
                                    print(f"Error fetching followers/followings: {e}")
                        elif part.text:
                            # If no function call, send the model's text response directly to the user.
                            reply = format_message(
                                part.text.strip(),
                                thread_id=str(thread_id),
                                sender_username=sender_username,
                                sender_full_name=sender_full_name,
                                timestamp=timestamp,
                                sender_follower_count=str(sender_follower_count),
                                owner_username=OWNER_USERNAME
                            )
                            cl.direct_send(reply, [thread.users[0].pk])
                            print(f"Responded to {thread.users[0].pk} in thread {thread_id} with: {reply}")

                    # If a function was triggered, send a second request to the API to explain the action to the user.
                    if function_triggered:
                        function_message_placeholder = ""
                        if function_name == "notify_owner":
                            function_message_placeholder = f"The message sent to my owner was: {function_message}"

                        target_thread_placeholder = ""
                        if function_name == "target_thread" and target_thread_id:
                            target_thread_placeholder = f"I am now targeting thread {target_thread_id} as requested."

                        send_message_placeholder = ""
                        if function_name == "send_message":
                            sent_msg_content = args_for_prompt.get('message', 'Unknown')
                            sent_to_str = ', '.join(sent_to_users) if sent_to_users else 'None'
                            failed_to_str = ', '.join(failed_to_users) if failed_to_users else 'None'
                            send_message_placeholder = f"I attempted to send the message: {sent_msg_content} - Successfully sent to: {sent_to_str}, Failed to send to: {failed_to_str}"

                        list_or_view_dms_placeholder = ""
                        if function_name in ["list_threads", "view_dms"]:
                            list_or_view_dms_placeholder = f"Here’s the result: {function_message}"
                        
                        fetched_data_placeholder = ""
                        if function_name == "fetch_followers_followings":
                            fetched_data_placeholder = f"Here’s the fetched data: {fetched_data}"

                        prompt_second = PROMPT_SECOND_TEMPLATE.format(
                            bot_username_in_context=cl.username,
                            sender_username=sender_username,
                            message_text=message_text,
                            thread_id=thread_id,
                            function_name=function_name,
                            function_message_placeholder=function_message_placeholder,
                            target_thread_placeholder=target_thread_placeholder,
                            send_message_placeholder=send_message_placeholder,
                            list_or_view_dms_placeholder=list_or_view_dms_placeholder,
                            fetched_data_placeholder=fetched_data_placeholder,
                            sender_full_name=sender_full_name, # Added missing placeholder
                            timestamp=timestamp,
                            sender_follower_count=sender_follower_count,
                            owner_username=OWNER_USERNAME
                        )
                        try:
                            print(f"Sending second request to Gemini API for thread {thread_id}")
                            response_second = chat.send_message(prompt_second)
                            print(f"Second response parts: {response_second.parts}")

                            for part in response_second.parts:
                                if part.text:
                                    user_reply = format_message(
                                        part.text.strip(),
                                        thread_id=str(thread_id),
                                        sender_username=sender_username,
                                        sender_full_name=sender_full_name,
                                        timestamp=timestamp,
                                        sender_follower_count=str(sender_follower_count),
                                        owner_username=OWNER_USERNAME
                                    )
                                    cl.direct_send(user_reply, [thread.users[0].pk])
                                    print(f"Responded to {thread.users[0].pk} in thread {thread_id} with: {user_reply}")
                                else:
                                    print(f"No text reply in second response for thread {thread_id}")
                        except Exception as e:
                            print(f"Error sending second request to Gemini API or processing its response for thread {thread_id}, message {message_id}: {e}")
                            # message_id is already added to processed_message_ids before the first API call, 
                            # or will be added after this block if the first call succeeded.
                            # No need to send a message to user here as the interaction is already complex.
                    
                    # Mark the message as processed (if not already marked due to API error)
                    processed_message_ids.add(message_id)

                # Update the last checked timestamp for the thread
                if messages:
                    last_checked_timestamps[thread_id] = max(msg.timestamp for msg in messages)

        except Exception as e:
            print(f"Error in auto_respond: {e}")
        # Random sleep to mimic human behavior and avoid rate limiting
        sleep_time = random.randint(MIN_SLEEP_TIME, MAX_SLEEP_TIME)
        print("sleeping for ", sleep_time, " seconds")
        time.sleep(sleep_time)

def e_exit(signum, frame):
    """Handles graceful shutdown on SIGINT (Ctrl+C)."""
    print("\nShutting down...")
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, e_exit)
    if not login():
        exit()
    print_user_info()
    print("Starting auto-responder...")
    auto_respond()