import uiautomator2 as u2
import time
import random
import signal
from datetime import datetime, timedelta
from config import (API_KEY, OWNER_USERNAME, PROMPT_FIRST_TEMPLATE, PROMPT_SECOND_TEMPLATE,
                    BOT_NAME, BOT_DISPLAY_NAME, THREAD_FETCH_AMOUNT, MESSAGE_FETCH_AMOUNT,
                    # Added BLUE_DOT_CHECK_INTERVAL
                    MIN_SLEEP_TIME, MAX_SLEEP_TIME, BLUE_DOT_CHECK_INTERVAL,
                    NOTIFICATION_CHECK_INTERVAL, DM_LIST_CHECK_INTERVAL)  # SESSION_ID removed
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

import uiautomator2_utils as u2_utils  # Our new helper

# --- uiautomator2 Device Connection ---
# USER: Configure your device connection here
# d = u2.connect() # Default: first USB device or emulator
d_device_identifier = "192.168.29.207:5555"
# d = u2.connect_usb("")
# For this script, we assume 'd' is initialized globally after successful connection.
d_device = None  # Will be initialized in __main__

# --- Global Variables ---
BOT_ACTUAL_USERNAME = BOT_NAME  # Initial assumption, verified in login_ui
# Key: thread_identifier (peer_username/group_name), Value: bool
auto_responding = {}
genai.configure(api_key=API_KEY)
start_time = datetime.now()
last_checked_timestamps = {}  # Key: thread_identifier, Value: datetime object
# Key: thread_identifier, Value: {"users": [usernames], "messages": []}
all_threads_history = {}
# For processed_message_ids, use a tuple of (text, approx_timestamp_str, sender_username_ui) for uniqueness
processed_message_ids = set()

# --- Gemini Function Declarations (Descriptions might need slight tweaks for UI context) ---
# Parameters like "thread_id" will now refer to a UI-based thread identifier (e.g., peer username)
# (Function declarations like notify_owner_func, pause_response_func etc. are largely the same as your original,
#  ensure their descriptions make sense in a UI context if needed. For brevity, not repeating them all here.
#  Make sure `OWNER_USERNAME` and `BOT_NAME` are used from config where appropriate.)

notify_owner_func = FunctionDeclaration(
    name="notify_owner",
    description=f"Notify the owner ({OWNER_USERNAME}) about a message with detailed context.",
    parameters={  # ... (same as original, ensure thread_id description is clear)
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
# ... Add other function declarations: pause_response_func, resume_response_func, target_thread_func,
# send_message_func, list_threads_func, view_dms_func, fetch_followers_followings_func
# For fetch_followers_followings, be very clear in description it's UI intensive and limited.
# Example for send_message_func:
send_message_func = FunctionDeclaration(
    name="send_message",
    description="Sends a message to a specified user or existing thread via UI.",
    parameters={
        "type": "object", "properties": {
            "message": {"type": "string", "description": "The message to send"},
            "target_username": {"type": "string",
                                "description": "The username to send the message to (will find or start DM)"},
            "thread_id": {"type": "string",
                          "description": "The existing thread identifier (peer username/group name) to send to (optional)"}
        }, "required": ["message"]
    }
)
fetch_followers_followings_func = FunctionDeclaration(
    name="fetch_followers_followings",
    description=f"Fetches followers/followings for a user. UI-Intensive: SLOW and LIMITED results. Only callable by {OWNER_USERNAME}.",
    parameters={
        "type": "object", "properties": {
            "target_username": {"type": "string", "description": "The Instagram username to fetch for"},
            "max_count": {"type": "integer", "description": "Approx max to fetch (UI limited, e.g., 10-20)"}
        }, "required": ["target_username"]
    }
)

# Make sure all your functions are in this list
tools = Tool(function_declarations=[
    notify_owner_func, send_message_func,  # Add ALL your other funcs here
    # pause_response_func, resume_response_func, target_thread_func,
    # list_threads_func, view_dms_func,
    fetch_followers_followings_func
])
model = genai.GenerativeModel(
    "gemini-1.5-flash-latest", tools=tools)  # Or your preferred model


def format_message_for_llm(template_string: str, **kwargs) -> str:
    for key, value in kwargs.items():
        template_string = template_string.replace(f"[[{key}]]", str(value))
    return template_string


def send_message_to_owner_via_ui(message_body, original_context):
    global d_device, BOT_ACTUAL_USERNAME
    if not OWNER_USERNAME:
        print("ERROR: OWNER_USERNAME not configured.")
        return

    full_message_to_owner = (f"{BOT_DISPLAY_NAME} ({BOT_ACTUAL_USERNAME}) Update for Master {OWNER_USERNAME}:\n"
                             f"{message_body}\n---Original Context---\n"
                             f"Thread: {original_context.get('thread_id', 'N/A')}\n"
                             f"Sender: {original_context.get('sender_username', 'N/A')}\n"
                             f"Timestamp: {original_context.get('timestamp', 'N/A')}\n")

    print(
        f"Attempting to send to owner ({OWNER_USERNAME}) via UI: {full_message_to_owner[:100]}...")
    if u2_utils.search_and_open_dm_with_user(d_device, OWNER_USERNAME, BOT_ACTUAL_USERNAME):
        if u2_utils.send_dm_in_open_thread(d_device, full_message_to_owner):
            print(f"Message sent to owner {OWNER_USERNAME} via UI.")
        else:
            print(f"Failed to type/send DM content to owner {OWNER_USERNAME}.")
    else:
        print(f"Failed to open/start DM thread with owner {OWNER_USERNAME}.")
    u2_utils.go_to_dm_list(d_device)  # Ensure back in DM list for next cycle


def login_ui():
    global d_device, BOT_ACTUAL_USERNAME
    print("Attempting UI Login/Setup...")
    u2_utils.ensure_instagram_open(d_device)  # Make sure Instagram is open
    time.sleep(3)  # Give app time to settle

    # Get bot's actual username from its profile page if possible
    profile_info = u2_utils.get_bot_profile_info(
        d_device, BOT_NAME)  # BOT_NAME from config is initial guess
    if profile_info.get("username"):
        BOT_ACTUAL_USERNAME = profile_info["username"]
        if BOT_ACTUAL_USERNAME.lower() != BOT_NAME.lower():
            print(
                f"WARNING: Actual bot username '{BOT_ACTUAL_USERNAME}' differs from BOT_NAME config '{BOT_NAME}'. Using actual.")
    else:
        print(
            f"WARNING: Could not verify bot username from profile. Using BOT_NAME from config: '{BOT_NAME}'. Ensure this is correct.")
        BOT_ACTUAL_USERNAME = BOT_NAME

    if not OWNER_USERNAME:
        print("CRITICAL ERROR: OWNER_USERNAME is not configured in config.py. Bot cannot function correctly.")
        return False

    print(
        f"UI 'Login' complete. Bot Username: {BOT_ACTUAL_USERNAME}, Owner: {OWNER_USERNAME}")
    u2_utils.go_to_dm_list(d_device)  # End in DM list
    return True


def print_bot_user_info_ui():
    global d_device, BOT_ACTUAL_USERNAME
    print(f"\n--- Bot ({BOT_ACTUAL_USERNAME}) Profile Info (UI Scraped) ---")
    # Re-scrape or use stored if available
    info = u2_utils.get_bot_profile_info(d_device, BOT_ACTUAL_USERNAME)
    print(f"  Username: {info.get('username', BOT_ACTUAL_USERNAME)}")
    print(f"  Full Name: {info.get('full_name', 'N/A')}")
    print(f"  Biography: {info.get('biography', 'N/A')}")
    print(f"  Followers: {info.get('follower_count', 'N/A')}")
    u2_utils.go_to_dm_list(d_device)  # Return to DMs


def auto_respond_via_ui():
    global d_device, auto_responding, last_checked_timestamps, processed_message_ids, all_threads_history, BOT_ACTUAL_USERNAME

    print("Ensuring Instagram is open at the start of the bot cycle...")
    u2_utils.ensure_instagram_open(d_device)
    # Assuming ensure_instagram_open will handle critical errors or the script will fail later if it's not open.
    print("Instagram check/start attempt complete.")

    if not BOT_ACTUAL_USERNAME:
        print("CRITICAL: Bot username not determined. Cannot start auto-responder. Run login_ui first.")
        return

    chat_session = model.start_chat(history=[])  # Gemini chat session

    while True:
        # Flag to determine if long sleep is needed. Default to True for errors.
        sleep_after_cycle = True
        try:
            print(
                f"\n--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} --- UI Bot Cycle ---")

            # 1. Navigate to DM List and check for unread threads (blue dot indicator)
            # Notification-based checks have been removed as they were less reliable than direct UI inspection.
            if not u2_utils.go_to_dm_list(d_device):
                print(
                    "ERROR: Failed to navigate to DM list at the start of the cycle. Retrying after sleep.")
                # sleep_after_cycle remains True for the long sleep
                continue

            # `unread_threads` is a list of usernames (thread_identifiers) that have the unread indicator.
            unread_threads = u2_utils.check_for_unread_dm_threads(d_device)

            if unread_threads:
                print(
                    f"Found {len(unread_threads)} unread thread(s) by blue dot: {unread_threads}")
                active_thread_identifier = None  # Tracks the currently open thread

                for thread_identifier in unread_threads:
                    critical_context_switch_error = False  # Initialize for this thread
                    # `thread_identifier` here is the username of the other party in the DM thread.
                    if thread_identifier.lower() == BOT_ACTUAL_USERNAME.lower():
                        print(
                            f"Skipping unread indicator in own chat ({thread_identifier}).")
                        continue

                    print(
                        f"\nProcessing unread UI Thread: {thread_identifier}")

                    # Initialize auto-responding state and history if this is a new thread
                    if thread_identifier not in auto_responding:
                        auto_responding[thread_identifier] = True
                    if thread_identifier not in all_threads_history:
                        # For users, it's usually [thread_identifier, BOT_ACTUAL_USERNAME]
                        # This might need adjustment if group chats are handled differently by check_for_unread_dm_threads
                        all_threads_history[thread_identifier] = {"users": [thread_identifier, BOT_ACTUAL_USERNAME],
                                                                  "messages": []}

                    # Get the last time messages were checked for this specific thread
                    last_ts_for_thread = last_checked_timestamps.get(thread_identifier,
                                                                     start_time - timedelta(hours=1))

                    # Open the specific thread identified as unread
                    if not u2_utils.open_thread_by_username(d_device, thread_identifier):
                        print(
                            f"ERROR: Could not open thread for {thread_identifier} even though it was marked unread. Skipping.")
                        active_thread_identifier = None
                        # Attempt to return to DM list to ensure stability for the next iteration
                        if not u2_utils.return_to_dm_list_from_thread(d_device):
                            print(
                                "ERROR: Failed to return to DM list after failing to open a thread. Attempting full nav.")
                            # Try full navigation
                            u2_utils.go_to_dm_list(d_device)
                        continue  # Move to the next unread thread
                    active_thread_identifier = thread_identifier

                    # Fetch messages from the now-open thread
                    messages_in_thread_ui = u2_utils.get_messages_from_open_thread(d_device, BOT_ACTUAL_USERNAME,
                                                                                   MESSAGE_FETCH_AMOUNT)
                    latest_msg_timestamp_this_cycle = last_ts_for_thread
                    new_ui_messages_to_process = []

                    # Process fetched messages to find new ones
                    for msg_ui in messages_in_thread_ui:
                        # Add to global history if not already there
                        is_in_history = any(h_msg["id"] == msg_ui["id"] for h_msg in
                                            all_threads_history[thread_identifier]["messages"])
                        if not is_in_history:
                            all_threads_history[thread_identifier]["messages"].append({
                                "id": msg_ui["id"], "user_id": msg_ui["user_id"], "username": msg_ui["user_id"],
                                "text": msg_ui["text"],
                                "timestamp": msg_ui["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                            })

                        # Check if the message is new (by timestamp and its direct ID) and not from the bot itself
                        if msg_ui["timestamp"] > last_ts_for_thread and msg_ui["id"] not in processed_message_ids:
                            if msg_ui["user_id"].lower() != BOT_ACTUAL_USERNAME.lower():
                                new_ui_messages_to_process.append(msg_ui)

                        # Update the latest message timestamp encountered in this cycle for this thread
                        if msg_ui["timestamp"] > latest_msg_timestamp_this_cycle:
                            latest_msg_timestamp_this_cycle = msg_ui["timestamp"]

                    if not new_ui_messages_to_process:
                        print(
                            f"No new messages to process in unread thread {thread_identifier} since {last_ts_for_thread.strftime('%H:%M')}. Unread indicator might be for older messages or bot's own.")
                        # Still update timestamp as we've "checked" it due to unread marker
                        last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
                        active_thread_identifier = None  # Clear active thread as we are done with this one
                        # Return to DM list before processing the next unread thread
                        if not u2_utils.return_to_dm_list_from_thread(d_device):
                            print(
                                f"WARN: Failed to return to DM list cleanly from thread {thread_identifier}. Attempting full nav.")
                            u2_utils.go_to_dm_list(d_device)
                        time.sleep(1)  # Small pause before next unread thread
                        continue  # To the next thread_identifier in unread_threads

                    # Process new messages found in this thread
                    if new_ui_messages_to_process:
                        # Consolidate message texts
                        consolidated_message_text_ui = "\n".join(
                            [msg["text"] for msg in new_ui_messages_to_process])

                        # Get context from the last message in the batch
                        last_message_data = new_ui_messages_to_process[-1]
                        sender_username_ui = last_message_data["user_id"]
                        timestamp_approx_str = last_message_data["timestamp"].strftime(
                            "%Y-%m-%d %H:%M:%S")
                        sender_full_name_ui = "Unknown (UI)"
                        sender_follower_count_ui = 0  # Placeholder

                        print(
                            f"Processing batch of {len(new_ui_messages_to_process)} new UI DMs in {thread_identifier} from {sender_username_ui}. Consolidated text: {consolidated_message_text_ui[:100]}...")

                        # Check if auto-response is paused for this thread (using last message for keyword check)
                        if not auto_responding.get(thread_identifier, True):
                            if last_message_data["text"] and any(
                                    k_word in last_message_data["text"].lower() for k_word in ["resume", "start", "unpause"]):
                                auto_responding[thread_identifier] = True
                                u2_utils.send_dm_in_open_thread(d_device,
                                                                f"{BOT_DISPLAY_NAME}: Auto-response R E S U M E D for {thread_identifier}.")
                                print(
                                    f"Auto-response resumed for {thread_identifier} based on keyword in last message.")
                                for msg_data_item in new_ui_messages_to_process:  # Mark all as processed
                                    processed_message_ids.add(
                                        msg_data_item["id"])
                                last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
                                if not u2_utils.return_to_dm_list_from_thread(d_device):
                                    u2_utils.go_to_dm_list(d_device)
                                active_thread_identifier = None
                                time.sleep(random.randint(1, 2))
                                continue  # To the next unread thread
                            else:
                                print(
                                    f"Auto-response paused for {thread_identifier}. Skipping batch.")
                                for msg_data_item in new_ui_messages_to_process:  # Mark all as processed
                                    processed_message_ids.add(
                                        msg_data_item["id"])
                                last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
                                if not u2_utils.return_to_dm_list_from_thread(d_device):
                                    u2_utils.go_to_dm_list(d_device)
                                active_thread_identifier = None
                                time.sleep(random.randint(1, 2))
                                continue  # To the next unread thread

                        # Build prompt history for Gemini
                        prompt_history = []
                        sorted_thread_msgs = sorted(
                            all_threads_history[thread_identifier]["messages"], key=lambda x: x["timestamp"])
                        # Build history from messages *before* the current batch
                        # Get last 10 messages from history
                        for hist_msg in sorted_thread_msgs[-10:]:
                            # Check if this historical message is one of the new messages we are about to process
                            is_part_of_current_batch = any(
                                new_msg["id"] == hist_msg["id"] for new_msg in new_ui_messages_to_process)
                            if not is_part_of_current_batch:
                                role = "User" if hist_msg["username"].lower(
                                ) != BOT_ACTUAL_USERNAME.lower() else BOT_DISPLAY_NAME
                                prompt_history.append(
                                    f"{role} ({hist_msg['username']}): {hist_msg['text']}")

                        # Add the consolidated new message(s) from the user to the prompt history
                        current_msg_in_prompt = f"User ({sender_username_ui}): {consolidated_message_text_ui}"
                        prompt_history.append(current_msg_in_prompt)
                        history_text_for_llm = "\n".join(prompt_history)

                        # First pass to Gemini
                        prompt_first = format_message_for_llm(
                            PROMPT_FIRST_TEMPLATE,
                            bot_display_name=BOT_DISPLAY_NAME, bot_actual_username=BOT_ACTUAL_USERNAME,
                            owner_username=OWNER_USERNAME, current_date=datetime.now().strftime('%Y-%m-%d'),
                            sender_username=sender_username_ui, thread_id=thread_identifier,
                            sender_full_name=sender_full_name_ui, timestamp=timestamp_approx_str,
                            sender_follower_count=sender_follower_count_ui, history_text=history_text_for_llm,
                            message_text=consolidated_message_text_ui  # Use consolidated message
                        )
                        print(
                            f"Sending consolidated message to Gemini (1st pass) for {thread_identifier}...")
                        try:
                            response_first = chat_session.send_message(
                                prompt_first)
                        except Exception as e:
                            print(
                                f"ERROR: Gemini API (1st pass) failed for {thread_identifier} with consolidated message: {e}")
                            for msg_data_item in new_ui_messages_to_process:  # Mark all as processed
                                processed_message_ids.add(msg_data_item["id"])
                            last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
                            if not u2_utils.return_to_dm_list_from_thread(d_device):
                                u2_utils.go_to_dm_list(d_device)
                            active_thread_identifier = None
                            time.sleep(random.randint(1, 2))
                            continue  # To the next unread thread

                        function_triggered_this_message = False
                        llm_args_for_second_prompt = {}
                        llm_function_name = None

                        # Handle Gemini's response (function call or direct text)
                        for part in response_first.parts:
                            if part.function_call:
                                function_triggered_this_message = True
                                func_call = part.function_call
                                llm_function_name = func_call.name
                                llm_args_for_second_prompt = dict(
                                    func_call.args)
                                print(
                                    f"LLM requested function: {llm_function_name} with args: {llm_args_for_second_prompt}")

                                # --- Handle Function Calls via UI ---
                                if llm_function_name == "notify_owner":
                                    original_ctx = {"thread_id": thread_identifier,
                                                    "sender_username": sender_username_ui,
                                                    "timestamp": timestamp_approx_str}
                                    send_message_to_owner_via_ui(
                                        llm_args_for_second_prompt.get(
                                            "message", "LLM requested owner notification."),
                                        original_ctx)
                                    llm_args_for_second_prompt[
                                        "details_for_user"] = f"I've notified my owner, {OWNER_USERNAME}."
                                elif llm_function_name == "send_message":
                                    msg_to_send = llm_args_for_second_prompt.get(
                                        "message")
                                    target_user = llm_args_for_second_prompt.get(
                                        "target_username")
                                    target_thread_id_from_llm = llm_args_for_second_prompt.get(
                                        "thread_id")  # Renamed to avoid clash
                                    actual_target = target_user or target_thread_id_from_llm
                                    success_send = False
                                    if msg_to_send and actual_target:
                                        # If target is different from current open thread
                                        if actual_target.lower() != active_thread_identifier.lower():
                                            # Need to switch context
                                            if not u2_utils.search_and_open_dm_with_user(d_device, actual_target,
                                                                                         BOT_ACTUAL_USERNAME):
                                                llm_args_for_second_prompt[
                                                    "details_for_user"] = f"I tried to message {actual_target} but couldn't find or open the chat."
                                            else:
                                                active_thread_identifier = actual_target  # Switched context
                                                success_send = u2_utils.send_dm_in_open_thread(
                                                    d_device, msg_to_send)
                                        else:  # Target is the currently open thread
                                            success_send = u2_utils.send_dm_in_open_thread(
                                                d_device, msg_to_send)

                                        if success_send:
                                            llm_args_for_second_prompt[
                                                "details_for_user"] = f"I've sent your requested message to {actual_target}."
                                        # If sending failed even if chat was opened (or was already open)
                                        else:
                                            llm_args_for_second_prompt[
                                                "details_for_user"] = f"I tried to send a message to {actual_target}, but it failed."

                                        # IMPORTANT: If we switched context, switch back to original thread to continue processing its messages
                                        if active_thread_identifier.lower() != thread_identifier.lower():
                                            if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                                active_thread_identifier = thread_identifier  # Switched back
                                            else:
                                                print(
                                                    f"CRITICAL ERROR: Failed to switch back to original thread {thread_identifier} after sending message to {actual_target}. Further processing for this thread might be compromised.")
                                                critical_context_switch_error = True  # Set flag
                                                # No need to add to processed_message_ids here, it's done after LLM handling
                                                break  # Break from 'for part in response_first.parts'
                                    else:  # msg_to_send or actual_target was missing
                                        llm_args_for_second_prompt[
                                            "details_for_user"] = "I was asked to send a message, but the target or message was unclear."

                                elif llm_function_name == "fetch_followers_followings":
                                    target_fetch_user = llm_args_for_second_prompt.get(
                                        "target_username")
                                    llm_args_for_second_prompt[
                                        "details_for_user"] = f"Fetching followers/followings for {target_fetch_user} via UI is complex and slow. This feature is currently stubbed for UI automation."
                                    print(
                                        f"STUB: UI fetch_followers_followings for {target_fetch_user}")
                                # Add other function handlers here if needed

                            elif part.text:  # Direct text reply from LLM
                                reply_text = format_message_for_llm(part.text.strip(),
                                                                    bot_display_name=BOT_DISPLAY_NAME,
                                                                    bot_actual_username=BOT_ACTUAL_USERNAME)
                                print(
                                    f"LLM direct reply for {thread_identifier}: {reply_text[:50]}...")
                                if active_thread_identifier.lower() == thread_identifier.lower():  # Ensure we are in the correct thread
                                    u2_utils.send_dm_in_open_thread(
                                        d_device, reply_text)
                                else:
                                    # This case should ideally not happen if context switching for send_message is correct
                                    print(
                                        f"ERROR: Attempted direct reply but active thread '{active_thread_identifier}' doesn't match target '{thread_identifier}'. Re-opening target.")
                                    if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                        active_thread_identifier = thread_identifier
                                        u2_utils.send_dm_in_open_thread(
                                            d_device, reply_text)
                                    else:
                                        print(
                                            f"ERROR: Could not re-open {thread_identifier} to send LLM direct reply. Message lost.")

                        # If a function was called, send a second prompt to Gemini for user-facing explanation
                        if function_triggered_this_message and llm_function_name:
                            function_execution_summary = llm_args_for_second_prompt.get("details_for_user",
                                                                                        "I performed an action based on your message.")
                            prompt_second = format_message_for_llm(
                                PROMPT_SECOND_TEMPLATE,
                                bot_display_name=BOT_DISPLAY_NAME, bot_actual_username=BOT_ACTUAL_USERNAME,
                                sender_username=sender_username_ui, message_text=consolidated_message_text_ui,  # Consolidated
                                thread_id=thread_identifier, function_name=llm_function_name,
                                function_message_placeholder=function_execution_summary if llm_function_name == "notify_owner" else "",
                                send_message_placeholder=function_execution_summary if llm_function_name == "send_message" else "",
                                fetched_data_placeholder=function_execution_summary if llm_function_name == "fetch_followers_followings" else "",
                                sender_full_name=sender_full_name_ui, timestamp=timestamp_approx_str,
                                sender_follower_count=sender_follower_count_ui, owner_username=OWNER_USERNAME
                            )
                            try:
                                response_second = chat_session.send_message(
                                    prompt_second)
                                for part_second in response_second.parts:
                                    if part_second.text:
                                        user_explanation = format_message_for_llm(part_second.text.strip(),
                                                                                  bot_display_name=BOT_DISPLAY_NAME,
                                                                                  bot_actual_username=BOT_ACTUAL_USERNAME)
                                        if active_thread_identifier.lower() == thread_identifier.lower():  # Ensure correct thread
                                            u2_utils.send_dm_in_open_thread(
                                                d_device, user_explanation)
                                        else:  # Should not happen if context management is correct
                                            print(
                                                f"ERROR: Attempted 2nd pass reply but active thread '{active_thread_identifier}' doesn't match target '{thread_identifier}'. Re-opening.")
                                            if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                                active_thread_identifier = thread_identifier
                                                u2_utils.send_dm_in_open_thread(
                                                    d_device, user_explanation)
                                            else:
                                                print(
                                                    f"ERROR: Could not re-open {thread_identifier} for 2nd pass. Explanation lost.")
                            except Exception as e:
                                print(
                                    f"ERROR: Gemini API (2nd pass) failed for {thread_identifier} with consolidated message: {e}")

                        # Mark all messages in the processed batch as processed_message_ids
                        for msg_data_item in new_ui_messages_to_process:
                            processed_message_ids.add(msg_data_item["id"])

                        if critical_context_switch_error:
                            print(
                                f"Critical context switch error occurred for thread {thread_identifier}. Skipping to next thread if any.")
                            # Timestamp already updated before this check. Attempt to go to DM list.
                            if not u2_utils.return_to_dm_list_from_thread(d_device):
                                u2_utils.go_to_dm_list(d_device)
                            active_thread_identifier = None
                            time.sleep(random.randint(1, 2))
                            continue  # To the next thread_identifier

                    # End of 'if new_ui_messages_to_process:'
                    last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
                    print(
                        f"Finished checks for unread thread {thread_identifier}. Last check updated to {latest_msg_timestamp_this_cycle.strftime('%H:%M')}")

                    if not u2_utils.return_to_dm_list_from_thread(d_device):
                        print(
                            f"WARN: Failed to return to DM list cleanly from thread {thread_identifier} after processing. Attempting full nav.")
                        u2_utils.go_to_dm_list(d_device)
                    active_thread_identifier = None
                    time.sleep(random.randint(1, 3))

                # End of 'for thread_identifier in unread_threads:'
                sleep_after_cycle = False  # Processed DMs, so quick re-check

            else:  # No unread_threads found by blue dot
                print("No unread DMs detected by blue dot.")
                # Sleep for the configured interval when no unread DMs are found.
                print(
                    f"Sleeping for {BLUE_DOT_CHECK_INTERVAL} seconds (no unread DMs).")
                time.sleep(BLUE_DOT_CHECK_INTERVAL)
                sleep_after_cycle = False  # Already slept, no need for the end-of-cycle long sleep

        except Exception as e:
            print(
                f"!!!!!!!!!! MAJOR ERROR IN UI AUTO-RESPOND LOOP !!!!!!!!!!: {e}")
            import traceback
            traceback.print_exc()
            try:
                print(
                    "Attempting to recover UI state by ensuring Instagram is open and going to DM list...")
                u2_utils.ensure_instagram_open(d_device)
                u2_utils.go_to_dm_list(d_device)
                active_thread_identifier = None  # Reset active thread context
            except Exception as e2:
                print(
                    f"Failed to recover UI state during error handling: {e2}. Stopping app as a last resort.")
                # Consider d_device.app_stop("com.instagram.android") here if errors persist critically
                # For now, we'll let the main loop try again after a sleep.
            # sleep_after_cycle is already True by default, so a long sleep will occur.

        # This will be True if an exception occurred, or if initial nav failed.
        if sleep_after_cycle:
            # The role of MIN_SLEEP_TIME/MAX_SLEEP_TIME is now primarily for recovery after errors,
            # or if the very first go_to_dm_list in a cycle fails.
            # Normal "no unread DMs" scenario has its own 10s sleep.
            sleep_duration = random.randint(MIN_SLEEP_TIME, MAX_SLEEP_TIME)
            print(
                f"Sleeping for {sleep_duration} seconds (long interval, typically after an error or initial nav failure).")
            time.sleep(sleep_duration)


def graceful_exit(signum, frame):
    global d_device
    print("\nSIGINT received, shutting down UI automator...")
    if d_device:
        try:
            # Optional: Try to navigate to home or stop app
            # u2_utils.go_to_home(d_device)
            # d_device.app_stop("com.instagram.android")
            print("UI automation actions on exit (if any) complete.")
        except Exception as e:
            print(f"Error during exit cleanup: {e}")
    exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, graceful_exit)

    try:
        print(
            f"Attempting to connect to uiautomator2 device: {d_device_identifier}...")
        if not d_device_identifier:
            raise Exception(
                "Multiple ADB devices detected, but no specific 'd_device_identifier' was set in the script.")

        d_device = u2.connect(d_device_identifier)

        if not d_device:  # Should not happen if connect is successful, but good to check
            raise Exception("u2.connect() returned None, connection failed.")

        # REMOVE or COMMENT OUT d_device.healthcheck()
        # d_device.healthcheck()

        # Instead of healthcheck, try a simple operation like getting device info or window size
        # This will implicitly check if the connection is working.
        device_info = d_device.device_info
        if not device_info:  # Check if device_info is valid
            raise Exception(
                "Failed to get device_info after connect. Connection might be unstable.")

        print(
            f"Successfully connected to: {device_info.get('model', 'Unknown Model')} (Serial: {device_info.get('serial', 'N/A')})")
        # This also tests the connection
        print(f"Screen resolution: {d_device.window_size()}")

    except Exception as e:
        print(f"FATAL: Could not connect to uiautomator2 device. Error: {e}")
        print("Please ensure:")
        print("1. Your target Android device/emulator is listed in `adb devices`.")
        print(
            "2. `atx-agent` is running on the target device (run `python -m uiautomator2 init --serial YOUR_TARGET_DEVICE_ID` if needed).")
        print("3. If connecting via WiFi, both your computer and device are on the same network,")
        print(
            "   and the device identifier (IP:PORT or mDNS name) is correct and reachable.")
        print(
            f"4. You've set 'd_device_identifier' correctly in the script (currently: '{d_device_identifier}').")
        exit(1)

    # Call login_ui() *before* print_bot_user_info_ui()
    if not login_ui():
        print("FATAL: login_ui failed. Exiting.")
        exit(1)

    print_bot_user_info_ui()  # Print some info about the bot account

    print("\nStarting Instagram DM Bot with UI Automation (uiautomator2)...")
    auto_respond_via_ui()
