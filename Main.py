import uiautomator2 as u2
import time
import random
import signal
from datetime import datetime, timedelta

from config import (API_KEY, OWNER_USERNAME, PROMPT_FIRST_TEMPLATE, PROMPT_SECOND_TEMPLATE,
                    bot_instagram_username, BOT_DISPLAY_NAME, MESSAGE_FETCH_AMOUNT,
                    MIN_SLEEP_TIME, MAX_SLEEP_TIME, BLUE_DOT_CHECK_INTERVAL, DEVICE_IDENTIFIER
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

tools = Tool(function_declarations=[
    notify_owner_func,
    send_message_func,
    fetch_followers_followings
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
                    critical_context_switch_error = False
                    if thread_identifier.lower() == BOT_ACTUAL_USERNAME.lower():
                        print(f"Skipping unread indicator in own chat ({thread_identifier}).")
                        continue

                    print(f"\nProcessing unread UI Thread: {thread_identifier}")

                    if thread_identifier not in auto_responding:
                        auto_responding[thread_identifier] = True
                    if thread_identifier not in all_threads_history:
                        all_threads_history[thread_identifier] = {
                            "users": [thread_identifier, BOT_ACTUAL_USERNAME],
                            "messages": [],
                            "processed_stable_ids": set()  # Initialize here
                        }
                    last_ts_for_thread = last_checked_timestamps.get(thread_identifier, start_time - timedelta(hours=1))

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
                    if "processed_stable_ids" not in all_threads_history[thread_identifier]:  # Ensure initialization
                        all_threads_history[thread_identifier]["processed_stable_ids"] = set()

                    for msg_ui in messages_in_thread_ui:
                        if msg_ui["timestamp"] > latest_msg_timestamp_this_cycle:
                            latest_msg_timestamp_this_cycle = msg_ui["timestamp"]

                        stable_id = hash(str(msg_ui.get("user_id", "")) + str(msg_ui.get("text", "")))

                        if stable_id not in all_threads_history[thread_identifier]["processed_stable_ids"]:
                            all_threads_history[thread_identifier]["processed_stable_ids"].add(stable_id)

                            history_entry = {
                                "id": msg_ui["id"],
                                "stable_id_for_history": stable_id,
                                "user_id": msg_ui["user_id"],
                                "username": msg_ui["user_id"],
                                "text": msg_ui["text"],
                                "timestamp": msg_ui["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                            }
                            all_threads_history[thread_identifier]["messages"].append(history_entry)
                            if msg_ui["user_id"].lower() != BOT_ACTUAL_USERNAME.lower():
                                new_ui_messages_to_process.append(msg_ui)
                                processed_message_ids.add(msg_ui["id"])


                    last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle

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

                        if not auto_responding.get(thread_identifier, True):
                            if last_message_data["text"] and any(
                                    k_word in last_message_data["text"].lower() for k_word in
                                    ["resume", "start", "unpause"]):
                                auto_responding[thread_identifier] = True
                                resume_message = f"{BOT_DISPLAY_NAME}: Auto-response R E S U M E D for {thread_identifier}."
                                if u2_utils.send_dm_in_open_thread(d_device, resume_message):
                                    bot_sent_message_hashes.add(hash(resume_message))
                                    _perform_back_press(d_device)
                                    active_thread_identifier = None
                                print(
                                    f"Auto-response resumed for {thread_identifier} based on keyword in last message.")
                                for msg_data_item in new_ui_messages_to_process: processed_message_ids.add(
                                    msg_data_item["id"])
                                last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
                                if not u2_utils.return_to_dm_list_from_thread(d_device): u2_utils.go_to_dm_list(
                                    d_device)
                                active_thread_identifier = None
                                time.sleep(random.randint(1, 2))
                                continue
                            else:
                                print(f"Auto-response paused for {thread_identifier}. Skipping batch.")
                                for msg_data_item in new_ui_messages_to_process: processed_message_ids.add(
                                    msg_data_item["id"])
                                last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
                                if not u2_utils.return_to_dm_list_from_thread(d_device): u2_utils.go_to_dm_list(
                                    d_device)
                                active_thread_identifier = None
                                time.sleep(random.randint(1, 2))
                                continue

                        prompt_history_lines = []
                        current_full_thread_history = all_threads_history[thread_identifier]["messages"]
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
                            last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
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

                                if new_stable_id not in all_threads_history[thread_identifier][
                                    "processed_stable_ids"] and \
                                        msg_new_check["user_id"].lower() != BOT_ACTUAL_USERNAME.lower():

                                    genuinely_new_messages.append(msg_new_check)
                                    all_threads_history[thread_identifier]["processed_stable_ids"].add(new_stable_id)
                                    processed_message_ids.add(msg_new_check["id"])

                                    new_history_entry = {
                                        "id": msg_new_check["id"],
                                        "stable_id_for_history": new_stable_id,
                                        "user_id": msg_new_check["user_id"],
                                        "username": msg_new_check["user_id"],
                                        "text": msg_new_check["text"],
                                        "timestamp": msg_new_check["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    all_threads_history[thread_identifier]["messages"].append(new_history_entry)
                                    if msg_new_check["timestamp"] > latest_msg_timestamp_this_cycle:
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
                                                                                               message_with_sender)
                                                if success_send:
                                                    bot_sent_message_hashes.add(hash(message_with_sender))
                                                    _perform_back_press(d_device)  # Go back to DM list
                                                    active_thread_identifier = None  # We are no longer in actual_target's chat
                                                    print(
                                                        f"INFO: Returned to DM list after sending to {actual_target}. Active context reset to None.")
                                        else:  # Sending to the current active thread
                                            success_send = u2_utils.send_dm_in_open_thread(d_device,
                                                                                           message_with_sender)
                                            if success_send:
                                                bot_sent_message_hashes.add(hash(message_with_sender))
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
                                elif llm_function_name == "fetch_followers_followings":
                                    target_fetch_user = llm_args_for_second_prompt.get("target_username")
                                    llm_args_for_second_prompt[
                                        "details_for_user"] = f"Fetching followers/followings for {target_fetch_user} via UI is complex and slow. This feature is currently stubbed for UI automation."
                                    print(f"STUB: UI fetch_followers_followings for {target_fetch_user}")

                            elif part.text:  # Direct text reply from LLM
                                reply_text = format_message_for_llm(part.text.strip(),
                                                                    bot_display_name=BOT_DISPLAY_NAME,
                                                                    bot_actual_username=BOT_ACTUAL_USERNAME)
                                print(f"LLM direct reply for {thread_identifier}: {reply_text[:50]}...")
                                message_sent_successfully = False
                                if active_thread_identifier and active_thread_identifier.lower() == thread_identifier.lower():
                                    if u2_utils.send_dm_in_open_thread(d_device, reply_text):
                                        message_sent_successfully = True
                                        if message_sent_successfully:
                                            bot_sent_message_hashes.add(hash(reply_text))
                                else:  # Should not happen if send_message context switch is handled correctly
                                    print(
                                        f"LLM direct reply: Active thread is '{active_thread_identifier}', target is '{thread_identifier}'. Re-opening target.")
                                    if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                        active_thread_identifier = thread_identifier
                                        if u2_utils.send_dm_in_open_thread(d_device, reply_text):
                                            message_sent_successfully = True
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
                                            bot_sent_message_hashes.add(hash(user_explanation))
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

                    last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
                    print(
                        f"Finished checks for unread thread {thread_identifier}. Last check updated to {latest_msg_timestamp_this_cycle.strftime('%H:%M')}")

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
        print(f"Screen resolution: {d_device.window_size()}")

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
