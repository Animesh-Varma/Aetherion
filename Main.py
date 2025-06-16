import uiautomator2 as u2
import time
import random
import signal
from datetime import datetime, timedelta

from config import (API_KEY, OWNER_USERNAME, PROMPT_FIRST_TEMPLATE, PROMPT_SECOND_TEMPLATE,
                    bot_instagram_username, BOT_DISPLAY_NAME, MESSAGE_FETCH_AMOUNT,
                    MIN_SLEEP_TIME, MAX_SLEEP_TIME, BLUE_DOT_CHECK_INTERVAL, DEVICE_IDENTIFIER,
                    THREAD_PAUSE_KEYWORD, THREAD_RESUME_KEYWORD,
                    OWNER_REMOTE_PAUSE_KEYWORD, OWNER_REMOTE_RESUME_KEYWORD
                    )
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

import uiautomator2_utils as u2_utils

# --- uiautomator2 Device Connection ---
# USER: Configure your device connection here (e.g., IP:PORT for Wi-Fi, or device serial number for USB if single device)
d_device_identifier = DEVICE_IDENTIFIER
d_device = None  # Will be initialized in __main__

# --- Global Variables ---
BOT_ACTUAL_USERNAME = bot_instagram_username  # Initial assumption, verified/updated in login_ui()
auto_responding = {}  # Key: thread_identifier (peer_username/group_name), Value: bool (true if auto-responding)
bot_profile_info_global = None
genai.configure(api_key=API_KEY)
start_time = datetime.now()  # Used for initial timestamp if a thread has no prior check time
last_checked_timestamps = {}  # Key: thread_identifier, Value: datetime object (timestamp of last processed message in that thread)
all_threads_history = {}  # Key: thread_identifier, Value: {"users": [usernames], "messages": []} (stores message history)
processed_message_ids = set()  # Set of unique message IDs (hashes) that have been processed by the LLM in the current session
bot_sent_message_hashes = set()
paused_by_owner_threads = set()

# --- Gemini Function Declarations ---
# These define functions the LLM can request the bot to execute via UI automation.

# Sends a msg to the owner
notify_owner_func = FunctionDeclaration(
    name="notify_owner",
    description=f"Notify the owner ({OWNER_USERNAME}) about a message with detailed context.",
    parameters={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message content to send to the owner"},
            "thread_id": {"type": "string",
                          "description": "Thread identifier (e.g., sender's username) where the message originated"},
            "sender_username": {"type": "string", "description": "Username of the sender"},
            "sender_full_name": {"type": "string", "description": "Full name of the sender (if available)"},
            "timestamp": {"type": "string", "description": "Approximate timestamp of the message"},
            "sender_follower_count": {"type": "integer", "description": "Sender's follower count (if available)"}
        },
        "required": ["message", "thread_id"]
    }
)

view_dms_func = FunctionDeclaration(
    name="view_dms",
    description=f"Fetches the locally stored direct message (DM) history for a specified thread. This function can only be called by the owner ({OWNER_USERNAME}). It does not mark messages as read or interact with the live Instagram UI for fetching.",
    parameters={
        "type": "object",
        "properties": {
            "thread_id": {
                "type": "string",
                "description": "The Instagram username or group name of the thread whose DMs are to be viewed."
            }
        },
        "required": ["thread_id"]
    }
)

owner_control_thread_func = FunctionDeclaration(
    name="owner_control_thread_autoresponse",
    description="Allows the owner to pause or resume auto-responses for a specific target user's thread. This function can only be invoked if the request comes from the configured OWNER_USERNAME.",
    parameters={
        "type": "object",
        "properties": {
            "target_username": {
                "type": "string",
                "description": "The Instagram username of the user whose thread auto-response is to be controlled."
            },
            "action": {
                "type": "string",
                "description": "The action to perform: 'pause' to temporarily halt auto-responses, or 'resume' to re-enable them.",
                "enum": ["pause", "resume"]
            }
        },
        "required": ["target_username", "action"]
    }
)

# Sends a msg to the specified user
send_message_func = FunctionDeclaration(
    name="send_message",
    description="Sends a message to a specified user or existing thread via UI.",
    parameters={
        "type": "object", "properties": {
            "message": {"type": "string", "description": "The message to send"},
            "target_username": {"type": "string",
                                "description": "The username to send the message to (will find or start DM)."},
            "thread_id": {"type": "string",
                          "description": "The existing thread identifier (peer username/group name) to send to (optional)."}
        }, "required": ["message"]
    }
)

# Fetches follower and following for any specified user (Currently un tested for uiautomator2_imp)
fetch_followers_followings = FunctionDeclaration(
    name="fetch_followers_followings",
    description=f"Fetches followers/followings for a user. UI-Intensive: SLOW and LIMITED results. Only callable by {OWNER_USERNAME}.",
    parameters={
        "type": "object", "properties": {
            "target_username": {"type": "string", "description": "The Instagram username to fetch for."},
            "max_count": {"type": "integer", "description": "Approx max to fetch (UI limited, e.g., 10-20)."}
        }, "required": ["target_username"]
    }
)

trigger_thread_pause_func = FunctionDeclaration(
    name="trigger_thread_pause",
    description="Pauses bot responses specifically for the current conversation thread. The bot will stop sending messages in this thread until a resume keyword is received from the user in this thread. Use this if the conversation context suggests the user in this thread wants a temporary halt or if the bot needs to stop responding in this specific thread for some reason.",
    parameters={
        "type": "object",
        "properties": {
            "reason": {"type": "string",
                       "description": "Optional reason for pausing, which can be relayed to the user in this thread."}
            # thread_id could be an implicit parameter based on current context, or explicitly passed if needed.
            # For now, assume it operates on the current thread_identifier.
        }
    }
)

PRE_CALL_TEMPLATES = {
    "notify_owner": "Greetings, {sender_username}. I am taking a moment to notify my owner, {owner_username}. I'll let you know once this is completed.",
    "send_message": "Greetings, {sender_username}. I'm preparing to send your message '{message_preview}' to '{target_username_or_thread_id}'. I'll confirm once sent.",
    "fetch_followers_followings": "Greetings, {sender_username}. I'm about to start fetching follower/following information for '{target_username}'. This might take a moment. I'll let you know when I have the results.",
    "trigger_thread_pause": "Understood, {sender_username}. I am now pausing my responses in this specific chat. I'll let you know once this is active.",
    "owner_control_thread_autoresponse": "Understood, Master {owner_username}. I will now attempt to {action} auto-responses for user '{target_username}'. I'll confirm once this is done."
}

OWNER_REMOTE_PAUSE_SUCCESS_CONFIRMATION = "{BOT_DISPLAY_NAME}: Successfully PAUSED auto-responses for thread '{TARGET_USERNAME}'."
OWNER_REMOTE_RESUME_SUCCESS_CONFIRMATION = "{BOT_DISPLAY_NAME}: Successfully RESUMED auto-responses for thread '{TARGET_USERNAME}'."
OWNER_REMOTE_TARGET_NOT_FOUND_ERROR = "{BOT_DISPLAY_NAME}: Error: Could not find an active thread or user '{TARGET_USERNAME}'."
TARGET_THREAD_PAUSED_BY_OWNER_NOTIFICATION = "{BOT_DISPLAY_NAME}: Auto-responses for this chat have been paused by the owner and can only be resumed by them."
TARGET_THREAD_RESUMED_BY_OWNER_NOTIFICATION = "{BOT_DISPLAY_NAME}: Auto-responses for this chat have been resumed by the owner."
THREAD_PAUSE_CONFIRMATION_MESSAGE = "{BOT_DISPLAY_NAME}: Auto-responses have been PAUSED for this chat. Send '{THREAD_RESUME_KEYWORD}' to resume."
THREAD_RESUME_CONFIRMATION_MESSAGE = "{BOT_DISPLAY_NAME}: Auto-responses have been RESUMED for this chat."
USER_CANNOT_RESUME_OWNER_PAUSE_MESSAGE = "{BOT_DISPLAY_NAME}: Auto-responses for this chat were paused by the owner and can only be resumed by them."

tools = Tool(function_declarations=[
    notify_owner_func,
    send_message_func,
    fetch_followers_followings,
    trigger_thread_pause_func,
    owner_control_thread_func,
    view_dms_func
])
model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20", tools=tools)


def format_message_for_llm(template_string: str, **kwargs) -> str:
    for key, value in kwargs.items():
        template_string = template_string.replace(f"[[{key}]]", str(value))
    return template_string


def send_message_to_owner_via_ui(message_body, original_context):
    global d_device, BOT_ACTUAL_USERNAME
    if not OWNER_USERNAME:
        print("ERROR: OWNER_USERNAME not configured.")
        return

    timestamp_str = original_context.get('timestamp', 'N/A')
    formatted_timestamp = ""

    if timestamp_str and timestamp_str != "N/A":
        try:
            dt_object = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            formatted_timestamp = dt_object.strftime('\nDate: %B %d, %Y\nTime: %Hh %Mm %Ss')
        except ValueError:
            formatted_timestamp = f"Timestamp (raw): [{timestamp_str}]"
    else:
        formatted_timestamp = "Timestamp: [Not Available]"

    full_message_to_owner = (f"{BOT_DISPLAY_NAME} ({BOT_ACTUAL_USERNAME}) Update for Master {OWNER_USERNAME}:\n"
                             f"{message_body}\n---Original Context---\n"
                             f"Sender: {original_context.get('sender_username', 'N/A')}\n"
                             f"---Notification Timestamp---{formatted_timestamp}\n")

    print(f"Attempting to send to owner ({OWNER_USERNAME}) via UI: {full_message_to_owner[:100]}...")
    if u2_utils.search_and_open_dm_with_user(d_device, OWNER_USERNAME, BOT_ACTUAL_USERNAME):
        if u2_utils.send_dm_in_open_thread(d_device, full_message_to_owner):
            bot_sent_message_hashes.add(hash(full_message_to_owner.strip()))  # Verified
            print(f"Message sent to owner {OWNER_USERNAME} via UI.")
        else:
            print(f"Failed to type/send DM content to owner {OWNER_USERNAME}.")
    else:
        print(f"Failed to open/start DM thread with owner {OWNER_USERNAME}.")
    u2_utils.go_to_dm_list(d_device)


def login_ui():
    global d_device, BOT_ACTUAL_USERNAME, bot_profile_info_global
    print("Attempting UI Login/Setup...")
    u2_utils.ensure_instagram_open(d_device)
    time.sleep(3)  # Give app time to settle

    # Get bot's actual username from its profile page
    profile_info = u2_utils.get_bot_profile_info(d_device,
                                                 bot_instagram_username)  # bot_instagram_username from config is an initial guess
    bot_profile_info_global = profile_info
    if profile_info.get("username"):
        BOT_ACTUAL_USERNAME = profile_info["username"]
        if BOT_ACTUAL_USERNAME.lower() != bot_instagram_username.lower():
            print(
                f"WARNING: Actual bot username '{BOT_ACTUAL_USERNAME}' differs from bot_instagram_username config '{bot_instagram_username}'. Using actual.")
    else:
        print(
            f"WARNING: Could not verify bot username from profile. Using bot_instagram_username from config: '{bot_instagram_username}'. Ensure this is correct.")
        BOT_ACTUAL_USERNAME = bot_instagram_username

    if not OWNER_USERNAME:
        print("CRITICAL ERROR: OWNER_USERNAME is not configured in config.py. Bot cannot function correctly.")
        return False

    print(f"UI 'Login' complete. Bot Username: {BOT_ACTUAL_USERNAME}, Owner: {OWNER_USERNAME}")
    u2_utils.go_to_dm_list(d_device)  # End in DM list
    return True


def print_bot_user_info_ui():
    global d_device, BOT_ACTUAL_USERNAME, bot_profile_info_global
    print(f"\n--- Bot ({BOT_ACTUAL_USERNAME}) Profile Info (UI Scraped) ---")
    print(
        f"  Username: {bot_profile_info_global.get('username', BOT_ACTUAL_USERNAME) if bot_profile_info_global else BOT_ACTUAL_USERNAME}")
    print(f"  Full Name: {bot_profile_info_global.get('full_name', 'N/A') if bot_profile_info_global else 'N/A'}")
    print(f"  Biography: {bot_profile_info_global.get('biography', 'N/A') if bot_profile_info_global else 'N/A'}")
    print(f"  Followers: {bot_profile_info_global.get('follower_count', 'N/A') if bot_profile_info_global else 'N/A'}")
    u2_utils.go_to_dm_list(d_device)  # Return to DMs


def view_dms(thread_id: str, calling_username: str) -> str:
    '''
    Allows the owner to view the locally stored message history for a given thread.

    Args:
        thread_id: The username or group name of the thread to view.
        calling_username: The username of the user calling this function.

    Returns:
        A string containing the formatted DMs or an error/info message.
    '''
    global all_threads_history, OWNER_USERNAME

    if calling_username.lower() != OWNER_USERNAME.lower():
        return "Error: You are not authorized to use this function."

    thread_history = all_threads_history.get(thread_id.lower())  # Use .lower() for case-insensitive matching

    if not thread_history or not thread_history.get("messages"):
        return f"No local message history found for thread: {thread_id}"

    formatted_messages = [f"--- DMs for thread: {thread_id} ---"]
    for msg in thread_history["messages"]:
        sender = msg.get("username", "Unknown User")
        text = msg.get("text", "")
        timestamp = msg.get("timestamp", "No timestamp")
        formatted_messages.append(f"[{timestamp}] {sender}: {text}")

    if len(formatted_messages) == 1:  # Only header was added
        return f"No messages found in the local history for thread: {thread_id}"

    return "\n".join(formatted_messages)


def _perform_back_press(d_device_internal, LLM_HISTORY_LENGTH=10):
    """
    Performs back presses to ensure UI stability, typically to close keyboard/editor
    and return to DM list from an open chat.
    """
    print("Performing back press(es) to return to DM list...")
    d_device_internal.press("back")
    time.sleep(0.5)
    # A second back press might be needed if the first only closed a software keyboard
    if not d_device_internal(resourceId=u2_utils.DM_LIST_HEADER_TEXT_RESID).wait(timeout=1):
        print("First back press didn't return to DM list, pressing back again.")
        d_device_internal.press("back")
        time.sleep(0.5)


def auto_respond_via_ui():
    global d_device, auto_responding, last_checked_timestamps, processed_message_ids, all_threads_history, BOT_ACTUAL_USERNAME
    LLM_HISTORY_LENGTH = 10  # Number of past messages to include in LLM prompt history
    MAX_ATTEMPTS = 3  # Max attempts for LLM calls
    SEND_EXPLANATION_ATTEMPTS = 3  # Max attempts for sending the explanation message

    print("Ensuring Instagram is open at the start of the bot cycle...")
    u2_utils.ensure_instagram_open(d_device)
    print("Instagram check/start attempt complete.")

    if not BOT_ACTUAL_USERNAME:
        print("CRITICAL: Bot username not determined. Cannot start auto-responder. Run login_ui first.")
        return

    chat_session = model.start_chat(history=[])

    while True:
        sleep_after_cycle = True  # Flag to determine if long sleep is needed (e.g. after errors)
        try:
            print(f"\n--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} --- UI Bot Cycle ---")

            if not u2_utils.go_to_dm_list(d_device):
                print("ERROR: Failed to navigate to DM list at the start of the cycle. Retrying after sleep.")
                continue

            unread_threads = u2_utils.check_for_unread_dm_threads(d_device)

            if unread_threads:
                print(f"Found {len(unread_threads)} unread thread(s) by blue dot: {unread_threads}")
                active_thread_identifier = None  # Tracks the currently open thread

                for thread_identifier in unread_threads:
                    # --- BEGIN NEW CODE ---
                    if thread_identifier.lower() in paused_by_owner_threads:
                        print(
                            f"Thread '{thread_identifier}' is currently paused by the owner. Skipping its processing from unread list for this cycle.")
                        # Update timestamp to prevent immediate reprocessing if blue dot persists due to already checked messages
                        last_checked_timestamps[thread_identifier] = datetime.now()
                        # Also, ensure any new messages that might have been fetched IF we didn't skip
                        # are notionally marked. Since we are skipping message fetching entirely for this thread,
                        # this primarily serves to prevent a loop if the blue dot doesn't clear without opening.
                        # This might be an over-cautious measure if the blue dot clears on its own.
                        # For now, just updating last_checked_timestamps should be the main effect.
                        continue  # Move to the next thread_identifier in unread_threads
                    # --- END NEW CODE ---

                    critical_context_switch_error = False
                    if thread_identifier.lower() == BOT_ACTUAL_USERNAME.lower():
                        print(f"Skipping unread indicator in own chat ({thread_identifier}).")
                        continue

                    lower_thread_identifier = thread_identifier.lower()

                    print(f"\nProcessing unread UI Thread: {thread_identifier} (key: {lower_thread_identifier})")

                    if lower_thread_identifier not in auto_responding:  # Use lower_thread_identifier for auto_responding dict
                        auto_responding[lower_thread_identifier] = True
                    if lower_thread_identifier not in all_threads_history:
                        all_threads_history[lower_thread_identifier] = {  # Use lower_thread_identifier
                            "users": [thread_identifier, BOT_ACTUAL_USERNAME],  # Original casing for user list
                            "messages": [],
                            "processed_stable_ids": set()
                        }
                    last_ts_for_thread = last_checked_timestamps.get(lower_thread_identifier, start_time - timedelta(
                        hours=1))  # Use lower_thread_identifier

                    if not u2_utils.open_thread_by_username(d_device, thread_identifier):
                        print(
                            f"ERROR: Could not open thread for {thread_identifier} even though it was marked unread. Skipping.")
                        active_thread_identifier = None
                        if not u2_utils.return_to_dm_list_from_thread(d_device):
                            print(
                                "ERROR: Failed to return to DM list after failing to open a thread. Attempting full nav.")
                            u2_utils.go_to_dm_list(d_device)
                        continue
                    active_thread_identifier = thread_identifier

                    messages_in_thread_ui = u2_utils.get_messages_from_open_thread(d_device, BOT_ACTUAL_USERNAME,
                                                                                   bot_sent_message_hashes,
                                                                                   max_messages=MESSAGE_FETCH_AMOUNT)
                    latest_msg_timestamp_this_cycle = last_ts_for_thread
                    new_ui_messages_to_process = []
                    # lower_thread_identifier is already defined
                    if "processed_stable_ids" not in all_threads_history[lower_thread_identifier]:
                        all_threads_history[lower_thread_identifier]["processed_stable_ids"] = set()

                    for msg_ui in messages_in_thread_ui:
                        if msg_ui["timestamp"] > latest_msg_timestamp_this_cycle:
                            latest_msg_timestamp_this_cycle = msg_ui["timestamp"]

                        stable_id = hash(str(msg_ui.get("user_id", "")) + str(msg_ui.get("text", "")))

                        if stable_id not in all_threads_history[lower_thread_identifier][
                            "processed_stable_ids"]:  # Use lower_thread_identifier
                            all_threads_history[lower_thread_identifier]["processed_stable_ids"].add(
                                stable_id)  # Use lower_thread_identifier

                            history_entry = {
                                "id": msg_ui["id"],
                                "stable_id_for_history": stable_id,
                                "user_id": msg_ui["user_id"],
                                "username": msg_ui["user_id"],
                                "text": msg_ui["text"],
                                "timestamp": msg_ui["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                            }
                            all_threads_history[lower_thread_identifier]["messages"].append(
                                history_entry)  # Use lower_thread_identifier
                            if msg_ui["user_id"].lower() != BOT_ACTUAL_USERNAME.lower():
                                new_ui_messages_to_process.append(msg_ui)
                                processed_message_ids.add(msg_ui["id"])

                    last_checked_timestamps[
                        lower_thread_identifier] = latest_msg_timestamp_this_cycle  # Use lower_thread_identifier

                    if not new_ui_messages_to_process:
                        print(
                            f"No new messages to process in unread thread {thread_identifier}. Blue dot might be for bot's own or already processed messages.")
                        active_thread_identifier = None
                        if not u2_utils.return_to_dm_list_from_thread(d_device):
                            print(
                                f"WARN: Failed to return to DM list cleanly from thread {thread_identifier} (no new messages). Attempting full nav.")
                            u2_utils.go_to_dm_list(d_device)
                        time.sleep(1)
                        continue

                    if new_ui_messages_to_process:
                        new_ui_messages_to_process.sort(key=lambda m: m["timestamp"])
                        actual_latest_user_message_text = new_ui_messages_to_process[-1]['text']
                        latest_message_id = new_ui_messages_to_process[-1]['id']
                        last_message_data = new_ui_messages_to_process[-1]
                        sender_username_ui = last_message_data["user_id"]
                        timestamp_approx_str = last_message_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                        sender_full_name_ui = "Unknown (UI)"  # Placeholder
                        sender_follower_count_ui = 0  # Placeholder

                        print(
                            f"Processing batch of {len(new_ui_messages_to_process)} new UI DMs in {thread_identifier} from {sender_username_ui}. Latest message: {actual_latest_user_message_text[:100]}...")

                        owner_remote_command_processed = False  # Flag for this new logic

                        if sender_username_ui.lower() == OWNER_USERNAME.lower():
                            command_parts = actual_latest_user_message_text.strip().split()
                            if not command_parts:
                                pass

                            command = command_parts[0].lower()
                            target_username = None
                            if len(command_parts) > 1:
                                target_username = command_parts[1]

                            # --- Handle Owner Remote Pause ---
                            if command == OWNER_REMOTE_PAUSE_KEYWORD.lower():
                                owner_command_target_username = command_parts[1] if len(
                                    command_parts) > 1 else None  # Renamed for clarity
                                definitive_target_key_for_state = None

                                if owner_command_target_username:
                                    if owner_command_target_username.lower() == BOT_ACTUAL_USERNAME.lower():
                                        pass  # Or some error message to owner if trying to pause self.

                                    print(
                                        f"Owner remote PAUSE command for target argument '{owner_command_target_username}' in owner's thread {thread_identifier}.")

                                    # Attempt to open/verify target user's chat
                                    if u2_utils.search_and_open_dm_with_user(d_device, owner_command_target_username,
                                                                             BOT_ACTUAL_USERNAME):
                                        definitive_target_username_from_ui_kw = u2_utils.get_username_from_open_chat_header(
                                            d_device)

                                        if not definitive_target_username_from_ui_kw:
                                            err_msg_header = f"Note: Opened chat for '{owner_command_target_username}', but could not read chat header. Action aborted."
                                            print(err_msg_header)
                                            if u2_utils.send_dm_in_open_thread(d_device,
                                                                               err_msg_header):  # Send error to owner in their chat
                                                bot_sent_message_hashes.add(hash(err_msg_header.strip()))
                                            # Ensure we go back to owner's chat if possible, or DM list
                                            if not u2_utils.open_thread_by_username(d_device,
                                                                                    thread_identifier):  # thread_identifier is owner's chat
                                                u2_utils.go_to_dm_list(d_device)
                                        else:
                                            definitive_target_key_for_state = definitive_target_username_from_ui_kw.lower()
                                            print(
                                                f"Confirmed target for PAUSE: '{definitive_target_username_from_ui_kw}' (key: '{definitive_target_key_for_state}')")

                                            auto_responding[definitive_target_key_for_state] = False
                                            paused_by_owner_threads.add(definitive_target_key_for_state)

                                            # Notify target user (already in their chat)
                                            target_notify_msg = TARGET_THREAD_PAUSED_BY_OWNER_NOTIFICATION.format(
                                                BOT_DISPLAY_NAME=BOT_DISPLAY_NAME)
                                            if u2_utils.send_dm_in_open_thread(d_device, target_notify_msg):
                                                bot_sent_message_hashes.add(hash(target_notify_msg.strip()))
                                                all_threads_history.setdefault(definitive_target_key_for_state, {
                                                    "users": [definitive_target_key_for_state, BOT_ACTUAL_USERNAME],
                                                    "messages": [], "processed_stable_ids": set()})
                                                history_entry_target_notify = {"id": hash(target_notify_msg),
                                                                               "stable_id_for_history": hash(
                                                                                   target_notify_msg),
                                                                               "user_id": BOT_ACTUAL_USERNAME,
                                                                               "username": BOT_ACTUAL_USERNAME,
                                                                               "text": target_notify_msg,
                                                                               "timestamp": datetime.now().strftime(
                                                                                   "%Y-%m-%d %H:%M:%S")}
                                                all_threads_history[definitive_target_key_for_state]["messages"].append(
                                                    # definitive_target_key_for_state is already lower
                                                    history_entry_target_notify)
                                                all_threads_history[definitive_target_key_for_state][
                                                    # definitive_target_key_for_state is already lower
                                                    "processed_stable_ids"].add(hash(target_notify_msg))

                                            # Return to owner's chat and send confirmation
                                            if u2_utils.open_thread_by_username(d_device,
                                                                                thread_identifier):  # thread_identifier is owner's chat (original case)
                                                owner_confirm_msg = OWNER_REMOTE_PAUSE_SUCCESS_CONFIRMATION.format(
                                                    BOT_DISPLAY_NAME=BOT_DISPLAY_NAME,
                                                    TARGET_USERNAME=definitive_target_username_from_ui_kw
                                                    # Original case for display
                                                )
                                                if u2_utils.send_dm_in_open_thread(d_device, owner_confirm_msg):
                                                    bot_sent_message_hashes.add(hash(owner_confirm_msg.strip()))
                                                    # Add owner confirmation to owner's chat history (already handled for thread_identifier)
                                            else:  # Failed to return to owner's chat
                                                print(
                                                    f"ERROR: Failed to return to owner's chat {thread_identifier} to send PAUSE confirmation.")
                                                # Owner confirmation is lost, but action was performed.
                                    else:  # Failed to open target user's chat
                                        err_msg_target = OWNER_REMOTE_TARGET_NOT_FOUND_ERROR.format(
                                            BOT_DISPLAY_NAME=BOT_DISPLAY_NAME,
                                            TARGET_USERNAME=owner_command_target_username
                                        )
                                        # This error message is sent in the owner's currently open chat (thread_identifier)
                                        if u2_utils.send_dm_in_open_thread(d_device, err_msg_target):
                                            bot_sent_message_hashes.add(hash(err_msg_target.strip()))
                                else:  # No target_username provided in command
                                    err_msg = OWNER_REMOTE_TARGET_NOT_FOUND_ERROR.format(
                                        BOT_DISPLAY_NAME=BOT_DISPLAY_NAME, TARGET_USERNAME="<missing_username>")
                                    if u2_utils.send_dm_in_open_thread(d_device, err_msg):
                                        bot_sent_message_hashes.add(hash(err_msg.strip()))
                                owner_remote_command_processed = True
                            # --- Handle Owner Remote Resume ---
                            elif command == OWNER_REMOTE_RESUME_KEYWORD.lower():
                                owner_command_target_username = command_parts[1] if len(command_parts) > 1 else None
                                definitive_target_key_for_state = None

                                if owner_command_target_username:
                                    if owner_command_target_username.lower() == BOT_ACTUAL_USERNAME.lower():
                                        pass  # Cannot resume self if not paused by owner.

                                    print(
                                        f"Owner remote RESUME command for target argument '{owner_command_target_username}' in owner's thread {thread_identifier}.")

                                    if u2_utils.search_and_open_dm_with_user(d_device, owner_command_target_username,
                                                                             BOT_ACTUAL_USERNAME):
                                        # Using a distinct variable name for the resume block as requested
                                        definitive_target_username_from_ui_kw_resume = u2_utils.get_username_from_open_chat_header(
                                            d_device)

                                        if not definitive_target_username_from_ui_kw_resume:
                                            err_msg_header = f"Note: Opened chat for '{owner_command_target_username}', but could not read chat header. Action aborted."
                                            print(err_msg_header)
                                            if u2_utils.send_dm_in_open_thread(d_device,
                                                                               err_msg_header):  # Send error to owner
                                                bot_sent_message_hashes.add(hash(err_msg_header.strip()))
                                            if not u2_utils.open_thread_by_username(d_device,
                                                                                    thread_identifier):  # Return to Owner's chat
                                                u2_utils.go_to_dm_list(d_device)
                                        else:
                                            definitive_target_key_for_state = definitive_target_username_from_ui_kw_resume.lower()
                                            print(
                                                f"Confirmed target for RESUME: '{definitive_target_username_from_ui_kw_resume}' (key: '{definitive_target_key_for_state}')")

                                            auto_responding[definitive_target_key_for_state] = True
                                            paused_by_owner_threads.discard(definitive_target_key_for_state)

                                            target_notify_msg = TARGET_THREAD_RESUMED_BY_OWNER_NOTIFICATION.format(
                                                BOT_DISPLAY_NAME=BOT_DISPLAY_NAME)
                                            if u2_utils.send_dm_in_open_thread(d_device, target_notify_msg):
                                                bot_sent_message_hashes.add(hash(target_notify_msg.strip()))
                                                all_threads_history.setdefault(definitive_target_key_for_state, {
                                                    "users": [definitive_target_key_for_state, BOT_ACTUAL_USERNAME],
                                                    "messages": [], "processed_stable_ids": set()})
                                                history_entry_target_notify = {"id": hash(target_notify_msg),
                                                                               "stable_id_for_history": hash(
                                                                                   target_notify_msg),
                                                                               "user_id": BOT_ACTUAL_USERNAME,
                                                                               "username": BOT_ACTUAL_USERNAME,
                                                                               "text": target_notify_msg,
                                                                               "timestamp": datetime.now().strftime(
                                                                                   "%Y-%m-%d %H:%M:%S")}
                                                all_threads_history[definitive_target_key_for_state]["messages"].append(
                                                    # definitive_target_key_for_state is already lower
                                                    history_entry_target_notify)
                                                all_threads_history[definitive_target_key_for_state][
                                                    # definitive_target_key_for_state is already lower
                                                    "processed_stable_ids"].add(hash(target_notify_msg))

                                            if u2_utils.open_thread_by_username(d_device,
                                                                                # thread_identifier is owner's chat (original case)
                                                                                thread_identifier):  # Return to Owner's chat
                                                owner_confirm_msg = OWNER_REMOTE_RESUME_SUCCESS_CONFIRMATION.format(
                                                    BOT_DISPLAY_NAME=BOT_DISPLAY_NAME,
                                                    TARGET_USERNAME=definitive_target_username_from_ui_kw_resume
                                                    # Original case for display
                                                )
                                                if u2_utils.send_dm_in_open_thread(d_device, owner_confirm_msg):
                                                    bot_sent_message_hashes.add(hash(owner_confirm_msg.strip()))
                                            else:
                                                print(
                                                    f"ERROR: Failed to return to owner's chat {thread_identifier} to send RESUME confirmation.")
                                    else:  # Failed to open target chat
                                        err_msg_target = OWNER_REMOTE_TARGET_NOT_FOUND_ERROR.format(
                                            BOT_DISPLAY_NAME=BOT_DISPLAY_NAME,
                                            TARGET_USERNAME=owner_command_target_username
                                        )
                                        if u2_utils.send_dm_in_open_thread(d_device,
                                                                           err_msg_target):  # Sent in Owner's chat
                                            bot_sent_message_hashes.add(hash(err_msg_target.strip()))
                                else:  # No target username
                                    err_msg = OWNER_REMOTE_TARGET_NOT_FOUND_ERROR.format(
                                        BOT_DISPLAY_NAME=BOT_DISPLAY_NAME, TARGET_USERNAME="<missing_username>")
                                    if u2_utils.send_dm_in_open_thread(d_device, err_msg):
                                        bot_sent_message_hashes.add(hash(err_msg.strip()))
                                owner_remote_command_processed = True

                        if owner_remote_command_processed:
                            for msg_data_item in new_ui_messages_to_process:
                                processed_message_ids.add(msg_data_item["id"])
                                stable_id_cmd = hash(
                                    str(msg_data_item.get("user_id", "")) + str(msg_data_item.get("text", "")))
                                all_threads_history[lower_thread_identifier]["processed_stable_ids"].add(
                                    stable_id_cmd)  # Use lower_thread_identifier

                            last_checked_timestamps[
                                lower_thread_identifier] = latest_msg_timestamp_this_cycle  # Use lower_thread_identifier

                            if active_thread_identifier != thread_identifier:  # active_thread_identifier keeps original casing for UI ops
                                if not u2_utils.open_thread_by_username(d_device,
                                                                        thread_identifier):  # UI ops use original casing
                                    u2_utils.go_to_dm_list(d_device)
                                active_thread_identifier = thread_identifier  # UI ops use original casing

                            time.sleep(random.randint(1, 2))
                            continue

                        user_command_processed = False  # Flag to indicate if the message was a command

                        # Check for THREAD_PAUSE_KEYWORD
                        if actual_latest_user_message_text.strip().lower() == THREAD_PAUSE_KEYWORD.lower():
                            print(
                                f"Thread pause keyword '{THREAD_PAUSE_KEYWORD}' received in thread {thread_identifier} from {sender_username_ui}.")
                            auto_responding[thread_identifier] = False

                            confirmation_text = THREAD_PAUSE_CONFIRMATION_MESSAGE.format(
                                BOT_DISPLAY_NAME=BOT_DISPLAY_NAME,
                                THREAD_RESUME_KEYWORD=THREAD_RESUME_KEYWORD
                            )

                            if active_thread_identifier and active_thread_identifier.lower() == thread_identifier.lower():
                                if u2_utils.send_dm_in_open_thread(d_device, confirmation_text):
                                    bot_sent_message_hashes.add(hash(confirmation_text.strip()))
                                    # Add to history
                                    history_entry_confirm = {
                                        "id": hash(confirmation_text), "stable_id_for_history": hash(confirmation_text),
                                        "user_id": BOT_ACTUAL_USERNAME, "username": BOT_ACTUAL_USERNAME,
                                        "text": confirmation_text,
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    all_threads_history[lower_thread_identifier]["messages"].append(
                                        history_entry_confirm)  # Use lower_thread_identifier
                                    all_threads_history[lower_thread_identifier]["processed_stable_ids"].add(
                                        # Use lower_thread_identifier
                                        hash(confirmation_text))
                                    print(f"Sent thread pause confirmation to {thread_identifier}.")
                                else:
                                    print(f"Failed to send thread pause confirmation to {thread_identifier}.")
                            else:  # Should ideally not happen if active_thread_identifier is managed well
                                print(
                                    f"WARN: Context issue sending pause confirmation to {thread_identifier}. Active: {active_thread_identifier}")

                            user_command_processed = True

                        # Check for THREAD_RESUME_KEYWORD (only if not already processed as a pause command)
                        elif actual_latest_user_message_text.strip().lower() == THREAD_RESUME_KEYWORD.lower():
                            print(
                                f"Thread resume keyword '{THREAD_RESUME_KEYWORD}' received in thread {thread_identifier} from {sender_username_ui}.")  # Corrected the f-string variable
                            if thread_identifier.lower() in paused_by_owner_threads:
                                print(
                                    f"Thread {thread_identifier} was paused by owner. User {sender_username_ui} cannot resume.")
                                notification_text = USER_CANNOT_RESUME_OWNER_PAUSE_MESSAGE.format(
                                    BOT_DISPLAY_NAME=BOT_DISPLAY_NAME)
                                if active_thread_identifier and active_thread_identifier.lower() == thread_identifier.lower():
                                    if u2_utils.send_dm_in_open_thread(d_device, notification_text):
                                        bot_sent_message_hashes.add(hash(notification_text.strip()))
                                        # Add to history (optional, but good for consistency)
                                        history_entry_notify = {
                                            "id": hash(notification_text),
                                            "stable_id_for_history": hash(notification_text),
                                            "user_id": BOT_ACTUAL_USERNAME, "username": BOT_ACTUAL_USERNAME,
                                            "text": notification_text,
                                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        }
                                        all_threads_history[lower_thread_identifier]["messages"].append(
                                            history_entry_notify)  # Use lower_thread_identifier
                                        all_threads_history[lower_thread_identifier]["processed_stable_ids"].add(
                                            # Use lower_thread_identifier
                                            hash(notification_text))
                                        print(f"Sent 'cannot resume' notification to {thread_identifier}.")
                                    else:
                                        print(f"Failed to send 'cannot resume' notification to {thread_identifier}.")
                                else:
                                    print(
                                        f"WARN: Context issue sending 'cannot resume' notification to {thread_identifier}. Active: {active_thread_identifier}")
                            else:
                                auto_responding[thread_identifier] = True  # Ensure it's set to True
                                confirmation_text = THREAD_RESUME_CONFIRMATION_MESSAGE.format(
                                    BOT_DISPLAY_NAME=BOT_DISPLAY_NAME)

                                if active_thread_identifier and active_thread_identifier.lower() == thread_identifier.lower():
                                    if u2_utils.send_dm_in_open_thread(d_device, confirmation_text):
                                        bot_sent_message_hashes.add(hash(confirmation_text.strip()))
                                        # Add to history
                                        history_entry_confirm = {
                                            "id": hash(confirmation_text),
                                            "stable_id_for_history": hash(confirmation_text),
                                            "user_id": BOT_ACTUAL_USERNAME, "username": BOT_ACTUAL_USERNAME,
                                            "text": confirmation_text,
                                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        }
                                        all_threads_history[lower_thread_identifier]["messages"].append(
                                            history_entry_confirm)  # Use lower_thread_identifier
                                        all_threads_history[lower_thread_identifier]["processed_stable_ids"].add(
                                            # Use lower_thread_identifier
                                            hash(confirmation_text))
                                        print(f"Sent thread resume confirmation to {thread_identifier}.")
                                    else:
                                        print(f"Failed to send thread resume confirmation to {thread_identifier}.")
                                else:  # Should ideally not happen
                                    print(
                                        f"WARN: Context issue sending resume confirmation to {thread_identifier}. Active: {active_thread_identifier}")
                            user_command_processed = True

                        if user_command_processed:
                            # Mark all messages in new_ui_messages_to_process as processed to prevent LLM call for the command
                            for msg_data_item in new_ui_messages_to_process:
                                processed_message_ids.add(msg_data_item["id"])
                                stable_id_cmd = hash(
                                    str(msg_data_item.get("user_id", "")) + str(msg_data_item.get("text", "")))
                                all_threads_history[lower_thread_identifier]["processed_stable_ids"].add(
                                    stable_id_cmd)  # Use lower_thread_identifier

                            last_checked_timestamps[
                                lower_thread_identifier] = latest_msg_timestamp_this_cycle  # Use lower_thread_identifier

                            # If a command was processed, we might want to skip the rest of the loop for this thread iteration (LLM calls etc.)
                            # Ensure we return to DM list and go to the next thread or cycle.
                            if active_thread_identifier and not u2_utils.return_to_dm_list_from_thread(d_device):
                                u2_utils.go_to_dm_list(d_device)
                            active_thread_identifier = None  # Reset active thread as we are done with this one for now
                            time.sleep(random.randint(1, 2))  # Brief pause
                            continue  # Continue to the next thread_identifier in unread_threads

                        if not auto_responding.get(lower_thread_identifier,  # Use lower_thread_identifier
                                                   True) and lower_thread_identifier not in paused_by_owner_threads:
                            if last_message_data["text"] and any(
                                    k_word in last_message_data["text"].lower() for k_word in
                                    ["resume", "start", "unpause",
                                     THREAD_RESUME_KEYWORD.lower()]):
                                auto_responding[lower_thread_identifier] = True  # Use lower_thread_identifier
                                resume_message = f"{BOT_DISPLAY_NAME}: Auto-response R E S U M E D for {thread_identifier}."  # Display original case
                                if u2_utils.send_dm_in_open_thread(d_device, resume_message):
                                    bot_sent_message_hashes.add(hash(resume_message.strip()))
                                    _perform_back_press(d_device)
                                    active_thread_identifier = None
                                print(
                                    f"Auto-response resumed for {thread_identifier} based on keyword in last message.")
                                for msg_data_item in new_ui_messages_to_process: processed_message_ids.add(
                                    msg_data_item["id"])
                                last_checked_timestamps[
                                    lower_thread_identifier] = latest_msg_timestamp_this_cycle  # Use lower_thread_identifier
                                if not u2_utils.return_to_dm_list_from_thread(d_device): u2_utils.go_to_dm_list(
                                    d_device)
                                active_thread_identifier = None
                                time.sleep(random.randint(1, 2))
                                continue
                            else:
                                print(f"Auto-response paused for {thread_identifier}. Skipping batch.")
                                for msg_data_item in new_ui_messages_to_process: processed_message_ids.add(
                                    msg_data_item["id"])
                                last_checked_timestamps[
                                    lower_thread_identifier] = latest_msg_timestamp_this_cycle  # Use lower_thread_identifier
                                if not u2_utils.return_to_dm_list_from_thread(d_device): u2_utils.go_to_dm_list(
                                    d_device)
                                active_thread_identifier = None
                                time.sleep(random.randint(1, 2))
                                continue

                        prompt_history_lines = []
                        # lower_thread_identifier is already defined
                        current_full_thread_history = all_threads_history[lower_thread_identifier][
                            "messages"]  # Use lower_thread_identifier
                        history_for_prompt_excluding_latest = [msg for msg in current_full_thread_history if
                                                               msg["id"] != latest_message_id]
                        final_messages_for_history_prompt = history_for_prompt_excluding_latest[-LLM_HISTORY_LENGTH:]

                        # Check if history for prompt is effectively empty (no user messages)
                        # This is to ensure the LLM uses its "Initial Interaction" greeting.
                        if not final_messages_for_history_prompt:
                            history_text_for_llm = ""
                            print(
                                "No prior messages in history_for_prompt_excluding_latest; sending empty history_text.")
                        else:
                            user_message_found_in_history = False
                            for hist_msg_check in final_messages_for_history_prompt:
                                if hist_msg_check["username"].lower() != BOT_ACTUAL_USERNAME.lower():
                                    user_message_found_in_history = True
                                    break

                            if not user_message_found_in_history:
                                history_text_for_llm = ""
                                print(
                                    "History for LLM contains only bot messages; sending empty history_text to trigger initial greeting.")
                            else:
                                for hist_msg in final_messages_for_history_prompt:
                                    role_display = BOT_DISPLAY_NAME if hist_msg[
                                                                           "username"].lower() == BOT_ACTUAL_USERNAME.lower() else "User"
                                    prompt_history_lines.append(
                                        f"{role_display} ({hist_msg['username']}): {hist_msg['text']}")
                                history_text_for_llm = "\n".join(prompt_history_lines)

                        prompt_first = format_message_for_llm(
                            PROMPT_FIRST_TEMPLATE, bot_display_name=BOT_DISPLAY_NAME,
                            bot_instagram_username=BOT_ACTUAL_USERNAME,
                            owner_username=OWNER_USERNAME, current_date=datetime.now().strftime('%Y-%m-%d'),
                            sender_username=sender_username_ui, thread_id=thread_identifier,
                            sender_full_name=sender_full_name_ui,
                            timestamp=timestamp_approx_str, sender_follower_count=sender_follower_count_ui,
                            history_text=history_text_for_llm, message_text=actual_latest_user_message_text
                        )
                        print(
                            f"Sending latest message to Gemini (1st pass) for {thread_identifier} from {sender_username_ui}: '{actual_latest_user_message_text[:50]}...'")
                        try:
                            response_first = chat_session.send_message(prompt_first)
                        except Exception as e:
                            print(
                                f"ERROR: Gemini API (1st pass) failed for {thread_identifier} with consolidated message: {e}")
                            for msg_data_item in new_ui_messages_to_process: processed_message_ids.add(
                                msg_data_item["id"])
                            last_checked_timestamps[
                                lower_thread_identifier] = latest_msg_timestamp_this_cycle  # Use lower_thread_identifier
                            if not u2_utils.return_to_dm_list_from_thread(d_device): u2_utils.go_to_dm_list(d_device)
                            active_thread_identifier = None
                            time.sleep(random.randint(1, 2))
                            continue

                        # ---- START: Logic to fetch and process messages that arrived *during* the first LLM call ----

                        # Fetch messages again (this was the previous step's goal, now moved here)
                        print(
                            f"INFO: Fetching messages from open thread '{active_thread_identifier}' after first LLM response (attempt).")
                        messages_after_first_response = []
                        # Only proceed if response_first was successfully obtained (i.e., the 'continue' in except block was not hit) and we are in an active thread
                        if active_thread_identifier:  # response_first must exist if we didn't 'continue'
                            messages_after_first_response = u2_utils.get_messages_from_open_thread(
                                d_device,
                                BOT_ACTUAL_USERNAME,
                                bot_sent_message_hashes,
                                max_messages=MESSAGE_FETCH_AMOUNT
                            )
                            if messages_after_first_response:
                                print(
                                    f"INFO: Fetched {len(messages_after_first_response)} messages after first response in '{active_thread_identifier}'.")
                            else:
                                print(
                                    f"INFO: No messages found or error fetching messages after first response in '{active_thread_identifier}'.")
                        else:  # not active_thread_identifier (or response_first failed, and we continued - though this path wouldn't be hit then)
                            print(
                                f"INFO: Skipping message fetch after first response as active_thread_identifier is None or initial LLM call failed.")

                        genuinely_new_messages = []
                        # Proceed only if we are in a thread, and messages were fetched. response_first is implied to be valid if we are here.
                        if active_thread_identifier and messages_after_first_response:
                            for msg_new_check in messages_after_first_response:
                                new_stable_id = hash(
                                    str(msg_new_check.get("user_id", "")) + str(msg_new_check.get("text", "")))
                                # lower_thread_identifier is already defined
                                if new_stable_id not in all_threads_history[lower_thread_identifier][
                                    # Use lower_thread_identifier
                                    "processed_stable_ids"] and \
                                        msg_new_check["user_id"].lower() != BOT_ACTUAL_USERNAME.lower():

                                    genuinely_new_messages.append(msg_new_check)
                                    all_threads_history[lower_thread_identifier]["processed_stable_ids"].add(
                                        new_stable_id)  # Use lower_thread_identifier
                                    processed_message_ids.add(msg_new_check["id"])

                                    new_history_entry = {
                                        "id": msg_new_check["id"],
                                        "stable_id_for_history": new_stable_id,
                                        "user_id": msg_new_check["user_id"],
                                        "username": msg_new_check["user_id"],
                                        "text": msg_new_check["text"],
                                        "timestamp": msg_new_check["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    all_threads_history[lower_thread_identifier]["messages"].append(
                                        new_history_entry)  # Use lower_thread_identifier
                                    if msg_new_check[
                                        "timestamp"] > latest_msg_timestamp_this_cycle:  # This timestamp is fine as is
                                        latest_msg_timestamp_this_cycle = msg_new_check["timestamp"]

                        # Proceed only if new messages were found. response_first is implied to be valid.
                        if genuinely_new_messages:
                            print(
                                f"INFO: Found {len(genuinely_new_messages)} new messages in '{thread_identifier}' after first LLM call. Updating prompt.")

                            genuinely_new_messages.sort(key=lambda m: m["timestamp"])

                            additional_text_parts = [msg['text'] for msg in genuinely_new_messages]
                            combined_new_text = "\n".join(additional_text_parts)

                            actual_latest_user_message_text = f"{actual_latest_user_message_text}\n{combined_new_text}"

                            print(
                                f"INFO: Combined message text for updated LLM call: '{actual_latest_user_message_text[:100]}...'")

                            prompt_first = format_message_for_llm(
                                PROMPT_FIRST_TEMPLATE, bot_display_name=BOT_DISPLAY_NAME,
                                bot_instagram_username=BOT_ACTUAL_USERNAME,
                                owner_username=OWNER_USERNAME, current_date=datetime.now().strftime('%Y-%m-%d'),
                                sender_username=sender_username_ui, thread_id=thread_identifier,
                                sender_full_name=sender_full_name_ui,
                                timestamp=timestamp_approx_str,
                                sender_follower_count=sender_follower_count_ui,
                                history_text=history_text_for_llm,
                                message_text=actual_latest_user_message_text
                            )
                            print(
                                f"INFO: Sending updated message to Gemini for {thread_identifier} from {sender_username_ui}.")
                            try:
                                response_first = chat_session.send_message(prompt_first)  # Re-assign response_first
                                print(
                                    f"INFO: Successfully received response from updated Gemini call for {thread_identifier}.")
                            except Exception as e:
                                print(
                                    f"ERROR: Gemini API (updated pass) failed for {thread_identifier}: {e}. Original 'response_first' will be used.")

                        # ---- END: Logic for messages arrived during first LLM call ----

                        function_triggered_this_message = False
                        llm_args_for_second_prompt = {}
                        llm_function_name = None

                        # It's possible response_first is None if the initial call failed AND the updated call also failed or wasn't attempted.
                        # However, the except block for the initial call has a 'continue', so this point should only be reached if response_first is valid.
                        if response_first is None:
                            print(
                                f"CRITICAL: response_first is None before processing parts for {thread_identifier}. This should not happen if initial API call exception leads to 'continue'. Skipping to prevent error.")
                            # Attempt to safely exit this iteration for the thread
                            if active_thread_identifier and not u2_utils.return_to_dm_list_from_thread(d_device):
                                u2_utils.go_to_dm_list(d_device)
                            active_thread_identifier = None
                            time.sleep(random.randint(1, 2))
                            continue  # Skip to the next thread_identifier in unread_threads

                        for part in response_first.parts:
                            if part.function_call:
                                function_triggered_this_message = True
                                func_call = part.function_call
                                llm_function_name = func_call.name
                                llm_args_for_second_prompt = dict(func_call.args)
                                print(
                                    f"LLM requested function: {llm_function_name} with args: {llm_args_for_second_prompt}")

                                # --- Send Pre-call Notification (Locally Formatted) ---
                                try:
                                    pre_call_notification_text = None
                                    template = PRE_CALL_TEMPLATES.get(llm_function_name)
                                    args = llm_args_for_second_prompt

                                    if template:
                                        format_args = {
                                            "sender_username": sender_username_ui,
                                            "owner_username": OWNER_USERNAME
                                        }
                                        # notify_owner template no longer uses message_preview
                                        if llm_function_name == "send_message":
                                            msg_content = args.get('message', '')
                                            format_args["message_preview"] = msg_content[:30] + '...' if len(
                                                msg_content) > 30 else msg_content
                                            format_args["target_username_or_thread_id"] = args.get(
                                                'target_username') or args.get('thread_id', 'the current chat')
                                        elif llm_function_name == "fetch_followers_followings":
                                            format_args["target_username"] = args.get('target_username',
                                                                                      'the specified user')
                                        elif llm_function_name == "owner_control_thread_autoresponse":  # New conditional block
                                            format_args["action"] = args.get('action', 'N/A_ACTION')
                                            format_args["target_username"] = args.get('target_username', 'N/A_TARGET')

                                        pre_call_notification_text = template.format(**format_args)
                                    else:
                                        # Fallback message
                                        pre_call_notification_text = f"I am about to perform the action '{llm_function_name}' with arguments: {str(args)}."
                                        print(
                                            f"WARN: No pre-call template found for function '{llm_function_name}'. Using fallback.")

                                    if pre_call_notification_text:
                                        print(
                                            f"Locally formatted pre-call notification for {thread_identifier}: {pre_call_notification_text[:100]}...")
                                        if active_thread_identifier and active_thread_identifier.lower() == thread_identifier.lower():
                                            if u2_utils.send_dm_in_open_thread(d_device, pre_call_notification_text):
                                                bot_sent_message_hashes.add(
                                                    hash(pre_call_notification_text.strip()))  # Verified
                                                print(
                                                    f"Successfully sent pre-call notification to {thread_identifier}.")
                                            else:
                                                print(
                                                    f"ERROR: Failed to send pre-call notification to {thread_identifier} in open thread.")
                                        else:
                                            # This case should ideally not be hit if context is managed well before this point for function calls.
                                            print(
                                                f"WARN: Pre-call: Active thread '{active_thread_identifier}' differs from target '{thread_identifier}'. Attempting to open target for pre-call message.")
                                            if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                                active_thread_identifier = thread_identifier  # Update active context
                                                if u2_utils.send_dm_in_open_thread(d_device,
                                                                                   pre_call_notification_text):
                                                    bot_sent_message_hashes.add(
                                                        hash(pre_call_notification_text.strip()))  # Verified
                                                    print(
                                                        f"Successfully sent pre-call notification to {thread_identifier} after reopening.")
                                                else:
                                                    print(
                                                        f"ERROR: Failed to send pre-call notification to {thread_identifier} after reopening.")
                                            else:
                                                print(
                                                    f"ERROR: Could not open {thread_identifier} to send pre-call notification. Notification lost.")
                                except Exception as e_pre_call:
                                    print(
                                        f"ERROR: Failed to format or send local pre-call notification for {thread_identifier}: {e_pre_call}")
                                    # Continue with function execution even if pre-call notification fails

                                # --- Handle Function Calls via UI ---
                                if llm_function_name == "notify_owner":
                                    original_ctx = {"thread_id": thread_identifier,
                                                    "sender_username": sender_username_ui,
                                                    "timestamp": timestamp_approx_str}
                                    send_message_to_owner_via_ui(
                                        llm_args_for_second_prompt.get("message", "LLM requested owner notification."),
                                        original_ctx)
                                    llm_args_for_second_prompt[
                                        "details_for_user"] = f"I've notified my owner, {OWNER_USERNAME}."
                                elif llm_function_name == "send_message":
                                    msg_to_send = llm_args_for_second_prompt.get("message")
                                    target_user = llm_args_for_second_prompt.get("target_username")
                                    target_thread_id_from_llm = llm_args_for_second_prompt.get("thread_id")
                                    actual_target = target_user or target_thread_id_from_llm
                                    success_send = False
                                    if msg_to_send and actual_target:
                                        message_with_sender = f"{sender_username_ui}: {msg_to_send}"
                                        # If the message that triggered this 'send_message' action is from the OWNER_USERNAME,
                                        # then the bot should send the message as itself, without prefixing the owner's name.
                                        if sender_username_ui.lower() == OWNER_USERNAME.lower():
                                            message_to_actually_send = msg_to_send  # Send as bot
                                        else:
                                            message_to_actually_send = f"{sender_username_ui}: {msg_to_send}"  # Prepend sender for non-owner initiated messages

                                        if actual_target.lower() != active_thread_identifier.lower():  # Sending to a different user/thread
                                            if not u2_utils.search_and_open_dm_with_user(d_device, actual_target,
                                                                                         BOT_ACTUAL_USERNAME):
                                                llm_args_for_second_prompt[
                                                    "details_for_user"] = f"I tried to message {actual_target} but couldn't find or open the chat."
                                            else:  # Successfully opened/switched to new target's chat
                                                active_thread_identifier = actual_target
                                                print(
                                                    f"INFO: Context switched to target {actual_target} for sending message.")
                                                success_send = u2_utils.send_dm_in_open_thread(d_device,
                                                                                               message_to_actually_send)  # Use modified variable
                                                if success_send:
                                                    bot_sent_message_hashes.add(hash(
                                                        message_to_actually_send.strip()))  # Verified - use actual sent text
                                                    _perform_back_press(d_device)  # Go back to DM list
                                                    active_thread_identifier = None  # We are no longer in actual_target's chat
                                                    print(
                                                        f"INFO: Returned to DM list after sending to {actual_target}. Active context reset to None.")
                                        else:  # Sending to the current active thread
                                            success_send = u2_utils.send_dm_in_open_thread(d_device,
                                                                                           message_to_actually_send)  # Use modified variable
                                            if success_send:
                                                bot_sent_message_hashes.add(
                                                    hash(message_to_actually_send.strip()))  # Verified
                                            # No _perform_back_press here; if LLM sends multiple messages to same user, stay in thread.
                                            # The final _perform_back_press for the 2nd pass explanation will handle exiting.

                                        if success_send:
                                            llm_args_for_second_prompt[
                                                "details_for_user"] = f"I've sent your requested message to {actual_target}."
                                        else:  # If sending failed (and not due to opening chat)
                                            llm_args_for_second_prompt[
                                                "details_for_user"] = f"I tried to send a message to {actual_target}, but it failed."

                                        # If context was switched for send_message, switch back to original thread for the explanation message
                                        original_target_for_loop = thread_identifier
                                        if active_thread_identifier is None and actual_target.lower() != original_target_for_loop.lower():  # Implies successful send to different user and back to DM list
                                            print(
                                                f"LLM send_message: Context was switched to '{actual_target}' and message sent. Opening original thread '{original_target_for_loop}' for explanation.")
                                            if u2_utils.open_thread_by_username(d_device, original_target_for_loop):
                                                active_thread_identifier = original_target_for_loop
                                                print(
                                                    f"Successfully switched back to original thread: {active_thread_identifier}")
                                            else:
                                                print(
                                                    f"CRITICAL ERROR: Failed to switch back to original thread {original_target_for_loop} after sending message to {actual_target}. Explanation might be lost or sent to wrong thread.")
                                                llm_args_for_second_prompt[
                                                    "details_for_user"] = f"I've sent your requested message to {actual_target}, but encountered an issue returning to our chat to provide a full confirmation. The message to {actual_target} was attempted."
                                                break  # out of parts loop
                                    else:
                                        llm_args_for_second_prompt[
                                            "details_for_user"] = "I was asked to send a message, but the target or message was unclear."
                                    print(
                                        f"INFO: 'details_for_user' for second LLM prompt for {llm_function_name}: {llm_args_for_second_prompt.get('details_for_user')}")
                                elif llm_function_name == "owner_control_thread_autoresponse":
                                    target_username_control_arg = llm_args_for_second_prompt.get(
                                        "target_username")  # From LLM
                                    action_control = llm_args_for_second_prompt.get("action")
                                    details_for_user_msg = ""
                                    definitive_target_key = None  # Will hold the UI-confirmed username, lowercased

                                    if sender_username_ui.lower() != OWNER_USERNAME.lower():
                                        details_for_user_msg = "Error: This function can only be used by the owner."
                                        print(
                                            f"Security: Attempt to use owner_control_thread_autoresponse by non-owner {sender_username_ui}.")
                                    elif not target_username_control_arg or not action_control:
                                        details_for_user_msg = "Error: target_username and action are required."
                                        print(
                                            f"Owner_control_thread_autoresponse: Missing parameters. Target arg: {target_username_control_arg}, Action: {action_control}")
                                    else:
                                        original_owner_thread_id = thread_identifier

                                        if not u2_utils.go_to_dm_list(d_device):
                                            details_for_user_msg = f"Error: Could not navigate to DM list before attempting to {action_control} {target_username_control_arg}."
                                            print(f"ERROR: {details_for_user_msg}")
                                        elif u2_utils.search_and_open_dm_with_user(d_device,
                                                                                   target_username_control_arg,
                                                                                   BOT_ACTUAL_USERNAME):
                                            # Successfully opened/found target chat
                                            # Get definitive username from header
                                            definitive_target_username_from_ui = u2_utils.get_username_from_open_chat_header(
                                                d_device)

                                            if not definitive_target_username_from_ui:
                                                details_for_user_msg = f"Error: Opened chat for '{target_username_control_arg}', but could not read chat header to confirm username."
                                                print(details_for_user_msg)
                                                # Attempt to go back to DM list if header read fails
                                                if not u2_utils.return_to_dm_list_from_thread(
                                                        d_device): u2_utils.go_to_dm_list(d_device)
                                                active_thread_identifier = None
                                            else:
                                                definitive_target_key = definitive_target_username_from_ui.lower()
                                                active_thread_identifier = definitive_target_key  # Context is now target's chat

                                                if action_control == "pause":
                                                    auto_responding[definitive_target_key] = False
                                                    paused_by_owner_threads.add(definitive_target_key)
                                                    print(
                                                        f"Owner ({OWNER_USERNAME}) remotely PAUSED thread for {definitive_target_key} (arg was {target_username_control_arg}) via LLM function.")
                                                    target_notify_msg = TARGET_THREAD_PAUSED_BY_OWNER_NOTIFICATION.format(
                                                        BOT_DISPLAY_NAME=BOT_DISPLAY_NAME)
                                                    if u2_utils.send_dm_in_open_thread(d_device, target_notify_msg):
                                                        bot_sent_message_hashes.add(hash(target_notify_msg.strip()))
                                                        all_threads_history.setdefault(definitive_target_key, {
                                                            "users": [definitive_target_key, BOT_ACTUAL_USERNAME],
                                                            "messages": [], "processed_stable_ids": set()})
                                                        history_entry_target_notify = {"id": hash(target_notify_msg),
                                                                                       "stable_id_for_history": hash(
                                                                                           target_notify_msg),
                                                                                       "user_id": BOT_ACTUAL_USERNAME,
                                                                                       "username": BOT_ACTUAL_USERNAME,
                                                                                       "text": target_notify_msg,
                                                                                       "timestamp": datetime.now().strftime(
                                                                                           "%Y-%m-%d %H:%M:%S")}
                                                        all_threads_history[definitive_target_key]["messages"].append(
                                                            history_entry_target_notify)
                                                        all_threads_history[definitive_target_key][
                                                            "processed_stable_ids"].add(hash(target_notify_msg))
                                                        details_for_user_msg = f"Successfully paused auto-responses for {definitive_target_username_from_ui} and notified them."
                                                    else:
                                                        details_for_user_msg = f"Successfully paused auto-responses for {definitive_target_username_from_ui}, but failed to send them a notification."

                                                elif action_control == "resume":
                                                    auto_responding[definitive_target_key] = True
                                                    paused_by_owner_threads.discard(definitive_target_key)
                                                    print(
                                                        f"Owner ({OWNER_USERNAME}) remotely RESUMED thread for {definitive_target_key} (arg was {target_username_control_arg}) via LLM function.")
                                                    target_notify_msg = TARGET_THREAD_RESUMED_BY_OWNER_NOTIFICATION.format(
                                                        BOT_DISPLAY_NAME=BOT_DISPLAY_NAME)
                                                    if u2_utils.send_dm_in_open_thread(d_device, target_notify_msg):
                                                        bot_sent_message_hashes.add(hash(target_notify_msg.strip()))
                                                        all_threads_history.setdefault(definitive_target_key, {
                                                            "users": [definitive_target_key, BOT_ACTUAL_USERNAME],
                                                            "messages": [], "processed_stable_ids": set()})
                                                        history_entry_target_notify = {"id": hash(target_notify_msg),
                                                                                       "stable_id_for_history": hash(
                                                                                           target_notify_msg),
                                                                                       "user_id": BOT_ACTUAL_USERNAME,
                                                                                       "username": BOT_ACTUAL_USERNAME,
                                                                                       "text": target_notify_msg,
                                                                                       "timestamp": datetime.now().strftime(
                                                                                           "%Y-%m-%d %H:%M:%S")}
                                                        all_threads_history[definitive_target_key]["messages"].append(
                                                            history_entry_target_notify)
                                                        all_threads_history[definitive_target_key][
                                                            "processed_stable_ids"].add(hash(target_notify_msg))
                                                        details_for_user_msg = f"Successfully resumed auto-responses for {definitive_target_username_from_ui} and notified them."
                                                    else:
                                                        details_for_user_msg = f"Successfully resumed auto-responses for {definitive_target_username_from_ui}, but failed to send them a notification."
                                                else:
                                                    details_for_user_msg = f"Error: Invalid action '{action_control}' for {definitive_target_username_from_ui}. Must be 'pause' or 'resume'."
                                                    print(
                                                        f"Owner_control_thread_autoresponse: Invalid action {action_control} by {OWNER_USERNAME}")

                                                # Return to DM list from target's chat
                                                if not u2_utils.return_to_dm_list_from_thread(
                                                        d_device): u2_utils.go_to_dm_list(d_device)
                                                active_thread_identifier = None
                                        else:  # Failed to search_and_open_dm_with_user
                                            details_for_user_msg = f"Error: Could not find or open DM thread with user '{target_username_control_arg}' to {action_control}."
                                            print(details_for_user_msg)
                                            active_thread_identifier = None  # Should be in DM list or failed state

                                        # Restore context to owner's thread for the LLM's second response
                                        # (Copied from previous implementation, seems okay)
                                        print(
                                            f"Attempting to restore context to owner's thread: {original_owner_thread_id}. Current active_thread_identifier (should be None): {active_thread_identifier}")
                                        if active_thread_identifier is None:
                                            if u2_utils.open_thread_by_username(d_device, original_owner_thread_id):
                                                active_thread_identifier = original_owner_thread_id
                                                print(
                                                    f"Successfully switched back to owner's thread: {active_thread_identifier}")
                                            else:
                                                print(
                                                    f"CRITICAL ERROR: Failed to switch back to owner's thread {original_owner_thread_id}. LLM explanation might be lost.")
                                                details_for_user_msg += " (Error: Could not return to our chat for this confirmation.)"
                                        elif active_thread_identifier.lower() != original_owner_thread_id.lower():
                                            print(
                                                f"WARN: Context issue. Active thread {active_thread_identifier} was not None. Attempting to open owner's thread {original_owner_thread_id}.")
                                            if u2_utils.open_thread_by_username(d_device, original_owner_thread_id):
                                                active_thread_identifier = original_owner_thread_id
                                            else:
                                                print(
                                                    f"CRITICAL ERROR: Failed to force switch to owner's thread {original_owner_thread_id}.")
                                                details_for_user_msg += " (Error: Context switch issue for this confirmation.)"
                                        else:
                                            print(
                                                f"Context is already owner's thread: {active_thread_identifier}. No switch needed.")

                                    llm_args_for_second_prompt["details_for_user"] = details_for_user_msg
                                elif llm_function_name == "fetch_followers_followings":
                                    target_fetch_user = llm_args_for_second_prompt.get("target_username")
                                    llm_args_for_second_prompt[
                                        "details_for_user"] = f"Fetching followers/followings for {target_fetch_user} via UI is complex and slow. This feature is currently stubbed for UI automation."
                                    print(f"STUB: UI fetch_followers_followings for {target_fetch_user}")
                                elif llm_function_name == "trigger_thread_pause":
                                    if thread_identifier:  # Ensure thread_identifier is available
                                        auto_responding[thread_identifier] = False
                                        reason = llm_args_for_second_prompt.get("reason",
                                                                                "no specific reason provided.")

                                        # Prepare the message for the user for PROMPT_SECOND_TEMPLATE
                                        pause_details_for_user = THREAD_PAUSE_CONFIRMATION_MESSAGE.format(
                                            BOT_DISPLAY_NAME=BOT_DISPLAY_NAME,
                                            THREAD_RESUME_KEYWORD=THREAD_RESUME_KEYWORD
                                        )
                                        llm_args_for_second_prompt[
                                            "details_for_user"] = f"I am now pausing auto-responses in this chat. {pause_details_for_user} The reason given was: {reason}"
                                        print(
                                            f"Thread pause activated by LLM for thread {thread_identifier}. Reason: {reason}")
                                    else:
                                        llm_args_for_second_prompt[
                                            "details_for_user"] = "I tried to pause this chat, but there was an issue identifying the specific chat thread. Please try again or contact the owner."
                                        print(
                                            f"ERROR: LLM tried to trigger_thread_pause but thread_identifier was not available.")
                                elif llm_function_name == view_dms_func.name:
                                    target_thread_id_for_view = llm_args_for_second_prompt.get("thread_id")
                                    if target_thread_id_for_view:
                                        # Call view_dms, ensuring sender_username_ui is passed as the calling_username
                                        # sender_username_ui is the one who sent the message to the bot
                                        dm_history_result = view_dms(target_thread_id_for_view, sender_username_ui)

                                        owner_notification_context = {
                                            "thread_id": thread_identifier,
                                            # This is the owner's current chat with the bot
                                            "sender_username": sender_username_ui,  # This is the owner
                                            "timestamp": timestamp_approx_str,
                                            "action_details": f"Requested to view DMs for thread: {target_thread_id_for_view}"
                                        }

                                        # Format the message body for the owner
                                        if not dm_history_result.startswith(
                                                "Error:") and not dm_history_result.startswith("No local"):
                                            owner_message_body = f"DM history for '{target_thread_id_for_view}':\n{dm_history_result}"
                                        else:
                                            owner_message_body = dm_history_result

                                        send_message_to_owner_via_ui(owner_message_body, owner_notification_context)

                                        llm_args_for_second_prompt[
                                            "details_for_user"] = f"I have attempted to fetch and send the DM history for '{target_thread_id_for_view}' to your chat."
                                    else:
                                        llm_args_for_second_prompt[
                                            "details_for_user"] = "I was asked to view DMs, but the target thread_id was not specified."
                                    print(
                                        f"Handled view_dms. Details for user: {llm_args_for_second_prompt.get('details_for_user')}")
                            elif part.text:  # Direct text reply from LLM
                                reply_text = format_message_for_llm(part.text.strip(),
                                                                    bot_display_name=BOT_DISPLAY_NAME,
                                                                    bot_actual_username=BOT_ACTUAL_USERNAME)
                                print(f"LLM direct reply for {thread_identifier}: {reply_text[:50]}...")
                                message_sent_successfully = False
                                if active_thread_identifier and active_thread_identifier.lower() == thread_identifier.lower():
                                    if u2_utils.send_dm_in_open_thread(d_device, reply_text):
                                        message_sent_successfully = True
                                        bot_sent_message_hashes.add(hash(reply_text.strip()))  # Verified
                                else:  # Should not happen if send_message context switch is handled correctly
                                    print(
                                        f"LLM direct reply: Active thread is '{active_thread_identifier}', target is '{thread_identifier}'. Re-opening target.")
                                    if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                        active_thread_identifier = thread_identifier
                                        if u2_utils.send_dm_in_open_thread(d_device, reply_text):
                                            message_sent_successfully = True
                                            bot_sent_message_hashes.add(hash(reply_text.strip()))  # Verified
                                    else:
                                        print(
                                            f"ERROR: Could not re-open {thread_identifier} to send LLM direct reply. Message lost.")
                                # No _perform_back_press here for direct replies yet, handled by 2nd pass or end of loop.

                        if function_triggered_this_message and llm_function_name and not critical_context_switch_error:
                            function_execution_summary = llm_args_for_second_prompt.get("details_for_user",
                                                                                        "I performed an action based on your message.")
                            prompt_second = format_message_for_llm(
                                PROMPT_SECOND_TEMPLATE, bot_display_name_on_profile=BOT_DISPLAY_NAME,
                                bot_instagram_username=BOT_ACTUAL_USERNAME,
                                sender_username=sender_username_ui, message_text=actual_latest_user_message_text,
                                thread_id=thread_identifier, function_name=llm_function_name,
                                function_execution_summary=function_execution_summary,  # Consolidated placeholder
                                sender_full_name=sender_full_name_ui, timestamp=timestamp_approx_str,
                                sender_follower_count=sender_follower_count_ui, owner_username=OWNER_USERNAME
                            )

                            user_explanation = None
                            message_sent_successfully_explain = False  # Tracks if the explanation was successfully *sent*

                            print(
                                f"INFO: Attempting second LLM call for {llm_function_name} in thread {thread_identifier}. Summary input to LLM: {function_execution_summary[:100]}...")
                            for attempt in range(MAX_ATTEMPTS):
                                try:
                                    response_second = chat_session.send_message(prompt_second)
                                    for part_second in response_second.parts:
                                        if part_second.text:
                                            user_explanation = format_message_for_llm(part_second.text.strip(),
                                                                                      bot_display_name=BOT_DISPLAY_NAME,
                                                                                      bot_actual_username=BOT_ACTUAL_USERNAME)
                                            # Generation successful, break from retry loop
                                    if user_explanation:  # Check if user_explanation was populated
                                        print(
                                            f"INFO: Successfully received explanation from second LLM for {thread_identifier} (attempt {attempt + 1}): {user_explanation[:100]}...")
                                        break
                                except Exception as e:
                                    print(
                                        f"ERROR: Gemini API (2nd pass) attempt {attempt + 1}/{MAX_ATTEMPTS} failed for {thread_identifier}: {e}")
                                    if attempt < MAX_ATTEMPTS - 1:
                                        time.sleep(2)  # Wait before retrying
                                else:  # If try was successful (no exception) and user_explanation was found
                                    if user_explanation:  # Ensure explanation was actually extracted
                                        break

                            if user_explanation is None:  # All attempts failed or no text part found
                                print(
                                    f"All {MAX_ATTEMPTS} attempts for Gemini API (2nd pass) failed for {thread_identifier}. Using fallback explanation.")
                                user_explanation = f"Regarding your request: {function_execution_summary}. I tried to get a more detailed confirmation, but I'm having a little trouble generating it right now."
                                print(
                                    f"INFO: Using fallback explanation for {thread_identifier} as second LLM call failed all attempts. Fallback: {user_explanation[:100]}...")
                                # message_sent_successfully_explain remains False as generation 'failed'

                            # Attempt to send the user_explanation (either generated or fallback)
                            if user_explanation:  # Ensure there's something to send
                                message_sent_successfully_explain = False  # Initialize before attempting to send
                                print(f"INFO: Ensuring thread '{thread_identifier}' is open to send explanation.")

                                if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                    active_thread_identifier = thread_identifier  # Update active context
                                    print(
                                        f"INFO: Thread '{thread_identifier}' successfully opened/focused for explanation.")
                                    print(
                                        f"INFO: Attempting to send explanation to {thread_identifier} (current active: {active_thread_identifier}). Explanation: {user_explanation[:100]}...")
                                    for attempt_send in range(SEND_EXPLANATION_ATTEMPTS):
                                        if u2_utils.send_dm_in_open_thread(d_device, user_explanation):
                                            message_sent_successfully_explain = True
                                            bot_sent_message_hashes.add(hash(user_explanation.strip()))  # Verified
                                            print(
                                                f"INFO: Successfully sent explanation to {thread_identifier} (attempt {attempt_send + 1}).")
                                            break  # Exit send retry loop on success
                                        else:
                                            print(
                                                f"ERROR: Failed to send explanation to {thread_identifier} (in supposedly open thread) attempt {attempt_send + 1}/{SEND_EXPLANATION_ATTEMPTS}.")
                                            if attempt_send < SEND_EXPLANATION_ATTEMPTS - 1:
                                                time.sleep(1)
                                            elif attempt_send == SEND_EXPLANATION_ATTEMPTS - 1:  # Last attempt failed
                                                print(
                                                    f"ERROR: FINAL - Failed to send explanation to {thread_identifier} after {SEND_EXPLANATION_ATTEMPTS} attempts. Message: {user_explanation[:50]}...")
                                else:
                                    print(
                                        f"ERROR: Failed to open thread '{thread_identifier}' to send explanation. Message: {user_explanation[:50]}... lost.")
                                    # message_sent_successfully_explain remains False

                            if message_sent_successfully_explain:  # Only perform back press if message was sent
                                _perform_back_press(d_device)
                                active_thread_identifier = None
                            # If message sending failed, we are likely still in the original user's thread or couldn't open it.
                            # No back press here allows subsequent error handling or cycle end to manage UI state.

                        elif not function_triggered_this_message:  # If it was a direct reply, no 2nd pass, so perform back press here
                            _perform_back_press(d_device)
                            active_thread_identifier = None

                        for msg_data_item in new_ui_messages_to_process:
                            processed_message_ids.add(msg_data_item["id"])

                        if critical_context_switch_error:
                            print(
                                f"Critical context switch error occurred for thread {thread_identifier}. Skipping to next thread if any.")
                            if not u2_utils.return_to_dm_list_from_thread(d_device): u2_utils.go_to_dm_list(d_device)
                            active_thread_identifier = None
                            time.sleep(random.randint(1, 2))
                            continue

                    last_checked_timestamps[
                        lower_thread_identifier] = latest_msg_timestamp_this_cycle  # Use lower_thread_identifier
                    print(
                        f"Finished checks for unread thread {thread_identifier}. Last check updated to {latest_msg_timestamp_this_cycle.strftime('%H:%M')}")  # Display original case

                    if active_thread_identifier:  # If still in a thread (e.g. after direct reply, before 2nd pass failed or was skipped)
                        if not u2_utils.return_to_dm_list_from_thread(d_device):
                            print(
                                f"WARN: Failed to return to DM list cleanly from thread {thread_identifier} after processing. Attempting full nav.")
                            u2_utils.go_to_dm_list(d_device)
                        active_thread_identifier = None
                    time.sleep(random.randint(1, 3))

                sleep_after_cycle = False  # Processed DMs, so quick re-check

            else:  # No unread_threads found by blue dot
                print("No unread DMs detected by blue dot.")
                print(f"Sleeping for {BLUE_DOT_CHECK_INTERVAL} seconds (no unread DMs).")
                time.sleep(BLUE_DOT_CHECK_INTERVAL)
                sleep_after_cycle = False  # Already slept

        except Exception as e:
            print(f"!!!!!!!!!! MAJOR ERROR IN UI AUTO-RESPOND LOOP !!!!!!!!!!: {e}")
            import traceback
            traceback.print_exc()
            try:
                print("Attempting to recover UI state by ensuring Instagram is open and going to DM list...")
                u2_utils.ensure_instagram_open(d_device)
                u2_utils.go_to_dm_list(d_device)
                active_thread_identifier = None  # Reset active thread context
            except Exception as e2:
                print(f"Failed to recover UI state during error handling: {e2}. Stopping app as a last resort.")
                # Consider d_device.app_stop("com.instagram.android")
            # sleep_after_cycle is True by default here.

        if sleep_after_cycle:  # True if an exception occurred, or if initial nav to DM list failed.
            sleep_duration = random.randint(MIN_SLEEP_TIME, MAX_SLEEP_TIME)
            print(
                f"Sleeping for {sleep_duration} seconds (long interval, typically after an error or initial nav failure).")
            time.sleep(sleep_duration)


def graceful_exit(signum, frame):
    global d_device
    print("\nSIGINT received, shutting down UI automator...")
    if d_device:
        try:
            # Optional: Try to navigate to home or stop app if desired for cleanup
            # u2_utils.go_to_home(d_device)
            # d_device.app_stop("com.instagram.android")
            print("UI automation actions on exit (if any) complete.")
        except Exception as e:
            print(f"Error during exit cleanup: {e}")
    exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, graceful_exit)

    try:
        print(f"Attempting to connect to uiautomator2 device: {d_device_identifier}...")
        if not d_device_identifier:
            raise Exception(
                "Multiple ADB devices detected, but no specific 'd_device_identifier' was set in the script.")

        d_device = u2.connect(d_device_identifier)
        if not d_device:
            raise Exception("u2.connect() returned None, connection failed.")

        # Simple operation to check connection instead of d_device.healthcheck()
        device_info = d_device.device_info
        if not device_info:
            raise Exception("Failed to get device_info after connect. Connection might be unstable.")
        print(
            f"Successfully connected to: {device_info.get('model', 'Unknown Model')} (Serial: {device_info.get('serial', 'N/A')})")
        # print(f"Screen resolution: {d_device.window_size()}")

    except Exception as e:
        print(f"FATAL: Could not connect to uiautomator2 device. Error: {e}")
        print("Please ensure:")
        print("1. Your target Android device/emulator is listed in `adb devices`.")
        print(
            "2. `atx-agent` is running on the target device (run `python -m uiautomator2 init --serial YOUR_TARGET_DEVICE_ID` if needed).")
        print("3. If connecting via WiFi, both your computer and device are on the same network,")
        print("   and the device identifier (IP:PORT or mDNS name) is correct and reachable.")
        print(f"4. You've set 'd_device_identifier' correctly in the script (currently: '{d_device_identifier}').")
        exit(1)

    if not login_ui():
        print("FATAL: login_ui failed. Exiting.")
        exit(1)

    print_bot_user_info_ui()
    print("\nStarting Instagram DM Bot with UI Automation (uiautomator2)...")
    auto_respond_via_ui()
