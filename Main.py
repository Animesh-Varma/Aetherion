import uiautomator2 as u2
import time
import random
import signal
from datetime import datetime, timedelta
from config import (API_KEY, OWNER_USERNAME, PROMPT_FIRST_TEMPLATE, PROMPT_SECOND_TEMPLATE,
                    BOT_NAME, THREAD_FETCH_AMOUNT, MESSAGE_FETCH_AMOUNT,
                    MIN_SLEEP_TIME, MAX_SLEEP_TIME)  # SESSION_ID removed
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

import uiautomator2_utils as u2_utils  # Our new helper

# --- uiautomator2 Device Connection ---
# USER: Configure your device connection here
# d = u2.connect() # Default: first USB device or emulator
d_device_identifier = "192.168.29.251:43369"
# d = u2.connect_usb("YOUR_DEVICE_SERIAL")
# For this script, we assume 'd' is initialized globally after successful connection.
d_device = None  # Will be initialized in __main__

# --- Global Variables ---
BOT_ACTUAL_USERNAME = BOT_NAME  # Initial assumption, verified in login_ui
auto_responding = {}  # Key: thread_identifier (peer_username/group_name), Value: bool
genai.configure(api_key=API_KEY)
start_time = datetime.now()
last_checked_timestamps = {}  # Key: thread_identifier, Value: datetime object
all_threads_history = {}  # Key: thread_identifier, Value: {"users": [usernames], "messages": []}
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
model = genai.GenerativeModel("gemini-1.5-flash-latest", tools=tools)  # Or your preferred model


def format_message_for_llm(template_string: str, **kwargs) -> str:
    for key, value in kwargs.items():
        template_string = template_string.replace(f"[[{key}]]", str(value))
    return template_string


def send_message_to_owner_via_ui(message_body, original_context):
    global d_device, BOT_ACTUAL_USERNAME
    if not OWNER_USERNAME:
        print("ERROR: OWNER_USERNAME not configured.")
        return

    full_message_to_owner = (f"Raphael ({BOT_ACTUAL_USERNAME}) Update for Master {OWNER_USERNAME}:\n"
                             f"{message_body}\n---Original Context---\n"
                             f"Thread: {original_context.get('thread_id', 'N/A')}\n"
                             f"Sender: {original_context.get('sender_username', 'N/A')}\n"
                             f"Timestamp: {original_context.get('timestamp', 'N/A')}\n")

    print(f"Attempting to send to owner ({OWNER_USERNAME}) via UI: {full_message_to_owner[:100]}...")
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
    profile_info = u2_utils.get_bot_profile_info(d_device, BOT_NAME)  # BOT_NAME from config is initial guess
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

    print(f"UI 'Login' complete. Bot Username: {BOT_ACTUAL_USERNAME}, Owner: {OWNER_USERNAME}")
    u2_utils.go_to_dm_list(d_device)  # End in DM list
    return True


def print_bot_user_info_ui():
    global d_device, BOT_ACTUAL_USERNAME
    print(f"\n--- Bot ({BOT_ACTUAL_USERNAME}) Profile Info (UI Scraped) ---")
    info = u2_utils.get_bot_profile_info(d_device, BOT_ACTUAL_USERNAME)  # Re-scrape or use stored if available
    print(f"  Username: {info.get('username', BOT_ACTUAL_USERNAME)}")
    print(f"  Full Name: {info.get('full_name', 'N/A')}")
    print(f"  Biography: {info.get('biography', 'N/A')}")
    print(f"  Followers: {info.get('follower_count', 'N/A')}")
    u2_utils.go_to_dm_list(d_device)  # Return to DMs


def auto_respond_via_ui():
    global d_device, auto_responding, last_checked_timestamps, processed_message_ids, all_threads_history, BOT_ACTUAL_USERNAME

    if not BOT_ACTUAL_USERNAME:
        print("CRITICAL: Bot username not determined. Cannot start auto-responder. Run login_ui first.")
        return

    chat_session = model.start_chat(history=[])  # Gemini chat session

    while True:
        try:
            print(f"\n--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} --- UI Bot Cycle ---")
            if not u2_utils.go_to_dm_list(d_device):
                print("Failed to navigate to DM list. Retrying after sleep.")
                time.sleep(60)
                continue

            # Fetch thread summaries from UI
            # This gets currently visible threads, potentially with some scrolling.
            # Thread "id" from u2_utils is the peer_username or group_name.
            threads_on_screen = u2_utils.get_threads_from_dm_list(d_device, BOT_ACTUAL_USERNAME, THREAD_FETCH_AMOUNT)

            if not threads_on_screen:
                print("No threads found on DM screen or failed to fetch.")
                time.sleep(random.randint(MIN_SLEEP_TIME, MAX_SLEEP_TIME))
                continue

            active_thread_identifier = None  # To track which thread is currently open

            for thread_summary in threads_on_screen:
                thread_identifier = thread_summary["id"]  # Peer username or group name
                if thread_identifier.lower() == BOT_ACTUAL_USERNAME.lower(): continue

                print(f"\nProcessing UI Thread: {thread_identifier}")

                # Initialize states for this thread if new
                if thread_identifier not in auto_responding: auto_responding[thread_identifier] = True
                if thread_identifier not in all_threads_history:
                    all_threads_history[thread_identifier] = {"users": thread_summary["users"], "messages": []}

                last_ts_for_thread = last_checked_timestamps.get(thread_identifier, start_time - timedelta(
                    hours=1))  # Check for recent messages

                # Open the specific thread
                if not u2_utils.open_thread_by_username(d_device, thread_identifier):
                    print(f"Could not open thread for {thread_identifier}. Skipping.")
                    active_thread_identifier = None
                    u2_utils.go_to_dm_list(d_device)  # Ensure back in DM list
                    continue
                active_thread_identifier = thread_identifier  # Mark thread as open

                # Get messages from the OPENED thread
                # Timestamps from UI are approximations (fetch time)
                messages_in_thread_ui = u2_utils.get_messages_from_open_thread(d_device, BOT_ACTUAL_USERNAME,
                                                                               MESSAGE_FETCH_AMOUNT)

                # Update history and find new messages
                latest_msg_timestamp_this_cycle = last_ts_for_thread
                new_ui_messages_to_process = []

                for msg_ui in messages_in_thread_ui:
                    # Create a unique ID for UI message to check if processed
                    # msg_ui["user_id"] is the SENDER username from UI
                    ui_msg_tuple_id = (msg_ui["text"], msg_ui["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                       msg_ui["user_id"])

                    # Add to history if not already there (based on simple check)
                    is_in_history = any(
                        h_msg["id"] == msg_ui["id"] for h_msg in all_threads_history[thread_identifier]["messages"])
                    if not is_in_history:
                        all_threads_history[thread_identifier]["messages"].append({
                            "id": msg_ui["id"],  # UI hash
                            "user_id": msg_ui["user_id"],
                            "username": msg_ui["user_id"],  # SENDER from UI
                            "text": msg_ui["text"],
                            "timestamp": msg_ui["timestamp"].strftime("%Y-%m-%d %H:%M:%S")  # Approx
                        })

                    if msg_ui["timestamp"] > last_ts_for_thread and ui_msg_tuple_id not in processed_message_ids:
                        if msg_ui["user_id"].lower() != BOT_ACTUAL_USERNAME.lower():  # Not bot's own message
                            new_ui_messages_to_process.append(msg_ui)

                    if msg_ui["timestamp"] > latest_msg_timestamp_this_cycle:
                        latest_msg_timestamp_this_cycle = msg_ui["timestamp"]

                if not new_ui_messages_to_process:
                    print(
                        f"No new messages to process in thread {thread_identifier} since {last_ts_for_thread.strftime('%H:%M')}")
                    last_checked_timestamps[
                        thread_identifier] = latest_msg_timestamp_this_cycle  # Update even if no new ones *to process*
                    active_thread_identifier = None
                    u2_utils.go_to_dm_list(d_device)  # Go back before next thread in outer loop
                    time.sleep(1)
                    continue

                # Process new messages
                for message_data in new_ui_messages_to_process:
                    ui_msg_tuple_id_for_processing = (message_data["text"],
                                                      message_data["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                                      message_data["user_id"])

                    if ui_msg_tuple_id_for_processing in processed_message_ids:  # Double check
                        continue

                    sender_username_ui = message_data["user_id"]  # Sender's username from UI
                    message_text_ui = message_data["text"]
                    timestamp_approx_str = message_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

                    # Placeholder for full name and follower count (hard to get via UI per message)
                    sender_full_name_ui = "Unknown (UI)"
                    sender_follower_count_ui = 0

                    print(f"New UI DM in {thread_identifier} from {sender_username_ui}: {message_text_ui[:40]}...")

                    # Auto-response pause check
                    if not auto_responding.get(thread_identifier, True):
                        print(f"Auto-response paused for {thread_identifier}. Checking for resume cmd.")
                        if message_text_ui and any(
                                k_word in message_text_ui.lower() for k_word in ["resume", "start", "unpause"]):
                            auto_responding[thread_identifier] = True
                            u2_utils.send_dm_in_open_thread(d_device,
                                                            f"Raphael: Auto-response resumed for {thread_identifier}.")
                            print(f"Auto-response resumed for {thread_identifier}.")
                            processed_message_ids.add(ui_msg_tuple_id_for_processing)
                        continue  # Skip LLM processing if paused

                    # Acknowledge (optional, can be chatty)
                    # u2_utils.send_dm_in_open_thread(d_device, "Raphael is processing...")

                    # Build conversation history for LLM
                    # Use the more structured all_threads_history
                    prompt_history = []
                    sorted_thread_msgs = sorted(all_threads_history[thread_identifier]["messages"],
                                                key=lambda x: x["timestamp"])
                    for hist_msg in sorted_thread_msgs[-10:]:  # Last 10 messages for context
                        role = "User" if hist_msg["username"].lower() != BOT_ACTUAL_USERNAME.lower() else "Raphael"
                        prompt_history.append(f"{role} ({hist_msg['username']}): {hist_msg['text']}")

                    # Ensure current message is last if not captured by history scrape (unlikely if sorted)
                    current_msg_in_prompt = f"User ({sender_username_ui}): {message_text_ui}"
                    if not prompt_history or prompt_history[-1] != current_msg_in_prompt:
                        prompt_history.append(current_msg_in_prompt)

                    history_text_for_llm = "\n".join(prompt_history)

                    # --- Call Gemini API (First Pass) ---
                    prompt_first = format_message_for_llm(
                        PROMPT_FIRST_TEMPLATE,
                        bot_username_in_context=BOT_ACTUAL_USERNAME, owner_username=OWNER_USERNAME,
                        current_date=datetime.now().strftime('%Y-%m-%d'), sender_username=sender_username_ui,
                        thread_id=thread_identifier, sender_full_name=sender_full_name_ui,
                        timestamp=timestamp_approx_str, sender_follower_count=sender_follower_count_ui,
                        history_text=history_text_for_llm, message_text=message_text_ui
                    )

                    print(f"Sending to Gemini (1st pass) for {thread_identifier}...")
                    try:
                        response_first = chat_session.send_message(prompt_first)
                    except Exception as e:
                        print(f"ERROR: Gemini API (1st pass) failed for {thread_identifier}: {e}")
                        processed_message_ids.add(ui_msg_tuple_id_for_processing)
                        continue

                    # --- Process Gemini Response (Function Calls or Text Reply) ---
                    function_triggered_this_message = False
                    llm_args_for_second_prompt = {}
                    llm_function_name = None

                    for part in response_first.parts:
                        if part.function_call:
                            function_triggered_this_message = True
                            func_call = part.function_call
                            llm_function_name = func_call.name
                            llm_args_for_second_prompt = dict(func_call.args)  # Store args
                            print(
                                f"LLM requested function: {llm_function_name} with args: {llm_args_for_second_prompt}")

                            # --- Handle Function Calls via UI ---
                            if llm_function_name == "notify_owner":
                                original_ctx = {"thread_id": thread_identifier, "sender_username": sender_username_ui,
                                                "timestamp": timestamp_approx_str}
                                send_message_to_owner_via_ui(
                                    llm_args_for_second_prompt.get("message", "LLM requested owner notification."),
                                    original_ctx)
                                # For the second prompt to user:
                                llm_args_for_second_prompt[
                                    "details_for_user"] = f"I've notified my owner, {OWNER_USERNAME}."

                            elif llm_function_name == "send_message":
                                msg_to_send = llm_args_for_second_prompt.get("message")
                                target_user = llm_args_for_second_prompt.get("target_username")
                                target_thread_id = llm_args_for_second_prompt.get(
                                    "thread_id")  # This is a peer username

                                actual_target = target_user or target_thread_id  # Prefer specific user if given
                                success_send = False
                                if msg_to_send and actual_target:
                                    print(f"Attempting LLM-requested send_message to '{actual_target}'")
                                    # If target is not current thread, need to navigate
                                    if actual_target.lower() != active_thread_identifier.lower():
                                        if not u2_utils.search_and_open_dm_with_user(d_device, actual_target,
                                                                                     BOT_ACTUAL_USERNAME):
                                            llm_args_for_second_prompt[
                                                "details_for_user"] = f"I tried to message {actual_target} but couldn't find or open the chat."
                                        else:  # Switched to new chat
                                            active_thread_identifier = actual_target  # Update active thread
                                            success_send = u2_utils.send_dm_in_open_thread(d_device, msg_to_send)
                                    else:  # Already in target thread
                                        success_send = u2_utils.send_dm_in_open_thread(d_device, msg_to_send)

                                    if success_send:
                                        llm_args_for_second_prompt[
                                            "details_for_user"] = f"I've sent your requested message to {actual_target}."
                                    else:
                                        llm_args_for_second_prompt[
                                            "details_for_user"] = f"I tried to send a message to {actual_target}, but it failed."

                                    # IMPORTANT: If we navigated away, navigate back to original thread to continue processing its messages
                                    if active_thread_identifier.lower() != thread_identifier.lower():
                                        print(f"Returning to original thread: {thread_identifier}")
                                        if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                            active_thread_identifier = thread_identifier
                                        else:  # Failed to return, big problem
                                            print(
                                                f"CRITICAL: Failed to return to original thread {thread_identifier}. Halting this thread's processing.")
                                            # Mark all subsequent messages in this thread as processed to avoid loop
                                            # Or break from inner loop. For now, let it try next message with messed up state.
                                            break  # Break from processing messages in THIS thread_summary
                                else:
                                    llm_args_for_second_prompt[
                                        "details_for_user"] = "I was asked to send a message, but the target or message was unclear."

                            # TODO: Implement other function handlers (pause, resume, target, list, view, fetch)
                            # fetch_followers_followings will be VERY slow and UI-dependent.
                            # Example for fetch_followers_followings (stubbed):
                            elif llm_function_name == "fetch_followers_followings":
                                target_fetch_user = llm_args_for_second_prompt.get("target_username")
                                llm_args_for_second_prompt[
                                    "details_for_user"] = f"Fetching followers/followings for {target_fetch_user} via UI is complex and slow. This feature is currently stubbed for UI automation."
                                print(f"STUB: UI fetch_followers_followings for {target_fetch_user}")


                        elif part.text:  # Direct text reply from LLM
                            reply_text = format_message_for_llm(part.text.strip(),
                                                                bot_username_in_context=BOT_ACTUAL_USERNAME)
                            print(f"LLM direct reply for {thread_identifier}: {reply_text[:50]}...")
                            if active_thread_identifier.lower() == thread_identifier.lower():  # Ensure still in correct thread
                                u2_utils.send_dm_in_open_thread(d_device, reply_text)
                            else:
                                print(
                                    f"WARN: Was about to reply in {thread_identifier}, but active thread is {active_thread_identifier}. Re-opening...")
                                if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                    active_thread_identifier = thread_identifier
                                    u2_utils.send_dm_in_open_thread(d_device, reply_text)
                                else:
                                    print(f"ERROR: Could not re-open {thread_identifier} to send LLM direct reply.")

                    # --- If function was called, send Second Prompt to LLM for user explanation ---
                    if function_triggered_this_message and llm_function_name:
                        # Use llm_args_for_second_prompt["details_for_user"]
                        function_execution_summary = llm_args_for_second_prompt.get("details_for_user",
                                                                                    "I performed an action based on your message.")

                        prompt_second = format_message_for_llm(
                            PROMPT_SECOND_TEMPLATE,
                            bot_username_in_context=BOT_ACTUAL_USERNAME, sender_username=sender_username_ui,
                            message_text=message_text_ui, thread_id=thread_identifier,
                            function_name=llm_function_name,
                            # Simplification: Pass the generated summary directly
                            function_message_placeholder=function_execution_summary if llm_function_name == "notify_owner" else "",
                            send_message_placeholder=function_execution_summary if llm_function_name == "send_message" else "",
                            fetched_data_placeholder=function_execution_summary if llm_function_name == "fetch_followers_followings" else "",
                            # Add other placeholders if needed, or make a generic one
                            # generic_function_result_placeholder=function_execution_summary,
                            sender_full_name=sender_full_name_ui, timestamp=timestamp_approx_str,
                            sender_follower_count=sender_follower_count_ui, owner_username=OWNER_USERNAME
                        )
                        print(f"Sending to Gemini (2nd pass) for {thread_identifier}...")
                        try:
                            response_second = chat_session.send_message(prompt_second)
                            for part_second in response_second.parts:
                                if part_second.text:
                                    user_explanation = format_message_for_llm(part_second.text.strip(),
                                                                              bot_username_in_context=BOT_ACTUAL_USERNAME)
                                    print(f"LLM explanation for {thread_identifier}: {user_explanation[:50]}...")
                                    if active_thread_identifier.lower() == thread_identifier.lower():  # Check if still in correct thread
                                        u2_utils.send_dm_in_open_thread(d_device, user_explanation)
                                    else:  # Re-open if necessary
                                        print(
                                            f"WARN: Was about to send explanation in {thread_identifier}, but active thread is {active_thread_identifier}. Re-opening...")
                                        if u2_utils.open_thread_by_username(d_device, thread_identifier):
                                            active_thread_identifier = thread_identifier
                                            u2_utils.send_dm_in_open_thread(d_device, user_explanation)
                                        else:
                                            print(
                                                f"ERROR: Could not re-open {thread_identifier} to send LLM explanation.")
                        except Exception as e:
                            print(f"ERROR: Gemini API (2nd pass) failed for {thread_identifier}: {e}")

                    processed_message_ids.add(ui_msg_tuple_id_for_processing)
                # End of processing messages in this thread
                last_checked_timestamps[thread_identifier] = latest_msg_timestamp_this_cycle
                print(
                    f"Finished processing new messages for {thread_identifier}. Last check updated to {latest_msg_timestamp_this_cycle.strftime('%H:%M')}")
                active_thread_identifier = None  # Reset active thread before next iteration of outer loop
                u2_utils.go_to_dm_list(d_device)  # Go back to DM list
                time.sleep(2)  # Small pause between threads

        except Exception as e:
            print(f"!!!!!!!!!! MAJOR ERROR IN UI AUTO-RESPOND LOOP !!!!!!!!!!: {e}")
            import traceback
            traceback.print_exc()
            # Attempt to recover UI state
            try:
                print("Attempting to recover UI state by going to DM list...")
                u2_utils.ensure_instagram_open(d_device)
                u2_utils.go_to_dm_list(d_device)
                active_thread_identifier = None
            except Exception as e2:
                print(f"Failed to recover UI state: {e2}. Stopping app as last resort.")
                d_device.app_stop("com.instagram.android")
                time.sleep(10)  # Wait longer if app had to be stopped

        sleep_duration = random.randint(MIN_SLEEP_TIME, MAX_SLEEP_TIME)
        print(f"Sleeping for {sleep_duration} seconds before next cycle.")
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
        print(f"Attempting to connect to uiautomator2 device: {d_device_identifier}...")
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
            raise Exception("Failed to get device_info after connect. Connection might be unstable.")

        print(
            f"Successfully connected to: {device_info.get('model', 'Unknown Model')} (Serial: {device_info.get('serial', 'N/A')})")
        print(f"Screen resolution: {d_device.window_size()}")  # This also tests the connection

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

    print_bot_user_info_ui()  # Print some info about the bot account

    print("\nStarting Instagram DM Bot with UI Automation (uiautomator2)...")
    auto_respond_via_ui()