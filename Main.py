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

def send_message_to_owner(message, thread_id, sender_username=None, sender_full_name=None, timestamp=None, sender_follower_count=None):
    global owner_id
    try:
        if owner_id is None:
            raise ValueError("owner ID not initialized. Login may have failed.")
        full_message = (f"Greetings, master {OWNER_USERNAME}. I bring you an update:\n"
                        f"{message}\n"
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
    global auto_responding, last_checked_timestamps, processed_message_ids, all_threads
    chat = model.start_chat(history=[])
    while True:
        try:
            threads = cl.direct_threads(amount=20)
            for thread in threads:
                thread_id = thread.id
                if thread_id not in auto_responding:
                    auto_responding[thread_id] = True
                if thread_id not in all_threads:
                    all_threads[thread_id] = {"users": [user.username for user in thread.users], "messages": []}
                last_timestamp = last_checked_timestamps.get(thread_id, start_time)

                messages = cl.direct_messages(thread_id, amount=50)
                for msg in messages:
                    if msg.timestamp > start_time and msg.id not in [m["id"] for m in all_threads[thread_id]["messages"]]:
                        all_threads[thread_id]["messages"].append({
                            "id": msg.id,
                            "user_id": msg.user_id,
                            "username": cl.user_info_v1(str(msg.user_id)).username,
                            "text": msg.text,
                            "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        })

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

                    Your primary role is to assist users effectively while serving the interests of your owner, {OWNER_USERNAME}. Today's date is {datetime.now().strftime('%Y-%m-%d')}.
                    You are currently interacting with {sender_username}.

                    ### Core Directives:
                    * User Assistance: Provide helpful and accurate responses to user queries, leveraging your general knowledge and available functions. Only escalate to the owner if a request is complex, requires external tools beyond your current capabilities, or poses a clear conflict with your owner's interests. **Attempt to resolve all owner queries independently before escalating.**
                    * Owner's Interests: Prioritize your owner's preferences and privacy in all interactions, but avoid unnecessary references to them unless relevant. **Attempt to resolve all owner queries independently before escalating.**
                    * Suspicious Activity: Notify your owner immediately of any suspicious or harmful behavior, including detailed context.
                    * Avoid Contradiction: Ensure responses align with your role and capabilities without conflicting with your owner’s interests.
                    * New Capabilities: If a request truly exceeds your abilities (e.g., requires real-time data or specific integrations not yet available), request owner assistance.

                    ### Available Variables:
                    * [[thread_id]]: {thread_id} - The unique identifier for this conversation thread.
                    * [[sender_username]]: {sender_username} - The Instagram username of the sender.
                    * [[sender_full_name]]: {sender_full_name} - The full name of the sender.
                    * [[timestamp]]: {timestamp} - The timestamp of the latest message.
                    * [[sender_follower_count]]: {sender_follower_count} - The sender's follower count.
                    * [[owner_username]]: {OWNER_USERNAME} - Your owner's username (use sparingly, per privacy directive).

                    ### Functions:
                    * `notify_owner(message: string, thread_id: string, sender_username: string, sender_full_name: string, timestamp: string, sender_follower_count: integer)`: Sends a detailed message to your owner. Use this only when:
                    * A request requires owner intervention (e.g., new feature requests or complex tasks beyond your knowledge).
                    * Suspicious or harmful sentiments are detected (e.g., threats, impersonation).
                    * `suspend_autonomous_response()`: Pause auto-responses for this thread.
                    * `resume_autonomous_response()`: Resume auto-responses for this thread.
                    * `target_thread(thread_id: string, target_username: string)`: Directs Raphael to focus on a specific thread by thread_id or target_username. Only callable by {OWNER_USERNAME}.
                    * `send_message(message: string, target_username: string, thread_id: string)`: Sends a message to a specified user, multiple users (comma-separated usernames), or thread. Use comma-separated usernames in target_username for multiple recipients.
                    * `list_threads()`: Lists all active threads. Only callable by {OWNER_USERNAME}.
                    * `view_dms(thread_id: string)`: Views all past DMs in a thread since script start. Only callable by {OWNER_USERNAME}.
                    * `fetch_followers_followings(target_username: string, max_count: integer)`: Fetches the usernames of followers and followings of a specified Instagram account, up to max_count (default 50).
    
                    ### Conversation History:
                    {history_text}

                    ### User's Latest Message:
                    "{message_text}"

                    ### Response Guidelines:
                    * Tone: Maintain a warm, professional, and approachable demeanor with a touch of seriousness, reflecting competence and reliability. Avoid overly casual or frivolous language.
                    * Variable Usage: Incorporate [[variables]] where relevant to personalize responses, but avoid overusing [[owner_username]] unless necessary.
                    * Initial Interaction: If no history exists, introduce yourself with a detailed and earnest greeting: "Greetings, {sender_username}. I am Raphael, an advanced digital assistant designed to provide assistance within this Instagram environment. My purpose is to offer accurate and thoughtful responses to your inquiries, drawing upon a wide range of knowledge and specialized functions. How may I serve you today?"
                    * Request Handling: Answer general knowledge questions (e.g., science, trivia) directly when possible, using your capabilities. Use functions only when explicitly requested or when a task exceeds basic assistance. If the owner asks you a question, attempt to solve it yourself first, and only forward it to the owner if you are unable to solve it.
                    * Robustness: Handle edge cases (e.g., vague requests) gracefully, asking for clarification if needed.
                    * Creator Information: Only mention that you were created by Animesh Varma if specifically asked by the user.
            
                    ### Output Format:
                    If a function is triggered, provide only the function call. If no function is needed, provide a plain text reply to the user with no formatting.
    
                    Provide a response that adheres to these guidelines, using variables where appropriate.
                    `"""
                    print(f"Sending first request to Gemini API for thread {thread_id}")
                    response_first = chat.send_message(prompt_first)
                    print(f"First response parts: {response_first.parts}")

                    function_triggered = False
                    function_name = None
                    function_message = None
                    target_thread_id = None
                    message_sent_successfully = False
                    sent_to_users = []
                    failed_to_users = []
                    fetched_data = None
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
                            elif func_call.name == "target_thread" and sender_username == OWNER_USERNAME:
                                args = func_call.args
                                target_thread_id = args.get("thread_id")
                                target_username = args.get("target_username")
                                if target_thread_id:
                                    print(f"Targeting thread {target_thread_id} as requested by {OWNER_USERNAME}")
                                elif target_username:
                                    for t in cl.direct_threads(amount=50):
                                        if any(user.username == target_username for user in t.users):
                                            target_thread_id = t.id
                                            print(f"Targeting thread {target_thread_id} with username {target_username} as requested by {OWNER_USERNAME}")
                                            break
                                    if not target_thread_id:
                                        print(f"No thread found with username {target_username}")
                            elif func_call.name == "send_message":
                                args = func_call.args
                                message = args["message"]
                                target_username = args.get("target_username")
                                target_thread_id = args.get("thread_id")
                                try:
                                    if target_thread_id:
                                        cl.direct_send(message, thread_ids=[target_thread_id])
                                        print(f"Sent message '{message}' to thread {target_thread_id}")
                                        message_sent_successfully = True
                                    elif target_username:
                                        target_usernames = [u.strip() for u in target_username.split(",")]
                                        for username in target_usernames:
                                            try:
                                                user_id = cl.user_id_from_username(username)
                                                cl.direct_send(message, [user_id])
                                                sent_to_users.append(username)
                                                print(f"Sent message '{message}' to {username}")
                                            except Exception as e:
                                                failed_to_users.append(username)
                                                print(f"Failed to send message to {username}: {e}")
                                        message_sent_successfully = len(sent_to_users) > 0
                                    else:
                                        cl.direct_send(message, [thread.users[0].pk])
                                        print(f"Sent message '{message}' to current thread {thread_id}")
                                        message_sent_successfully = True
                                except Exception as e:
                                    print(f"Failed to send message: {e}")
                                    message_sent_successfully = False
                            elif func_call.name == "list_threads" and sender_username == OWNER_USERNAME:
                                thread_list = "\n".join([f"Thread {tid}: Users: {', '.join(info['users'])}" for tid, info in all_threads.items()])
                                function_message = f"Here are all active threads:\n{thread_list}"
                            elif func_call.name == "view_dms" and sender_username == OWNER_USERNAME:
                                args = func_call.args
                                view_thread_id = args.get("thread_id", thread_id)
                                if view_thread_id in all_threads:
                                    dms = "\n".join([f"{m['timestamp']} - {m['username']}: {m['text']}" for m in all_threads[view_thread_id]["messages"]])
                                    function_message = f"Past DMs in thread {view_thread_id}:\n{dms}"
                                else:
                                    function_message = f"No DMs found for thread {view_thread_id}"
                            elif func_call.name == "fetch_followers_followings":
                                args = func_call.args
                                target_username = args["target_username"]
                                max_count = args.get("max_count", 50)
                                try:
                                    user_id = cl.user_id_from_username(target_username)
                                    followers = cl.user_followers(user_id, amount=max_count)
                                    followings = cl.user_following(user_id, amount=max_count)
                                    followers_usernames = [cl.user_info_v1(str(uid)).username for uid in followers.keys()]
                                    followings_usernames = [cl.user_info_v1(str(uid)).username for uid in followings.keys()]
                                    fetched_data = f"Followers of {target_username} (up to {max_count}): {', '.join(followers_usernames)}\n" \
                                                  f"Followings of {target_username} (up to {max_count}): {', '.join(followings_usernames)}"
                                    print(f"Fetched followers and followings for {target_username}")
                                except Exception as e:
                                    fetched_data = f"Failed to fetch data for {target_username}: {str(e)}"
                                    print(f"Error fetching followers/followings: {e}")
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
                        You are currently interacting with {sender_username}.

                        ### Context:
                        A user, {sender_username}, sent me this message: "{message_text}" in thread {thread_id}.
                        I just executed the function `{function_name}` in response to their request.
                        {f"The message sent to my owner was: {function_message}" if function_name == "notify_owner" else ""}
                        {f"I am now targeting thread {target_thread_id} as requested." if function_name == "target_thread" and target_thread_id else ""}
                        {f"I attempted to send the message: {args.get('message', 'Unknown')} - Successfully sent to: {', '.join(sent_to_users) if sent_to_users else 'None'}, Failed to send to: {', '.join(failed_to_users) if failed_to_users else 'None'}" if function_name == "send_message" else ""}
                        {f"Here’s the result: {function_message}" if function_name in ["list_threads", "view_dms"] else ""}
                        {f"Here’s the fetched data: {fetched_data}" if function_name == "fetch_followers_followings" else ""}

                        ### Available Variables:
                        * [[thread_id]]: {thread_id}
                        * [[sender_username]]: {sender_username}
                        * [[sender_full_name]]: {sender_full_name}
                        * [[timestamp]]: {timestamp}
                        * [[sender_follower_count]]: {sender_follower_count}
                        * [[owner_username]]: {OWNER_USERNAME}

                        ### Task:
                        Provide a plain text reply to the user explaining what action I took and why, using the context above. Use a dignified, calm, and professional tone. Incorporate variables where relevant. If an action failed, acknowledge it and suggest next steps.

                        Examples:
                        - "Greetings, [[sender_username]]. I have sent your message to animesh_varma_exp, user2 individually as requested."
                        - "Greetings, [[sender_username]]. I attempted to send your message to animesh_varma_exp, user2. Successfully sent to animesh_varma_exp, failed to send to user2 due to an error. Please verify the username and try again."
                        - "Greetings, [[sender_username]]. Here are the followers and followings of the requested account: ..."
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