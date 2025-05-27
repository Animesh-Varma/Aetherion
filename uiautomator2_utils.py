# uiautomator2_utils.py
# Helper functions for Instagram UI Automation.

import uiautomator2 as u2
import time
from datetime import datetime, timedelta

# --- Constants for Instagram UI Automation ---
# I. Main App Navigation Tabs
HOME_TAB_RESID = "com.instagram.android:id/feed_tab"
SEARCH_TAB_RESID = "com.instagram.android:id/search_tab"
CREATION_TAB_RESID = "com.instagram.android:id/creation_tab"
REELS_TAB_RESID = "com.instagram.android:id/clips_tab"
PROFILE_TAB_RESID = "com.instagram.android:id/profile_tab"

# II. DM (Direct Message) List Screen Elements
DM_INBOX_ICON_RESID = "com.instagram.android:id/action_bar_inbox_button"
DM_LIST_HEADER_TEXT_RESID = "com.instagram.android:id/action_bar_title_subtitle_container"  # Container for username/title
DM_LIST_SEARCH_ACTIVATION_ELEMENT_RESID = "com.instagram.android:id/animated_hints_text_layout"
DM_LIST_SEARCH_INPUT_FIELD_RESID = "com.instagram.android:id/row_thread_composer_edittext"  # This might be the container, actual EditText inside it.
DM_LIST_ACTUAL_SEARCH_EDITTEXT_RESID = "com.instagram.android:id/row_thread_composer_edittext"  # Often an EditText appears after activating search. Find its ID.

DM_THREAD_ITEM_CONTAINER_RESID = "com.instagram.android:id/row_inbox_container"
DM_THREAD_ITEM_USERNAME_TEXT_RESID = "com.instagram.android:id/row_inbox_username"
DM_THREAD_ITEM_SNIPPET_TEXT_RESID = "com.instagram.android:id/row_inbox_digest"
DM_THREAD_ITEM_TIMESTAMP_TEXT_RESID = "com.instagram.android:id/row_inbox_timestamp"
DM_THREAD_ITEM_UNREAD_INDICATOR_RESID = "com.instagram.android:id/thread_indicator_status_dot"

DM_LIST_NEW_CHAT_BUTTON_DESC = "New message"  # Using content-desc

# III. Inside an Active DM Chat/Thread Screen
DM_CHAT_HEADER_USERNAME_TEXT_RESID = "com.instagram.android:id/header_title"  # User confirmed this holds username in content-desc
DM_CHAT_MESSAGE_BUBBLE_CONTAINER_RESID = "com.instagram.android:id/direct_text_message_text_parent"
DM_CHAT_MESSAGE_TEXT_VIEW_RESID = "com.instagram.android:id/direct_text_message_text_view"
DM_CHAT_MESSAGE_SENDER_NAME_TEXT_RESID = "com.instagram.android:id/username"  # For groups
# Chosen primary candidate for message timestamp after evaluating alternatives.
# Fallback logic will be used if this ID fails.
DM_CHAT_MESSAGE_TIMESTAMP_TEXT_RESID = "com.instagram.android:id/message_time"

DM_CHAT_INPUT_FIELD_RESID = "com.instagram.android:id/row_thread_composer_edittext"
DM_CHAT_SEND_BUTTON_RESID = "com.instagram.android:id/row_thread_composer_send_button_container"

# IV. New Chat Screen (after tapping DM_LIST_NEW_CHAT_BUTTON_DESC)
NEW_CHAT_TO_FIELD_INPUT_RESID = "com.instagram.android:id/search_edit_text"  # The "To:" or "Search" EditText.
NEW_CHAT_USER_RESULT_ITEM_CONTAINER_RESID = "com.instagram.android:id/row_user_info_layout"
NEW_CHAT_USER_RESULT_USERNAME_TEXT_RESID = "com.instagram.android:id/row_user_secondary_name"  # User's @username
NEW_CHAT_USER_RESULT_FULLNAME_TEXT_RESID = "com.instagram.android:id/row_user_primary_name"  # User's full name
NEW_CHAT_USER_RESULT_SELECT_ELEMENT_RESID = "android.widget.FrameLayout"  # User provided FrameLayout. This is very generic. Might be the container itself or a specific child checkbox/radio.
# NEW_CHAT_USER_RESULT_SELECT_CHECKBOX_CLASS = "android.widget.CheckBox_TODO_NEW_CHAT" # If there's a specific checkbox class inside the container.

NEW_CHAT_CREATE_CHAT_BUTTON_TEXT = "Chat"  # Text on the button to finalize chat creation.
# NEW_CHAT_CREATE_CHAT_BUTTON_RESID = "com.instagram.android:id/next_button_TODO_NEW_CHAT" # Or look for its resource-id

# V. User Profile Screen
PROFILE_USERNAME_HEADER_TEXT_RESID = "com.instagram.android:id/action_bar_title"  # Username at the top of profile.
PROFILE_FULL_NAME_TEXT_RESID = "com.instagram.android:id/profile_header_full_name_above_vanity"
PROFILE_BIO_TEXT_RESID = "com.instagram.android:id/profile_header_bio_text"
PROFILE_FOLLOWER_COUNT_TEXT_RESID = "com.instagram.android:id/profile_header_familiar_followers_value"
PROFILE_FOLLOWING_COUNT_TEXT_RESID = "com.instagram.android:id/profile_header_familiar_following_value"
PROFILE_FOLLOW_BUTTON_RESID = "com.instagram.android:id/profile_header_user_action_follow_button"

PROFILE_OPTIONS_MENU_BUTTON_DESC = "Options"  # The three-dot menu on a user's profile page. Suggested: content-desc
PROFILE_SEND_MESSAGE_OPTION_TEXT = "com.instagram.android:id/action_sheet_row_text_view"  # The "Send message" text in the menu after clicking options. Suggested: text

# VI. General Search Screen (after tapping SEARCH_TAB_RESID)
GENERAL_SEARCH_INPUT_FIELD_RESID = "com.instagram.android:id/action_bar_search_edit_text"
GENERAL_SEARCH_USER_TAB_TEXT = "Accounts"  # Text for the "Accounts" or "Users" tab in search results.

GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS = "android.widget.LinearLayout"  # Class for a user item row in general search results.
# GENERAL_SEARCH_RESULT_ITEM_CONTAINER_RESID = "com.instagram.android:id/row_search_user_container_TODO_GENERAL_SEARCH" # Or its resource-id
GENERAL_SEARCH_RESULT_USERNAME_TEXT_RESID = "com.instagram.android:id/row_search_user_username"  # Username TextView within that item.

# Generic elements
BACK_BUTTON_DESC = "Back"
OPTIONS_BUTTON_DESC = "Options"  # Generic options, might be different from profile specific.


# --- End Constants ---


def safe_click(element, timeout=5):
    if element.wait(timeout=timeout):
        element.click()
        return True
    print(
        f"WARN: Element not found for click after {timeout}s: {element.selector if hasattr(element, 'selector') else 'Unknown element'}")
    return False


def ensure_instagram_open(d, package_name="com.instagram.android"):
    current_app = d.app_current()
    if current_app['package'] != package_name:
        print(f"Instagram not in foreground. Current app: {current_app['package']}. Starting Instagram...")
        d.app_start(package_name, use_monkey=True)
        time.sleep(3)


def go_to_home(d):
    # Ensure Instagram app is in the foreground.
    ensure_instagram_open(d)  # This helper makes sure Insta is the current app.

    # Try to navigate back multiple times to ensure we reach a state where the home tab is visible.
    # This is important if the bot is deep in a menu, a chat, a profile page, or any other UI state.
    # The goal is to return to a "base" screen where the main navigation tabs (like Home) are present.
    max_back_presses = 6  # Maximum number of times to press "back". Adjust if needed.
    home_tab_visible = False
    print(f"Attempting to navigate to Home. Max back presses: {max_back_presses}.")

    for i in range(max_back_presses):
        # Check if the home tab is already visible.
        # HOME_TAB_RESID is the resource ID for the home button/tab (e.g., "com.instagram.android:id/feed_tab").
        # Using .exists is a quick check without waiting for too long.
        if d(resourceId=HOME_TAB_RESID).exists:
            home_tab_visible = True
            print(f"Home tab found after {i} back press(es).")
            break  # Exit loop, home tab is visible.

        # If not visible, press the physical "back" button on the device.
        print(f"Home tab not visible yet, pressing back (attempt {i + 1}/{max_back_presses}).")
        d.press("back")
        # Wait for the UI to settle after the back press.
        # A short delay is crucial for the UI to update and for subsequent .exists checks to be accurate.
        time.sleep(2)  # Adjusted sleep time for UI transition.

    if not home_tab_visible:
        print(f"WARN: Home tab ({HOME_TAB_RESID}) was not found after {max_back_presses} back presses. "
              f"The UI might be in an unexpected state. Attempting to click the home tab anyway.")

    # Now, unconditionally attempt to click the home button.
    # Even if it wasn't found in the loop, it might have appeared after the last back press,
    # or we want to log the failure from safe_click if it's truly not there.
    home_button = d(resourceId=HOME_TAB_RESID)
    if not safe_click(home_button):  # safe_click includes a wait and then clicks.
        print(f"ERROR: Failed to click the Home tab (ID: '{HOME_TAB_RESID}'). "
              f"The bot may not be on the home screen, which can affect subsequent actions.")
    else:
        print("Successfully clicked the Home tab.")

    # Wait for the home screen to potentially load content or fully transition.
    time.sleep(1)


def go_to_dm_list(d):
    # Check if already on the DM list screen
    # Using DM_LIST_HEADER_TEXT_RESID and also checking for NEW_CHAT_BUTTON as a secondary confirmation
    if d(resourceId=DM_LIST_HEADER_TEXT_RESID).exists and \
            (d(description=DM_LIST_NEW_CHAT_BUTTON_DESC).exists or d(
                resourceId=DM_LIST_SEARCH_ACTIVATION_ELEMENT_RESID).exists):  # Added more checks for robustness
        print("Already on DM list. No action needed.")
        return True

    ensure_instagram_open(d)
    go_to_home(d)  # This function now also checks if it needs to go back from DM list first
    dm_button = d(resourceId=DM_INBOX_ICON_RESID)
    if not safe_click(dm_button, timeout=10):
        print(f"ERROR: DM icon '{DM_INBOX_ICON_RESID}' not found on home screen.")
        return False
    print("Navigated to DM list.")
    time.sleep(2)
    if d(resourceId=DM_LIST_HEADER_TEXT_RESID).wait(timeout=5):
        return True
    print("WARN: DM list header not found after clicking DM icon.")
    return False


def _get_element_identifier(ui_object_info):
    """Helper to get content-desc or text from ui_object.info"""
    if not ui_object_info:
        return None
    return ui_object_info.get('contentDescription') or ui_object_info.get('text')


def _parse_message_timestamp(timestamp_str: str, reference_date: datetime) -> datetime:
    """
    Parses various Instagram timestamp string formats into datetime objects.
    This is a simplified parser and might need significant enhancements.

    Args:
        timestamp_str: The string from the UI (e.g., "10:23 AM", "Yesterday", "Mon", "Dec 15").
        reference_date: The date to use as 'today' for relative timestamps.

    Returns:
        A datetime object, or reference_date if parsing fails (as a fallback).
    """
    if not timestamp_str:
        return reference_date  # Fallback to now

    timestamp_str_lower = timestamp_str.lower()
    now = reference_date

    try:
        # 1. Specific keywords like "now" (though less common for actual messages)
        if "now" in timestamp_str_lower:  # e.g., "Seen just now" - use current time
            return now

        # 2. Time only (e.g., "10:23 AM", "17:45") - assume today
        # Instagram often shows "Active now", "Active 10m ago", etc. These are statuses, not message timestamps.
        # Actual message timestamps are more like "10:23 AM" or "Yesterday".
        if ":" in timestamp_str and ("am" in timestamp_str_lower or "pm" in timestamp_str_lower) \
                and not any(
            day in timestamp_str_lower for day in ["yesterday", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]):
            # This is for formats like "10:30 AM"
            parsed_time = datetime.strptime(timestamp_str.replace(" ", ""), "%I:%M%p")  # "10:30AM"
            return now.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)

        # 3. "Yesterday"
        if "yesterday" in timestamp_str_lower:
            # If it includes a time like "Yesterday, 10:30 PM"
            if ":" in timestamp_str:
                try:
                    # Attempt to parse "Yesterday, HH:MM AM/PM"
                    # Need to remove "Yesterday, " part first
                    time_part = timestamp_str_lower.split("yesterday")[-1].strip(', ')
                    parsed_time = datetime.strptime(time_part.replace(" ", ""), "%I:%M%p")
                    return (now - timedelta(days=1)).replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0,
                                                             microsecond=0)
                except ValueError:  # If parsing time part fails, just use yesterday midnight
                    pass  # Fall through to simpler "yesterday"
            return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)  # Midnight yesterday

        # 4. Day of the week (e.g., "Mon", "Tue 11:00 AM")
        days_of_week = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        for day_name, day_num in days_of_week.items():
            if day_name in timestamp_str_lower:
                days_ago = (now.weekday() - day_num + 7) % 7
                if days_ago == 0 and not (
                        ":" in timestamp_str):  # If it's "Mon" and today is Monday, assume last week's Mon unless time specified
                    # If time is specified (e.g. "Mon 10:00 AM"), assume it's today if today is Mon.
                    # If no time, and it's today's day name, assume a week ago.
                    days_ago = 7  # Default to a week ago if it's just the day name and it matches today.

                # If it includes time, e.g., "Mon 11:23 AM"
                parsed_dt = (now - timedelta(days=days_ago))
                if ":" in timestamp_str:
                    try:
                        time_part = timestamp_str_lower.split(day_name)[-1].strip()
                        if time_part:  # Ensure there is a time part
                            parsed_time = datetime.strptime(time_part.replace(" ", ""), "%I:%M%p")
                            parsed_dt = parsed_dt.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0,
                                                          microsecond=0)
                        else:  # Just day name, e.g. "Mon"
                            parsed_dt = parsed_dt.replace(hour=0, minute=0, second=0, microsecond=0)  # Midnight
                        return parsed_dt
                    except ValueError:  # Parsing time part failed
                        # Fallback to midnight of that day
                        return parsed_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                else:  # Just the day name "Mon"
                    return parsed_dt.replace(hour=0, minute=0, second=0, microsecond=0)  # Midnight of that day

        # 5. Date format (e.g., "Dec 15", "15 Dec", "Dec 15, 2023")
        # This needs to handle year or assume current year.
        # Example: "Dec 15" or "15 Dec"
        # Python's strptime can be tricky with day/month order and optional year.
        # Let's try a few common formats.
        date_formats_to_try = [
            "%b %d",  # "Dec 15"
            "%d %b",  # "15 Dec"
            "%b %d, %Y",  # "Dec 15, 2023"
            "%d %b, %Y",  # "15 Dec, 2023"
        ]
        for fmt in date_formats_to_try:
            try:
                parsed_dt = datetime.strptime(timestamp_str, fmt)
                if parsed_dt.year == 1900:  # strptime defaults to 1900 if year not given
                    parsed_dt = parsed_dt.replace(year=now.year)
                # If the parsed date is in the future (e.g. "Dec 15" parsed in Jan, assumes current year),
                # it's likely from the previous year.
                if parsed_dt > now and fmt in ["%b %d", "%d %b"]:
                    parsed_dt = parsed_dt.replace(year=now.year - 1)

                # Check if there's also a time part, e.g., "Dec 15, 10:30 AM"
                if ":" in timestamp_str and ("am" in timestamp_str_lower or "pm" in timestamp_str_lower):
                    # This is more complex; the simple strptime above might fail if time is included directly.
                    # Example: "Dec 15, 10:54 AM"
                    # We might need to split date and time if combined.
                    # For now, if strptime succeeded with date only, we'll take it (midnight).
                    # A more robust parser would handle "Date, Time" formats.
                    # Let's try to re-parse with a combined format if it looks like it has time.
                    try:
                        full_fmt = fmt + ", %I:%M%p"  # e.g. "%b %d, %I:%M%p"
                        # Need to strip year from fmt if it was added by previous logic
                        if "%Y" in fmt:
                            full_fmt = fmt.replace(", %Y", "") + ", %I:%M%p"  # temporary fix
                            parsed_with_time = datetime.strptime(
                                timestamp_str.split(",")[0] + "," + timestamp_str.split(",")[1], full_fmt)
                            if parsed_with_time.year == 1900: parsed_with_time = parsed_with_time.replace(year=now.year)
                            if parsed_with_time > now and fmt in ["%b %d",
                                                                  "%d %b"]: parsed_with_time = parsed_with_time.replace(
                                year=now.year - 1)
                            return parsed_with_time
                        else:  # No year in original format
                            parsed_with_time = datetime.strptime(timestamp_str, full_fmt)
                            if parsed_with_time.year == 1900: parsed_with_time = parsed_with_time.replace(year=now.year)
                            if parsed_with_time > now: parsed_with_time = parsed_with_time.replace(
                                year=now.year - 1)  # if future date, assume last year
                            return parsed_with_time
                    except ValueError:
                        # Time parsing failed, stick with date at midnight
                        pass
                return parsed_dt.replace(hour=0, minute=0, second=0, microsecond=0)  # Midnight of that date
            except ValueError:
                continue  # Try next format

        # 6. Relative times like "1h", "23m" (these are often for "active status" not message timestamps)
        # For actual messages, IG tends to use "10:30 AM", "Yesterday", "Mon", "Dec 15".
        # If these appear for messages, this parser would need extension.
        # E.g., "1 h", "23 m"
        if "h" == timestamp_str_lower[-1] and timestamp_str_lower[:-1].strip().isdigit():
            hours_ago = int(timestamp_str_lower[:-1].strip())
            return now - timedelta(hours=hours_ago)
        if "m" == timestamp_str_lower[-1] and timestamp_str_lower[:-1].strip().isdigit():
            minutes_ago = int(timestamp_str_lower[:-1].strip())
            return now - timedelta(minutes=minutes_ago)

    except Exception as e:
        print(f"WARN: Could not parse timestamp string '{timestamp_str}': {e}. Defaulting to reference_date.")
        return reference_date  # Fallback

    print(f"WARN: Unhandled timestamp format: '{timestamp_str}'. Defaulting to reference_date.")
    return reference_date  # Fallback for unhandled formats


def open_thread_by_username(d, target_username_in_list, max_scrolls=3):
    print(f"Searching for thread with '{target_username_in_list}' in DM list...")
    for i in range(max_scrolls + 1):
        thread_containers = d(resourceId=DM_THREAD_ITEM_CONTAINER_RESID)
        if thread_containers.exists:
            for container_idx in range(thread_containers.count):
                container = thread_containers[container_idx]
                username_el = container.child(resourceId=DM_THREAD_ITEM_USERNAME_TEXT_RESID)
                if username_el.exists and target_username_in_list.lower() in username_el.info.get('text', '').lower():
                    print(f"Found thread container for '{target_username_in_list}'. Clicking.")
                    if safe_click(container):
                        time.sleep(2)
                        header_el = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
                        if header_el.wait(timeout=5):
                            header_identifier = _get_element_identifier(header_el.info)
                            if header_identifier and target_username_in_list.lower() in header_identifier.lower():
                                print(f"Successfully opened thread, header matches: {header_identifier}")
                                return True
                            else:
                                print(
                                    f"WARN: Chat header identifier '{header_identifier}' does not match '{target_username_in_list}'.")
                        else:
                            print(
                                f"WARN: Chat header '{DM_CHAT_HEADER_USERNAME_TEXT_RESID}' not found after opening thread.")
                        d.press("back")  # Go back if verification failed
                        return False  # Stop if we thought we found it but verification failed
        if i < max_scrolls:
            print(f"Scrolling DM list (attempt {i + 1}/{max_scrolls})")
            d.swipe_ext("up", scale=0.8, duration=0.2)
            time.sleep(1)
    print(f"ERROR: Thread with '{target_username_in_list}' not found in DM list after scrolling.")
    return False


def get_threads_from_dm_list(d, bot_username, max_threads_to_fetch=10, max_scrolls=3):
    print("Fetching threads from DM list...")
    threads_data = []
    seen_thread_titles = set()
    for i in range(max_scrolls + 1):
        thread_containers = d(resourceId=DM_THREAD_ITEM_CONTAINER_RESID)
        if not thread_containers.exists:
            if i == 0: print("No thread items found on DM screen.")
            break
        for container_idx in range(thread_containers.count):
            container = thread_containers[container_idx]
            title_el = container.child(resourceId=DM_THREAD_ITEM_USERNAME_TEXT_RESID)
            snippet_el = container.child(resourceId=DM_THREAD_ITEM_SNIPPET_TEXT_RESID)
            if title_el.exists:
                title = title_el.info['text']
                if title in seen_thread_titles or title.lower() == bot_username.lower():
                    continue
                seen_thread_titles.add(title)
                users_in_thread = [u.strip() for u in title.split(',')]
                if bot_username not in users_in_thread and len(users_in_thread) == 1:
                    users_in_thread.append(bot_username)
                threads_data.append({
                    "id": title, "users": users_in_thread,
                    "last_message_snippet": snippet_el.info['text'] if snippet_el.exists else "",
                    "timestamp_approx": datetime.now(),
                })
                if len(threads_data) >= max_threads_to_fetch: break
        if len(threads_data) >= max_threads_to_fetch or i == max_scrolls: break
        d.swipe_ext("up", scale=0.8, duration=0.2)
        time.sleep(1.5)
    print(f"Fetched {len(threads_data)} thread summaries.")
    return threads_data


def get_messages_from_open_thread(d, bot_username, last_processed_timestamp=None, max_messages=20, max_scrolls_up=3):
    print(f"Fetching messages from open thread. Stop if older than: {last_processed_timestamp}")
    messages = []
    processed_msg_hashes = set()
    stop_fetching = False  # Flag to break outer scroll loop
    peer_username_el = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
    peer_username = "UnknownPeer"
    if peer_username_el.exists:
        peer_username_info = peer_username_el.info
        peer_username = _get_element_identifier(peer_username_info) or 'UnknownPeer'

    # Reference date for parsing relative timestamps consistently across a screen
    # This might need adjustment if messages span multiple days on a single screen,
    # but for "HH:MM AM/PM" type times, it assumes they are for the "current" day of fetching.
    # A more sophisticated approach might try to infer date changes while scrolling.
    current_fetch_time = datetime.now()

    for i in range(max_scrolls_up + 1):
        message_bubbles = d(resourceId=DM_CHAT_MESSAGE_BUBBLE_CONTAINER_RESID)
        if not message_bubbles.exists:
            if i == 0: print("No message bubbles found in open thread.")
            break

        current_screen_messages = []
        # Iterate from bottom to top of screen (visually) for messages,
        # as Instagram usually shows newest at bottom.
        # uiautomator2 lists elements from top to bottom as they appear in XML.
        # So, we might process older messages first on screen if not reversed.
        # However, the sorting at the end should fix order.
        # For timestamp comparison, processing in any order on screen is fine,
        # as we break once *any* message is too old.

        for bubble_idx in range(message_bubbles.count):
            bubble = message_bubbles[bubble_idx]
            text_el = bubble.child(resourceId=DM_CHAT_MESSAGE_TEXT_VIEW_RESID)

            if text_el.exists:
                text = text_el.info['text']
                # Using text + bubble bounds for a simple hash. Consider more robust ID if possible.
                msg_hash = hash(text + str(bubble.info['bounds']))

                if msg_hash in processed_msg_hashes:
                    continue
                processed_msg_hashes.add(msg_hash)

                # --- Timestamp Parsing ---
                timestamp_str = None
                parsed_timestamp = current_fetch_time  # Default if all attempts fail

                # 1. Attempt with the chosen specific Resource ID
                if DM_CHAT_MESSAGE_TIMESTAMP_TEXT_RESID:  # If an ID is set
                    timestamp_el_specific = bubble.child(resourceId=DM_CHAT_MESSAGE_TIMESTAMP_TEXT_RESID)
                    if timestamp_el_specific.exists:
                        timestamp_str = timestamp_el_specific.info.get('text')
                        if timestamp_str:
                            print(
                                f"DEBUG: Found timestamp text '{timestamp_str}' using specific ID {DM_CHAT_MESSAGE_TIMESTAMP_TEXT_RESID}")
                            parsed_timestamp = _parse_message_timestamp(timestamp_str, current_fetch_time)
                        else:
                            print(
                                f"WARN: Timestamp element with ID {DM_CHAT_MESSAGE_TIMESTAMP_TEXT_RESID} found but text is empty. Bubble: {bubble.info['bounds']}")

                # 2. Fallback: Iterate through all TextViews within the bubble if specific ID failed or no text
                if not timestamp_str:  # If specific ID didn't yield a usable timestamp string
                    print(
                        f"INFO: Specific ID {DM_CHAT_MESSAGE_TIMESTAMP_TEXT_RESID if DM_CHAT_MESSAGE_TIMESTAMP_TEXT_RESID else 'N/A'} failed or no text. Trying fallback TextView search for bubble: {bubble.info['bounds']}")
                    possible_ts_elements = bubble.child(className="android.widget.TextView")
                    if not possible_ts_elements.exists:
                        # Sometimes the bubble itself IS the TextView if it's a simple text-only message.
                        # More often, the message text view is a child.
                        # If the bubble has no TextView children, it's unlikely to find a timestamp this way.
                        print(
                            f"DEBUG: No child TextViews found in bubble for fallback search. Bubble: {bubble.info['bounds']}")

                    found_in_fallback = False
                    for idx in range(possible_ts_elements.count):
                        potential_ts_el = possible_ts_elements[idx]
                        # Avoid re-processing the main message text view if it's different from the timestamp view
                        if potential_ts_el.info.get('resourceName') == DM_CHAT_MESSAGE_TEXT_VIEW_RESID:
                            continue  # Skip the main message text itself

                        potential_ts_text = potential_ts_el.info.get('text')
                        if potential_ts_text and potential_ts_text != text:  # Ensure it's not the message body
                            # Heuristic check: Does it look like a timestamp?
                            # _parse_message_timestamp is robust, so we can be a bit lenient here.
                            # Let's check for common characters or keywords.
                            if any(char in potential_ts_text for char in [":", "AM", "PM"]) or \
                                    any(keyword in potential_ts_text.lower() for keyword in
                                        ["yesterday", "mon", "tue", "wed", "thu", "fri", "sat", "sun", "jan", "feb",
                                         "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]):
                                print(
                                    f"DEBUG: Fallback found potential timestamp text '{potential_ts_text}' in bubble child TextView. RID: {potential_ts_el.info.get('resourceName')}")
                                # Try parsing this potential text
                                temp_parsed_ts = _parse_message_timestamp(potential_ts_text, current_fetch_time)
                                # If parsing changes it from current_fetch_time, it's likely a valid parse
                                # And ensure it's not just re-parsing the main message text successfully
                                if temp_parsed_ts != current_fetch_time:
                                    timestamp_str = potential_ts_text
                                    parsed_timestamp = temp_parsed_ts
                                    found_in_fallback = True
                                    print(
                                        f"INFO: Successfully parsed timestamp '{timestamp_str}' using FALLBACK logic. Parsed as: {parsed_timestamp}")
                                    break  # Found a plausible timestamp in fallback
                    if not found_in_fallback and not timestamp_str:  # Still no timestamp_str after specific and fallback
                        print(
                            f"WARN: Could not find or parse timestamp for message (text: '{text[:30]}...') using specific ID or fallback. Using current_fetch_time. Bubble: {bubble.info['bounds']}")

                # --- End Timestamp Parsing ---

                # Check against last_processed_timestamp
                if last_processed_timestamp and parsed_timestamp <= last_processed_timestamp:
                    print(
                        f"Message timestamp ({parsed_timestamp}) is older than or same as last processed ({last_processed_timestamp}). Stopping.")
                    stop_fetching = True
                    break  # Break from iterating current screen's bubbles

                screen_width = d.window_size()[0]
                # Crude way to check if message is outgoing (sent by bot)
                # Assumes outgoing messages are on the right half of the screen.
                is_outgoing = bubble.info['bounds']['left'] > screen_width / 3  # Adjusted threshold a bit

                sender_ui_name = bot_username if is_outgoing else peer_username

                # Check for explicit sender name (e.g., in group DMs)
                sender_name_explicit_el = bubble.child(resourceId=DM_CHAT_MESSAGE_SENDER_NAME_TEXT_RESID)
                if sender_name_explicit_el.exists:
                    sender_ui_name = sender_name_explicit_el.info['text']

                current_screen_messages.append({
                    "id": msg_hash,  # This hash should ideally be a unique message ID from IG if available
                    "user_id": sender_ui_name,
                    "text": text,
                    "timestamp": parsed_timestamp  # Use the parsed timestamp
                })

        # Add messages from current screen to main list (avoiding duplicates based on hash)
        # This logic might be slightly redundant if hashes are good, but ensures no full duplicates.
        existing_ids = {m['id'] for m in messages}
        for msg in current_screen_messages:
            if msg['id'] not in existing_ids:
                messages.append(msg)

        # messages = list({m['id']: m for m in messages}.values()) # More concise way to ensure unique by id

        if stop_fetching or len(messages) >= max_messages or i == max_scrolls_up:
            break  # Break from the scrolling loop (max_scrolls_up loop)

        # Scroll up to get older messages (swipe content of chat down)
        print(f"Scrolling down to fetch older messages (Loop {i + 1}/{max_scrolls_up})")
        d.swipe_ext("down", scale=0.6, duration=0.5)  # Swipe from near top downwards to load older
        time.sleep(1.5)  # Wait for new messages to load

    if not messages:
        print("No messages were fetched from the open thread.")
    else:
        print(f"Fetched {len(messages)} messages from open thread.")

    # Sort messages by timestamp (newest first, as is common in UIs, or oldest first if preferred)
    # The original code sorts oldest first (ascending). Let's keep that.
    return sorted(messages, key=lambda x: x['timestamp'])


def send_dm_in_open_thread(d, message_text):
    input_field = d(resourceId=DM_CHAT_INPUT_FIELD_RESID)
    send_button = d(resourceId=DM_CHAT_SEND_BUTTON_RESID)
    input_field = d(resourceId=DM_CHAT_INPUT_FIELD_RESID)  # Re-fetch, might have gone stale
    if not input_field.wait(timeout=3):
        print(f"ERROR: DM input field '{DM_CHAT_INPUT_FIELD_RESID}' not found before sending message.")
        return False
    if not safe_click(input_field):  # Click to focus
        print(f"ERROR: Could not click DM input field '{DM_CHAT_INPUT_FIELD_RESID}'.")
        return False
    d.clear_text()
    time.sleep(0.2)
    # d.set_text(message_text) # Alternative to send_keys, sometimes more reliable
    d.send_keys(message_text)
    time.sleep(0.5)
    if not safe_click(send_button):
        print(f"ERROR: DM send button '{DM_CHAT_SEND_BUTTON_RESID}' not found/clickable.")
        return False
    print(f"DM sent (hopefully): '{message_text[:30]}...'")
    time.sleep(1)
    return True


def go_to_user_profile(d, target_username):
    """Navigates to a user's profile page using general search."""
    ensure_instagram_open(d)
    print(f"Navigating to profile of {target_username} via general search...")
    go_to_home(d)
    if not safe_click(d(resourceId=SEARCH_TAB_RESID)):
        print(f"ERROR: Could not click search tab '{SEARCH_TAB_RESID}'.")
        return False
    time.sleep(2)

    search_bar = d(resourceId=GENERAL_SEARCH_INPUT_FIELD_RESID)
    if not safe_click(search_bar):  # Click to focus
        print(f"ERROR: General search input field '{GENERAL_SEARCH_INPUT_FIELD_RESID}' not found.")
        return False
    d.clear_text()
    d.send_keys(target_username)
    print(f"Typed '{target_username}' into general search. Waiting for results...")
    time.sleep(1)  # Wait for search results to load

    # Optionally, click on "Accounts" tab if it's not default
    accounts_tab = d(text=GENERAL_SEARCH_USER_TAB_TEXT)
    if accounts_tab.exists:
        print(f"Clicking '{GENERAL_SEARCH_USER_TAB_TEXT}' tab.")
        safe_click(accounts_tab)
        time.sleep(2)

    # Find the user in results (using GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS or _RESID)
    # This part needs robust selectors for the results list.
    # Assuming GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS exists and is reliable:
    user_results = d(
        className=GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS)  # Or by GENERAL_SEARCH_RESULT_ITEM_CONTAINER_RESID
    if not user_results.exists:
        print(
            f"No user results found using class '{GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS}'. Try different selector.")
        return False

    for i in range(user_results.count):
        item = user_results[i]
        username_el = item.child(resourceId=GENERAL_SEARCH_RESULT_USERNAME_TEXT_RESID)
        if username_el.exists and target_username.lower() in username_el.info.get('text', '').lower():
            print(f"Found {target_username} in general search results. Clicking.")
            if safe_click(item):  # Click the whole item
                time.sleep(3)  # Wait for profile to load
                # Verify on profile page
                profile_header_el = d(resourceId=PROFILE_USERNAME_HEADER_TEXT_RESID)
                if profile_header_el.wait(timeout=5) and target_username.lower() in profile_header_el.info.get('text',
                                                                                                               '').lower():
                    print(f"Successfully navigated to {target_username}'s profile.")
                    return True
                else:
                    print(f"Clicked user, but profile header verification failed for {target_username}.")
                    return False
    print(f"User {target_username} not found in the first page of general search results.")
    return False


def go_to_own_profile(d, bot_username):
    ensure_instagram_open(d)

    # Check if currently on DM list screen, if so, go back to access main tabs
    # Using DM_LIST_HEADER_TEXT_RESID and DM_LIST_NEW_CHAT_BUTTON_DESC
    if d(resourceId=DM_LIST_HEADER_TEXT_RESID).exists or \
            d(description=DM_LIST_NEW_CHAT_BUTTON_DESC).exists:
        print("Currently on DM list, pressing back to reach main tabs.")
        d.press("back")
        time.sleep(1.5)  # Allow UI to transition

    profile_tab_button = d(resourceId=PROFILE_TAB_RESID)
    if not safe_click(profile_tab_button):
        print(f"ERROR: Profile tab/button '{PROFILE_TAB_RESID}' not found.")
        return False
    time.sleep(3)
    # Use specific ID for own profile header username, as it differs from other users' profile headers
    # Case-insensitive check for the username text
    profile_header_el = d(resourceId="com.instagram.android:id/action_bar_large_title_auto_size")
    if profile_header_el.wait(timeout=5):
        header_text = profile_header_el.info.get('text', '')
        if bot_username.lower() == header_text.lower():
            print("Successfully on own profile.")
            return True
    print(
        f"ERROR: Navigated to profile tab, but header username does not match '{bot_username}' using specific ID 'com.instagram.android:id/action_bar_large_title_auto_size'. Header text found: '{header_text if 'header_text' in locals() else 'N/A'}'")
    return False


def get_bot_profile_info(d, bot_username):
    # ... (This function seems mostly fine with your filled constants, no major changes based on feedback yet)
    # Ensure PROFILE_FOLLOWER_COUNT_TEXT_RESID and PROFILE_FOLLOWING_COUNT_TEXT_RESID are correct.
    if not go_to_own_profile(d, bot_username):
        return {}
    print(f"Scraping profile info for {bot_username}...")
    info = {"username": bot_username}
    full_name_el = d(resourceId=PROFILE_FULL_NAME_TEXT_RESID)
    bio_el = d(resourceId=PROFILE_BIO_TEXT_RESID)
    if full_name_el.exists: info["full_name"] = full_name_el.info['text']
    if bio_el.exists: info["biography"] = bio_el.info['text']
    follower_el = d(resourceId=PROFILE_FOLLOWER_COUNT_TEXT_RESID)
    if follower_el.exists: info["follower_count"] = follower_el.info['text'].replace(',', '')
    following_el = d(resourceId=PROFILE_FOLLOWING_COUNT_TEXT_RESID)
    if following_el.exists: info["following_count"] = following_el.info['text'].replace(',', '')
    print(f"Bot profile info scraped: {info}")
    return info


def send_dm_from_profile(d, target_username, message_text):
    """Attempts to send a DM by navigating to profile, using options menu."""
    if not go_to_user_profile(d, target_username):
        print(f"Failed to navigate to {target_username}'s profile. Cannot send DM from profile.")
        return False

    # Click the three-dot options menu on the profile
    # PROFILE_OPTIONS_MENU_BUTTON_DESC is "Options"
    options_menu_btn = d(description=PROFILE_OPTIONS_MENU_BUTTON_DESC)
    if not safe_click(options_menu_btn):
        print(
            f"ERROR: Could not find/click profile options menu (desc: '{PROFILE_OPTIONS_MENU_BUTTON_DESC}') for {target_username}.")
        return False
    time.sleep(1.5)  # Wait for the action sheet to appear

    # Click "Send message" from the options menu
    # PROFILE_SEND_MESSAGE_OPTION_TEXT is "com.instagram.android:id/action_sheet_row_text_view"
    # This implies it's the resource-id of the TextViews in the action sheet.
    # We need to find the one whose text content is "Send message".

    send_message_option_el = None
    # Assuming PROFILE_SEND_MESSAGE_OPTION_TEXT holds the resource-id of the TextViews in the action sheet list
    action_sheet_rows = d(resourceId=PROFILE_SEND_MESSAGE_OPTION_TEXT)

    if action_sheet_rows.exists:
        for i in range(action_sheet_rows.count):
            row_text_view = action_sheet_rows[i]
            if row_text_view.info:  # Ensure info is available
                current_text = row_text_view.info.get('text', '').lower()
                print(f"Checking action sheet item: '{current_text}'")
                # Look for "send message" or a similar phrase. Adjust if the exact text is different.
                if "send message" in current_text:
                    send_message_option_el = row_text_view
                    print(f"Found 'Send message' option: {current_text}")
                    break

    if not send_message_option_el:
        print(
            f"ERROR: Could not find 'Send message' text within elements with ID '{PROFILE_SEND_MESSAGE_OPTION_TEXT}'.")
        # Attempt to close the action sheet if it's still open
        # This might be a back press or tapping outside the sheet, depending on UI
        if d(resourceId=PROFILE_OPTIONS_MENU_BUTTON_DESC).exists:  # Check if profile still visible (implies menu might be overlaid)
            print("Attempting to close action sheet with a back press.")
            d.press("back")
        return False

    if not safe_click(send_message_option_el):
        print(f"ERROR: Could not click the identified 'Send message' option.")
        # Attempt to close the action sheet
        if d(resourceId=PROFILE_OPTIONS_MENU_BUTTON_DESC).exists:
            print("Attempting to close action sheet with a back press after failed click.")
            d.press("back")
        return False

    print("Clicked 'Send message' option. Waiting for DM chat screen to open...")
    time.sleep(3.5)  # Increased wait time for DM chat screen to open

    # Now we should be in the DM chat screen with the target_username
    # Verify header
    header_el_verify = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
    opened_correct_chat = False
    if header_el_verify.wait(timeout=2):  # Increased timeout
        header_identifier_verify = _get_element_identifier(header_el_verify.info)
    if header_identifier_verify and target_username.lower() in header_identifier_verify.lower():
        opened_correct_chat = True
    print(
        f"Successfully navigated to DM screen with {target_username} from their profile. Header: {header_identifier_verify}")

    if not opened_correct_chat:
        print(f"ERROR: Opened a chat after 'Send message' from profile, but header does not match {target_username}.")
    # Try to navigate back if verification failed
    d.press("back")
    return False

    return send_dm_in_open_thread(d, message_text)


def search_and_open_dm_with_user(d, target_username,
                                 bot_username):  # bot_username is not used here but good for consistency
    ensure_instagram_open(d)
    print(f"Trying to find/start DM with {target_username}...")
    if not go_to_dm_list(d):
        return False

    # 1. Try to find and open existing thread from DM list (quick check)
    if open_thread_by_username(d, target_username, max_scrolls=1):
        print(f"Opened existing DM thread with {target_username} from list.")
        return True

    # 2. If not found in initial DM list, attempt to create a new chat using the user-provided flow
    print(
        f"Thread with {target_username} not found in initial DM list. Attempting to create new chat following specified flow.")

    # Step 1: Click New message (has content desc)
    new_chat_btn = d(description=DM_LIST_NEW_CHAT_BUTTON_DESC)  # Using content-desc as per your constant
    if not safe_click(new_chat_btn):
        print(f"ERROR: New chat button (desc: '{DM_LIST_NEW_CHAT_BUTTON_DESC}') not found in DM list.")
        return False
    print("Clicked 'New message' button. Waiting for New Chat screen...")
    time.sleep(1.5)  # Allow time for the new chat screen to load

    # Step 2: Get the selector for the "To:" or "Search" input field on the new chat screen.
    # NEW_CHAT_TO_FIELD_INPUT_RESID is the resource ID, e.g., "com.instagram.android:id/search_edit_text".
    search_input_selector = d(resourceId=NEW_CHAT_TO_FIELD_INPUT_RESID)

    # Try to click the search field to ensure it's focused before typing.
    # safe_click is a helper that waits for the element and then clicks.
    if not safe_click(search_input_selector):
        # If the click fails, it doesn't necessarily mean the element isn't usable.
        # It might be already focused, or there might be a temporary overlay that safe_click couldn't handle.
        print(f"WARN: safe_click failed for search input field '{NEW_CHAT_TO_FIELD_INPUT_RESID}'. "
              f"Checking if the element exists to attempt setting text anyway.")

        # Check if the element actually exists on the screen.
        if not search_input_selector.exists:
            # If the element genuinely doesn't exist, we can't proceed.
            print(f"ERROR: Search input field '{NEW_CHAT_TO_FIELD_INPUT_RESID}' not found on screen. "
                  f"Cannot type username.")
            d.press("back")  # Attempt to go back from the new chat screen to a known state.
            return False

        # If the element exists even though click failed, we can still try to set its text.
        print(f"WARN: Field '{NEW_CHAT_TO_FIELD_INPUT_RESID}' exists despite click issues. Attempting to set text.")

    # At this point, we believe the search input field is on the screen.
    # We will use element.set_text(target_username) to input the username.
    # This method is called directly on the UiObject (the search_input_selector).
    # element.set_text() usually overwrites any existing text in the field.
    # It's generally more robust than d.send_keys() for text input, especially if
    # Android Input Method Editor (IME) or virtual keyboard issues occur.
    print(f"Attempting to set text '{target_username}' into field '{NEW_CHAT_TO_FIELD_INPUT_RESID}'...")
    search_input_selector.set_text(target_username)

    # After setting the text, print a confirmation and wait for search results to load.
    print(f"Set text '{target_username}' into New Chat search. Waiting for results...")
    time.sleep(1.5)  # Allow time for search results to populate (e.g., user list).

    # Step 3: Click the user whose resource id com.instagram.android:id/row_user_secondary_name matches the username
    # NEW_CHAT_USER_RESULT_USERNAME_TEXT_RESID is "com.instagram.android:id/row_user_secondary_name"
    # We need to iterate through potential matches if multiple users appear.

    # The results are likely within NEW_CHAT_USER_RESULT_ITEM_CONTAINER_RESID
    user_results_containers = d(resourceId=NEW_CHAT_USER_RESULT_ITEM_CONTAINER_RESID)
    user_selected_and_navigated = False

    if user_results_containers.exists:
        for i in range(user_results_containers.count):
            container = user_results_containers[i]
            # Look for the username element WITHIN this specific container
            username_el = container.child(resourceId=NEW_CHAT_USER_RESULT_USERNAME_TEXT_RESID)
            if username_el.exists:
                current_username_text = username_el.info.get('text', '').lower()
                print(f"Checking search result: {current_username_text}")
                if target_username.lower() == current_username_text:
                    print(f"Found exact match for {target_username}. Clicking this user entry.")
                    # According to your flow, clicking this username element directly should work.
                    if safe_click(username_el):  # Click the username TextView directly
                        user_selected_and_navigated = True
                        break  # Exit loop once user is clicked
                    else:
                        print(f"ERROR: Failed to click the username element for {target_username}.")
                        # Potentially try clicking the container as a fallback if direct username click fails
                        if safe_click(container):
                            user_selected_and_navigated = True
                            break
                        else:
                            print(f"ERROR: Also failed to click container for {target_username}.")
                            continue

    if not user_selected_and_navigated:
        print(f"ERROR: User '{target_username}' not found in new chat search results, or failed to click.")
        d.press("back")  # Go back from the new chat screen
        return False

    print(f"Clicked on {target_username}. Expecting to be on chat screen...")
    time.sleep(1.5)  # Wait for the chat screen to fully load after selection

    # Step 4 & 5 are handled by verifying we are on the chat screen and then the main bot loop will use send_dm_in_open_thread
    # Verify we are on the chat screen with the correct user
    header_el_verify = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
    if header_el_verify.wait(timeout=7):  # Increased timeout for screen transition
        header_identifier_verify = _get_element_identifier(header_el_verify.info)
        if header_identifier_verify and target_username.lower() in header_identifier_verify.lower():
            print(f"Successfully navigated to chat screen with {target_username}. Header: {header_identifier_verify}")
            # The main bot loop will now handle sending the message using send_dm_in_open_thread
            # if the 'send_message' function was called by Gemini.
            return True  # Indicate that the chat is open and ready.
        else:
            print(
                f"WARN: Navigated to a chat screen, but header identifier '{header_identifier_verify}' does not match '{target_username}'.")
    else:
        print(
            f"ERROR: Did not land on the expected chat screen with {target_username} after selection (header element '{DM_CHAT_HEADER_USERNAME_TEXT_RESID}' not found or timed out).")

    # If verification fails, attempt to go back to a known state (DM list)
    print("Failed to verify chat screen for new chat. Returning to DM list.")
    d.press("back")  # Try to go back from whatever screen it's on
    time.sleep(0.5)
    # A second back press might be needed if the "new chat user selection" is a layer above the actual chat creation screen
    # If clicking the user directly opens the chat, one back might be enough.
    # If it goes to an intermediate "confirm chat" screen (which your flow implies it doesn't), then two backs.
    current_activity = d.app_current().get('activity')
    print(f"Current activity after first back: {current_activity}")
    # Heuristic: if not in DM list activity, press back again. This needs knowledge of activity names or more robust state checking.
    # For simplicity, we'll just do one back press for now from the unverified chat screen.
    # If this often leaves you on an intermediate screen, you might need a loop or specific check.

    return False


def return_to_dm_list_from_thread(d):
    """
    Attempts to return to the DM list screen from an open DM thread by pressing back.
    Verifies the return by checking for known DM list elements.
    """
    print("Attempting to return to DM list from thread by pressing back...")
    d.press("back")
    time.sleep(1.5)  # Allow UI to transition

    # Verify by checking for a known element on the DM list screen
    dm_list_header = d(resourceId=DM_LIST_HEADER_TEXT_RESID)
    new_chat_button = d(description=DM_LIST_NEW_CHAT_BUTTON_DESC)  # Alternative check

    if dm_list_header.wait(timeout=3) or new_chat_button.wait(timeout=3):
        print("Successfully returned to DM list screen.")
        return True
    else:
        print("WARN: After pressing back, DM list screen elements not immediately found.")
        # As a fallback, try the more comprehensive go_to_dm_list if simple back fails
        print("WARN: Attempting full go_to_dm_list as fallback.")
        return go_to_dm_list(d)


def check_for_instagram_dm_notification(d, package_name="com.instagram.android"):
    """
    Opens the notification shade, checks for Instagram DM notifications,
    clicks on a relevant one if found, and closes the shade.
    Returns True if a DM notification was found and clicked, False otherwise.
    """
    print("Opening notification shade to check for Instagram DMs...")
    d.open_notification()
    time.sleep(2)  # Allow notifications to load

    # Attempt to find notifications belonging to the Instagram package
    # Common resource IDs for notification elements (these can vary by Android version/OEM)
    # Android Oreo and above often use "android:id/title" for title, "android:id/text" for content.
    # Notifications are usually within a RecyclerView or similar container.
    # We'll iterate through elements that could be individual notifications.
    # A common parent for notifications might be 'com.android.systemui:id/notification_stack_scroller'

    # Generic approach: look for text elements that might contain app name or DM keywords
    # This is less precise than package name checking if directly available on the notification object
    # Uiautomator2's d.info['notifications'] or d.notifications might be more direct if available and working.
    # However, iterating through visible elements is a common fallback.

    # Let's assume notifications are list items, often with a TextView for the app name and another for content.
    # We'll look for any TextView containing "Instagram" first, then check its siblings/children for DM keywords.
    # This is a heuristic approach.

    # Try to get all top-level notifications
    # Common notification container IDs:
    # "com.android.systemui:id/notification_stack_scroller"
    # "android:id/notification_list_holder" (older Android)
    # Or simply look for all TextViews and filter.

    # Simpler: Iterate through all visible text elements in the notification shade
    # This is broad but can catch notifications if specific selectors fail.
    # We need to identify which elements are distinct notifications.

    # Let's try finding notifications by looking for elements with a text attribute that might be the app name
    # or keywords. A more robust way would be to get a list of notification objects if the uiautomator2
    # version/device supports it well (e.g., d.notifications). Since direct access might be tricky,
    # we'll rely on visual cues.

    # Heuristic: Find elements with class 'android.widget.TextView' that could be part of a notification.
    # Then check their parents or siblings for package info or more text.
    # For now, let's try to find notifications that explicitly mention "Instagram" and keywords.

    # A common resource-id for the app name in a notification is "android:id/app_name_text"
    # A common resource-id for the title is "android:id/title"
    # A common resource-id for the content is "android:id/text" or "android:id/big_text"

    notification_found_and_clicked = False

    # Iterate over potential notification views. This is highly dependent on OS version.
    # A common approach is to find elements with a known notification title or text resource ID.
    # Let's assume notifications have a title and text.
    # notifications = d(resourceIdMatches="android:id/notification_main_column") # Example parent
    # Or, more simply, check for text containing "Instagram"

    # This is a simplified approach: look for any text view containing "Instagram" and "message" or "DM"
    # It's not perfect, as it relies on text visible on screen.
    # A more robust solution would use d.notifications if available and reliable.

    possible_notifications = d(className="android.widget.TextView")

    # Prioritize notifications containing "Instagram" and typical DM keywords.
    # Keywords that might indicate a new DM: "New message", "sent you a message", "DM", "reply"
    dm_keywords = ["new message", "sent you a message", "dm", "reply", "sent a message"]

    # Look for notifications that have "Instagram" in their title or text.
    # This is a very broad search as a starting point.
    # A more specific search would involve checking notification structures.
    # For now, iterate through all TextViews in the shade.

    # The d.info['notifications'] or d.notifications() method is preferred if it works reliably.
    # As a fallback, we iterate visible elements.

    # Look for notifications linked to the Instagram package.
    # This is a common pattern for notifications, but might need adjustment.
    # The structure is often: ViewGroup (notification) -> ... -> TextView (title/text)
    # We're looking for any clickable element within a notification from Instagram that seems like a DM.

    # Generic notification elements to check
    # Common notification title ID: "android:id/title"
    # Common notification text ID: "android:id/text"
    # Common notification app name ID: "android:id/app_name_text"

    # Let's iterate through potential notification parent views
    # This is a guess; actual parent view IDs/classes might differ
    notification_parents = d(classNameMatches="android.widget.(FrameLayout|LinearLayout|RelativeLayout)",
                             packageName=package_name)
    if not notification_parents.exists:
        # Fallback if package specific search yields nothing, broaden search
        notification_parents = d(classNameMatches="android.widget.(FrameLayout|LinearLayout|RelativeLayout)")

    for i in range(notification_parents.count):
        parent_view = notification_parents[i]

        # Check if this view itself has text indicating an Instagram DM
        parent_info = parent_view.info
        parent_text_content = (parent_info.get('text', '') + " " + parent_info.get('contentDescription', '')).lower()

        is_instagram_notification = package_name in parent_info.get('packageName',
                                                                    '') or "instagram" in parent_text_content

        if is_instagram_notification:
            # Now check for DM keywords within this potential notification
            # Search for text views within this parent_view
            text_views = parent_view.child(className="android.widget.TextView")
            notification_text_combined = parent_text_content  # Start with parent's text

            for tv_idx in range(text_views.count):
                tv = text_views[tv_idx]
                tv_info = tv.info
                notification_text_combined += " " + (
                        tv_info.get('text', '') + " " + tv_info.get('contentDescription', '')).lower()

            is_dm = any(keyword in notification_text_combined for keyword in dm_keywords)

            if is_dm:
                print(f"Instagram DM notification found. Text: '{notification_text_combined[:100].strip()}...'")
                if safe_click(parent_view, timeout=3):  # Click the parent view of the notification
                    print("Clicked on Instagram DM notification.")
                    time.sleep(4)  # Allow app to open and transition
                    # Attempt to close notification shade - it might auto-close
                    # A single back press is often enough if it didn't auto-close.
                    # Or try d.close_notification() if available and reliable.
                    current_app_after_click = d.app_current()
                    if current_app_after_click.get('package') == package_name:
                        print(f"Instagram app is in foreground after clicking notification.")
                        # If shade is still open, try to close it.
                        # Checking if shade is open is hard. Assume it might be and try a gentle close.
                        # A swipe up from bottom or a back press.
                        # d.press("back") # This might go back in the app, be careful.
                        # d.close_notification() # Preferred if it works consistently.
                        # For now, assume it auto-closes or the app takes full screen.
                        # If not, this might need refinement.
                        # Let's try a specific close if the system UI is still active.
                        if d(packageName="com.android.systemui").exists:  # Check if system UI elements are still focusable
                            print("Attempting to close notification shade with back press (SystemUI was active).")
                            d.press("back")  # Attempt to close notification shade
                            time.sleep(0.5)

                    notification_found_and_clicked = True
                    break  # Exit loop once a notification is handled
                else:
                    print(
                        f"WARN: Found Instagram DM notification but failed to click it: {notification_text_combined[:100]}")
        if notification_found_and_clicked:
            break

    if not notification_found_and_clicked:
        print("No relevant Instagram DM notification found.")

    # Ensure notification shade is closed, regardless of finding a notification
    # d.close_notification() can be aggressive. A back press is usually safer if shade is open.
    # Check if shade is likely open: if current app is SystemUI or if a known shade element exists.
    # This is tricky. For simplicity, we'll try a single back press if no notification was clicked,
    # as clicking should ideally close it or take focus.
    if not notification_found_and_clicked:
        # If we didn't click anything, the shade is definitely still open.
        print("Closing notification shade (no relevant DM found or click failed) with back press.")
        d.press("back")  # Attempt to close notification shade
        time.sleep(1)  # Increased sleep after back press to ensure shade closes

    # One final check: if systemui is still the current app, something went wrong with closing shade.
    if d.app_current()['package'] == 'com.android.systemui':
        print("WARN: Notification shade still seems to be open. Attempting a back press.")
        d.press("back")
        time.sleep(1)

    return notification_found_and_clicked


def check_for_unread_dm_threads(d_device):
    """
    Checks for DM threads marked as unread on the Instagram DM list screen.

    This function navigates to the DM list, then looks at each visible thread
    to see if it has an "unread" indicator (like a blue dot). If it does,
    it gets the username associated with that thread.

    Args:
        d_device: The uiautomator2 device object. This object is our way of
                  interacting with the Android device, like telling it to tap
                  buttons or find elements on the screen.

    Returns:
        A list of strings, where each string is a username from an unread DM
        thread. If no unread threads are found on the currently visible part
        of the screen, or if there's an issue accessing the DM list,
        it returns an empty list.

    Important Concepts for Beginners:
    - Resource ID (e.g., DM_THREAD_ITEM_CONTAINER_RESID): This is a unique
      name given to a UI element (like a button, text field, or layout area)
      in an Android app's code. We use these IDs to reliably find specific
      elements on the screen. Think of it like a unique ID for an HTML element
      in web development (e.g., id="myButton").
    - UI Element: Anything you see on the screen of an app – buttons, text,
      images, input fields, containers holding other elements, etc.
    - d_device(...): This is how we tell uiautomator2 to find an element.
      For example, d_device(resourceId="some_id") means "find the element
      that has the resource ID 'some_id'".
    - .exists: After trying to find an element, .exists tells us if it was
      actually found on the screen (True or False).
    - .child(...): If an element is a container (like a box holding other things),
      .child(...) lets us find an element specifically inside that container.
    - .info['text']: If an element is a text field or has text, .info['text']
      retrieves that visible text content.
    """
    print("Checking for unread DM threads...")
    unread_thread_usernames = []

    # Step 1: Ensure we are on the DM list screen.
    # The go_to_dm_list function handles navigation and returns True if successful.
    if not go_to_dm_list(d_device):
        print("ERROR: Could not navigate to DM list. Cannot check for unread threads.")
        return []  # Return empty list if we can't even get to the DMs

    # Step 2: Find all visible DM thread item containers.
    # DM_THREAD_ITEM_CONTAINER_RESID is a constant (e.g., "com.instagram.android:id/row_inbox_container")
    # holding the resource ID for the container of each individual DM thread shown in the list.

    # First, get the selector for all DM thread item containers currently visible on the screen.
    # A selector is like a query or a recipe that uiautomator2 uses to find UI elements.
    # It doesn't get the elements immediately, but it knows how to find them.
    thread_container_selector = d_device(resourceId=DM_THREAD_ITEM_CONTAINER_RESID)

    # Before trying to loop, it's crucial to check if any such elements actually exist on the screen.
    # The .exists attribute on a selector returns True if one or more elements matching the criteria are found, False otherwise.
    if thread_container_selector.exists:
        # If elements are found, .count tells us how many matching elements are currently on the screen.
        # We then loop from 0 up to (but not including) the count, to process each element individually.
        num_containers = thread_container_selector.count
        print(f"Found {num_containers} DM thread containers on screen. Checking each for unread status...")

        # Step 3 & 4: Iterate through each container and check for unread indicator & get username.
        for i in range(num_containers):
            # We get a specific UiObject (representing a single thread container) by using its index with the selector.
            # This 'container' is now a direct reference to one of the DM thread rows on the screen.
            container = thread_container_selector[i]

            # Now, within this specific 'container' (which is a UiObject),
            # we look for the unread indicator (e.g., the blue dot).
            # DM_THREAD_ITEM_UNREAD_INDICATOR_RESID (e.g., "com.instagram.android:id/thread_indicator_status_dot")
            # is the ID for that blue dot.
            # .child() is used here to find an element *inside* the current 'container' UiObject.
            unread_indicator = container.child(resourceId=DM_THREAD_ITEM_UNREAD_INDICATOR_RESID)

            # If the unread indicator (blue dot) exists within this container...
            if unread_indicator.exists:
                # ...then this thread is unread. We need to get the username.
                # DM_THREAD_ITEM_USERNAME_TEXT_RESID (e.g., "com.instagram.android:id/row_inbox_username")
                # is the ID for the TextView element that holds the username.
                username_element = container.child(resourceId=DM_THREAD_ITEM_USERNAME_TEXT_RESID)

                # If the username element exists...
                if username_element.exists:
                    username = username_element.info.get('text')  # Get the actual text content
                    if username:  # Ensure the username is not empty or None
                        print(f"Found unread thread with username: {username}")
                        unread_thread_usernames.append(username)
                    else:
                        print("WARN: Found unread indicator, but username element has no text.")
                else:
                    print("WARN: Found unread indicator, but could not find username element in the same container.")
            # If unread_indicator.exists is false for this container, it means this thread isn't marked as unread.
            # So, we just move to the next container in the loop.
    else:
        # This block executes if the thread_container_selector.exists was false,
        # meaning no DM thread containers were found on the screen at all.
        print("No DM thread containers found on the screen.")

    # Step 5: Return the list of usernames from unread threads.
    # If no unread threads were found, or if no containers were on screen, this list will be empty.
    if not unread_thread_usernames:
        print("No unread DM threads found among the visible items after checking all.")
    else:
        print(f"Finished checking. Found {len(unread_thread_usernames)} unread thread(s): {unread_thread_usernames}")

    return unread_thread_usernames