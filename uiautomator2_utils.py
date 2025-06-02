import uiautomator2 as u2
import time
from datetime import datetime, timedelta
import json

# --- Constants for Instagram UI Automation ---
# These resource IDs and content descriptions are used to locate UI elements.
# They might need updates if the Instagram app UI changes.

# I. Main App Navigation Tabs
HOME_TAB_RESID = "com.instagram.android:id/feed_tab"
SEARCH_TAB_RESID = "com.instagram.android:id/search_tab"
CREATION_TAB_RESID = "com.instagram.android:id/creation_tab"
REELS_TAB_RESID = "com.instagram.android:id/clips_tab"
PROFILE_TAB_RESID = "com.instagram.android:id/profile_tab"

# II. DM (Direct Message) List Screen Elements
DM_INBOX_ICON_RESID = "com.instagram.android:id/action_bar_inbox_button"
DM_LIST_HEADER_TEXT_RESID = "com.instagram.android:id/action_bar_title_subtitle_container"  # Contains username/title
DM_LIST_SEARCH_ACTIVATION_ELEMENT_RESID = "com.instagram.android:id/animated_hints_text_layout"  # Text like "Search"
# TODO: Verify DM_LIST_SEARCH_INPUT_FIELD_RESID and DM_LIST_ACTUAL_SEARCH_EDITTEXT_RESID are correct and distinct if needed.
DM_LIST_SEARCH_INPUT_FIELD_RESID = "com.instagram.android:id/row_thread_composer_edittext"
DM_LIST_ACTUAL_SEARCH_EDITTEXT_RESID = "com.instagram.android:id/row_thread_composer_edittext"

DM_THREAD_ITEM_CONTAINER_RESID = "com.instagram.android:id/row_inbox_container"  # Container for each DM thread row
DM_THREAD_ITEM_USERNAME_TEXT_RESID = "com.instagram.android:id/row_inbox_username"
DM_THREAD_ITEM_SNIPPET_TEXT_RESID = "com.instagram.android:id/row_inbox_digest"
DM_THREAD_ITEM_TIMESTAMP_TEXT_RESID = "com.instagram.android:id/row_inbox_timestamp"
DM_THREAD_ITEM_UNREAD_INDICATOR_RESID = "com.instagram.android:id/thread_indicator_status_dot"  # Blue dot for unread

DM_LIST_NEW_CHAT_BUTTON_DESC = "New message"  # Accessibility description for new chat button

# III. Inside an Active DM Chat/Thread Screen
DM_CHAT_HEADER_USERNAME_TEXT_RESID = "com.instagram.android:id/header_title"  # Content-desc holds username
DM_CHAT_MESSAGE_BUBBLE_CONTAINER_RESID = "com.instagram.android:id/direct_text_message_text_parent"
DM_CHAT_MESSAGE_TEXT_VIEW_RESID = "com.instagram.android:id/direct_text_message_text_view"
DM_CHAT_MESSAGE_SENDER_NAME_TEXT_RESID = "com.instagram.android:id/username"  # For group chat sender names

DM_CHAT_INPUT_FIELD_RESID = "com.instagram.android:id/row_thread_composer_edittext"
DM_CHAT_SEND_BUTTON_RESID = "com.instagram.android:id/row_thread_composer_send_button_container"

# IV. New Chat Screen (after tapping New Message button)
NEW_CHAT_TO_FIELD_INPUT_RESID = "com.instagram.android:id/search_edit_text"  # "To:" or "Search" EditText
NEW_CHAT_USER_RESULT_ITEM_CONTAINER_RESID = "com.instagram.android:id/row_user_info_layout"
NEW_CHAT_USER_RESULT_USERNAME_TEXT_RESID = "com.instagram.android:id/row_user_secondary_name"  # User's @username
NEW_CHAT_USER_RESULT_FULLNAME_TEXT_RESID = "com.instagram.android:id/row_user_primary_name"  # User's full name
# TODO: Verify NEW_CHAT_USER_RESULT_SELECT_ELEMENT_RESID; it's very generic (FrameLayout).
# Consider if a more specific child (like a checkbox) is the actual clickable element.
NEW_CHAT_USER_RESULT_SELECT_ELEMENT_RESID = "android.widget.FrameLayout"
# Example: NEW_CHAT_USER_RESULT_SELECT_CHECKBOX_CLASS = "android.widget.CheckBox"

NEW_CHAT_CREATE_CHAT_BUTTON_TEXT = "Chat"  # Text on the button to finalize chat creation
# Example: NEW_CHAT_CREATE_CHAT_BUTTON_RESID = "com.instagram.android:id/next_button"

# V. User Profile Screen
PROFILE_USERNAME_HEADER_TEXT_RESID = "com.instagram.android:id/action_bar_title"  # Username at top of profile
PROFILE_FULL_NAME_TEXT_RESID = "com.instagram.android:id/profile_header_full_name_above_vanity"
PROFILE_BIO_TEXT_RESID = "com.instagram.android:id/profile_header_bio_text"
PROFILE_FOLLOWER_COUNT_TEXT_RESID = "com.instagram.android:id/profile_header_familiar_followers_value"
PROFILE_FOLLOWING_COUNT_TEXT_RESID = "com.instagram.android:id/profile_header_familiar_following_value"
PROFILE_FOLLOW_BUTTON_RESID = "com.instagram.android:id/profile_header_user_action_follow_button"

PROFILE_OPTIONS_MENU_BUTTON_DESC = "Options"  # Three-dot menu on user's profile
PROFILE_SEND_MESSAGE_OPTION_TEXT = "com.instagram.android:id/action_sheet_row_text_view"  # TextView for "Send message" in options menu

# VI. General Search Screen (after tapping bottom Search Tab)
GENERAL_SEARCH_INPUT_FIELD_RESID = "com.instagram.android:id/action_bar_search_edit_text"
GENERAL_SEARCH_USER_TAB_TEXT = "Accounts"  # Text for "Accounts" tab in search results

# TODO: Verify GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS, may need a more specific Resource ID.
GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS = "android.widget.LinearLayout"
# Example: GENERAL_SEARCH_RESULT_ITEM_CONTAINER_RESID = "com.instagram.android:id/row_search_user_container"
GENERAL_SEARCH_RESULT_USERNAME_TEXT_RESID = "com.instagram.android:id/row_search_user_username"

# Generic elements (use with caution, prefer specific IDs)
BACK_BUTTON_DESC = "Back"
OPTIONS_BUTTON_DESC = "Options"  # Generic options menu button

# --- End Constants ---

def safe_click(element, timeout=5):
    """Waits for an element and clicks it if found."""
    if element.wait(timeout=timeout):
        element.click()
        return True
    print(
        f"WARN: Element not found for click after {timeout}s: {element.selector if hasattr(element, 'selector') else 'Unknown element'}")
    return False

def ensure_instagram_open(d, package_name="com.instagram.android"):
    """Ensures Instagram is in the foreground, starting it if necessary."""
    current_app = d.app_current()
    if current_app['package'] != package_name:
        print(f"Instagram not in foreground. Current app: {current_app['package']}. Starting Instagram...")
        d.app_start(package_name, use_monkey=True)  # use_monkey=True can help bypass some startup issues
        time.sleep(3)  # Wait for app to load

def go_to_home(d):
    """Navigates to the Instagram home screen by pressing back multiple times then clicking the home tab."""
    ensure_instagram_open(d)
    max_back_presses = 6
    home_tab_visible = False
    print(f"Attempting to navigate to Home. Max back presses: {max_back_presses}.")

    for i in range(max_back_presses):
        if d(resourceId=HOME_TAB_RESID).exists:  # Check if home tab is already visible
            home_tab_visible = True
            print(f"Home tab found after {i} back press(es).")
            break
        print(f"Home tab not visible yet, pressing back (attempt {i + 1}/{max_back_presses}).")
        d.press("back")
        time.sleep(0.5)  # Allow UI to settle

    if not home_tab_visible:
        print(
            f"WARN: Home tab ({HOME_TAB_RESID}) was not found after {max_back_presses} back presses. Attempting to click it anyway.")

    home_button = d(resourceId=HOME_TAB_RESID)
    if not safe_click(home_button):
        print(f"ERROR: Failed to click the Home tab (ID: '{HOME_TAB_RESID}'). Bot may not be on home screen.")
    else:
        print("Successfully clicked the Home tab.")
    time.sleep(0.2)


def go_to_dm_list(d):
    """Navigates to the DM list screen from anywhere in the app."""
    # Check if already on DM list
    if d(resourceId=DM_LIST_HEADER_TEXT_RESID).exists and \
            (d(description=DM_LIST_NEW_CHAT_BUTTON_DESC).exists or d(
                resourceId=DM_LIST_SEARCH_ACTIVATION_ELEMENT_RESID).exists):
        print("Already on DM list screen.")
        return True

    ensure_instagram_open(d)
    go_to_home(d)  # Start from home screen to ensure main tabs are present
    dm_button = d(resourceId=DM_INBOX_ICON_RESID)
    if not safe_click(dm_button, timeout=10):  # Increased timeout for safety
        print(f"ERROR: DM icon '{DM_INBOX_ICON_RESID}' not found on home screen.")
        return False
    print("Clicked DM icon. Waiting for DM list to load.")
    time.sleep(0.5)  # Wait for DM list to transition
    if d(resourceId=DM_LIST_HEADER_TEXT_RESID).wait(timeout=5):
        print("Successfully navigated to DM list.")
        return True
    print("WARN: DM list header not found after clicking DM icon. Navigation may have failed.")
    return False


def _get_element_identifier(ui_object_info):
    """Helper to get contentDescription or text from a UiObject's info dictionary."""
    if not ui_object_info:
        return None
    return ui_object_info.get('contentDescription') or ui_object_info.get('text')


def open_thread_by_username(d, target_username_in_list, max_scrolls=3):
    """Opens an existing DM thread from the DM list by scrolling and matching username."""
    print(f"Searching for thread with '{target_username_in_list}' in DM list...")
    for i in range(max_scrolls + 1):  # Loop for scrolling
        thread_containers = d(resourceId=DM_THREAD_ITEM_CONTAINER_RESID)
        if thread_containers.exists:
            for container_idx in range(thread_containers.count):  # Loop through visible items
                container = thread_containers[container_idx]
                username_el = container.child(resourceId=DM_THREAD_ITEM_USERNAME_TEXT_RESID)
                if username_el.exists and target_username_in_list.lower() in username_el.info.get('text', '').lower():
                    print(f"Found thread container for '{target_username_in_list}'. Clicking.")
                    if safe_click(container):
                        time.sleep(0.8)  # Wait for chat to open
                        # Verify chat opened with correct user
                        header_el = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
                        if header_el.wait(timeout=5):
                            header_identifier = _get_element_identifier(header_el.info)
                            if header_identifier and target_username_in_list.lower() in header_identifier.lower():
                                print(f"Successfully opened thread, header matches: {header_identifier}")
                                return True
                            else:
                                print(
                                    f"WARN: Chat header identifier '{header_identifier}' does not match target '{target_username_in_list}'.")
                        else:
                            print(
                                f"WARN: Chat header '{DM_CHAT_HEADER_USERNAME_TEXT_RESID}' not found after opening thread.")
                        d.press("back")  # Go back if verification failed to allow re-try or next action
                        return False  # Verification failed
        if i < max_scrolls:
            print(f"Scrolling DM list (attempt {i + 1}/{max_scrolls})")
            d.swipe_ext("up", scale=1.8, duration=0.2)  # Swipe up to reveal more threads
            time.sleep(0.1)  # Wait for scroll to complete
    print(f"ERROR: Thread with '{target_username_in_list}' not found in DM list after {max_scrolls} scrolls.")
    return False


def get_threads_from_dm_list(d, bot_username, max_threads_to_fetch=20, max_scrolls=4):
    """Fetches thread summaries from the DM list. Currently not used by main bot logic."""
    print("Fetching threads from DM list...")
    threads_data = []
    seen_thread_titles = set()  # To avoid duplicates if UI refreshes during scroll
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
                if title in seen_thread_titles or title.lower() == bot_username.lower():  # Skip own thread or duplicates
                    continue
                seen_thread_titles.add(title)
                users_in_thread = [u.strip() for u in title.split(',')]  # Basic parsing for multiple users
                if bot_username not in users_in_thread and len(
                        users_in_thread) == 1:  # Add bot if it's a 1-on-1 chat not including bot
                    users_in_thread.append(bot_username)
                threads_data.append({
                    "id": title, "users": users_in_thread,
                    "last_message_snippet": snippet_el.info['text'] if snippet_el.exists else "",
                    "timestamp_approx": datetime.now(),  # Timestamp of fetch, not actual message
                })
                if len(threads_data) >= max_threads_to_fetch: break
        if len(threads_data) >= max_threads_to_fetch or i == max_scrolls: break
        d.swipe_ext("up", scale=0.8, duration=0.2)
        time.sleep(1.5)
    print(f"Fetched {len(threads_data)} thread summaries from DM list.")
    return threads_data

def get_messages_from_open_thread(d, bot_username, bot_sent_message_hashes, max_messages=20, max_scrolls_up=3):
    """
    Fetches messages currently visible in an open DM thread.
    NOTE: This version does not scroll up to fetch older messages due to complexity and unreliability.
    It processes messages visible on screen when called.
    """
    print("Fetching visible messages from open thread...")
    messages = []
    processed_msg_hashes = set()  # To avoid duplicates from same screen pass

    peer_username_el = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
    peer_username = "UnknownPeer"  # Default if header not found
    if peer_username_el.exists:
        peer_username_info = peer_username_el.info
        peer_username = _get_element_identifier(peer_username_info) or 'UnknownPeer'

    message_bubbles = d(resourceId=DM_CHAT_MESSAGE_BUBBLE_CONTAINER_RESID)
    if not message_bubbles.exists:
        print("No message bubbles found in open thread.")
    else:
        current_screen_messages = []
        for bubble_idx in range(message_bubbles.count):
            bubble = message_bubbles[bubble_idx]
            text_el = bubble.child(resourceId=DM_CHAT_MESSAGE_TEXT_VIEW_RESID)

            if text_el.exists:
                text = text_el.info['text']
                # Create a hash based on text and bounds to uniquely ID messages on screen
                msg_hash = hash(text + json.dumps(bubble.info['bounds'], sort_keys=True))

                if msg_hash in processed_msg_hashes: continue  # Skip if already processed in this pass
                processed_msg_hashes.add(msg_hash)

                screen_width = d.window_size()[0]
                text = text_el.info['text']
                msg_hash_for_tracking = hash(text)  # Calculate hash of the text content

                # Heuristic: outgoing messages (sent by bot) are usually on the right half.
                is_outgoing = bubble.info['bounds']['left'] > screen_width / 3

                # Determine sender_ui_name
                # Revised logic for sender_ui_name:
                explicit_sender_name_el = bubble.child(resourceId=DM_CHAT_MESSAGE_SENDER_NAME_TEXT_RESID)
                explicit_sender_name = None
                if explicit_sender_name_el.exists:
                    explicit_sender_name = explicit_sender_name_el.info['text']

                if msg_hash_for_tracking in bot_sent_message_hashes:
                    sender_ui_name = bot_username  # Verified self-sent
                elif explicit_sender_name and explicit_sender_name.lower() == bot_username.lower():
                    # If explicit name matches bot, and not caught by hash (e.g. old message)
                    sender_ui_name = bot_username
                elif explicit_sender_name:
                    sender_ui_name = explicit_sender_name  # Group chat message from another user
                elif is_outgoing:
                    sender_ui_name = bot_username  # UI heuristic for bot's message
                else:
                    sender_ui_name = peer_username  # Default to peer

                current_screen_messages.append({
                    "id": msg_hash,  # Unique ID for this scraped instance of the message
                    "user_id": sender_ui_name,  # Username of the sender
                    "text": text,
                    "timestamp": datetime.now()  # Timestamp of when this message was fetched
                })

        # Add messages from current screen to main list (avoiding duplicates based on hash for this call)
        existing_ids = {m['id'] for m in messages}
        for msg in current_screen_messages:
            if msg['id'] not in existing_ids:
                messages.append(msg)

        if len(messages) > max_messages:  # Trim if more than max_messages fetched
            messages = messages[:max_messages]  # Keep the ones at the top (likely older on screen)

    if not messages:
        print("No messages were fetched from the open thread.")
    else:
        print(f"Fetched {len(messages)} messages from open thread.")
    # Sort by timestamp (oldest first) as messages are scraped top-to-bottom of screen
    return sorted(messages, key=lambda x: x['timestamp'])

def send_dm_in_open_thread(d, message_text):
    """Sends a DM in the currently open chat thread."""
    input_field = d(resourceId=DM_CHAT_INPUT_FIELD_RESID)
    send_button = d(resourceId=DM_CHAT_SEND_BUTTON_RESID)

    if not input_field.wait(timeout=3):  # Wait for input field to be present
        print(f"ERROR: DM input field '{DM_CHAT_INPUT_FIELD_RESID}' not found.")
        return False
    if not safe_click(input_field):  # Click to focus
        print(f"ERROR: Could not click DM input field '{DM_CHAT_INPUT_FIELD_RESID}'.")
        return False
    d.clear_text()  # Clear any existing text
    time.sleep(0.2)
    d.send_keys(message_text)  # Type the message
    time.sleep(0.5)
    if not safe_click(send_button):
        print(f"ERROR: DM send button '{DM_CHAT_SEND_BUTTON_RESID}' not found or clickable.")
        return False
    print(f"DM sent (attempted): '{message_text[:30]}...'")
    time.sleep(1)  # Wait for message to send/UI to update
    return True


def go_to_user_profile(d, target_username):
    """Navigates to a user's profile page using Instagram's general search function."""
    ensure_instagram_open(d)
    print(f"Navigating to profile of '{target_username}' via general search...")
    go_to_home(d)  # Start from home
    if not safe_click(d(resourceId=SEARCH_TAB_RESID)):  # Click bottom search tab
        print(f"ERROR: Could not click search tab '{SEARCH_TAB_RESID}'.")
        return False
    time.sleep(2)  # Wait for search screen

    search_bar = d(resourceId=GENERAL_SEARCH_INPUT_FIELD_RESID)  # Top search input field
    if not safe_click(search_bar):  # Click to focus
        print(f"ERROR: General search input field '{GENERAL_SEARCH_INPUT_FIELD_RESID}' not found.")
        return False
    d.clear_text()
    d.send_keys(target_username)
    print(f"Typed '{target_username}' into general search. Waiting for results...")
    time.sleep(2)  # Wait for search results to load

    accounts_tab = d(text=GENERAL_SEARCH_USER_TAB_TEXT)  # "Accounts" tab
    if accounts_tab.exists:
        print(f"Clicking '{GENERAL_SEARCH_USER_TAB_TEXT}' tab.")
        safe_click(accounts_tab)
        time.sleep(2)  # Wait for tab content to load

    # Attempt to find the user in the search results.
    # GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS is a generic class, might need refinement.
    # TODO: Improve selector robustness for user search results if GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS is unreliable.
    user_results = d(className=GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS)
    if not user_results.exists:
        print(
            f"No user results found using class '{GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS}'. This selector might need adjustment.")
        return False

    for i in range(user_results.count):
        item = user_results[i]
        username_el = item.child(resourceId=GENERAL_SEARCH_RESULT_USERNAME_TEXT_RESID)
        if username_el.exists and target_username.lower() in username_el.info.get('text', '').lower():
            print(f"Found '{target_username}' in general search results. Clicking.")
            if safe_click(item):  # Click the container of the user item
                time.sleep(3)  # Wait for profile to load
                # Verify on profile page by checking the header username
                profile_header_el = d(resourceId=PROFILE_USERNAME_HEADER_TEXT_RESID)
                if profile_header_el.wait(timeout=5):
                    header_text = profile_header_el.info.get('text', '')
                    if target_username.lower() in header_text.lower():
                        print(f"Successfully navigated to '{target_username}'s profile.")
                        return True
                print(f"Clicked user, but profile header verification failed for '{target_username}'.")
                return False  # Header didn't match or wasn't found
    print(f"User '{target_username}' not found in the first page of general search results.")
    return False


def go_to_own_profile(d, bot_username):
    """Navigates to the bot's own profile page."""
    ensure_instagram_open(d)

    # If on DM list, go back to access main tabs
    if d(resourceId=DM_LIST_HEADER_TEXT_RESID).exists or d(description=DM_LIST_NEW_CHAT_BUTTON_DESC).exists:
        print("Currently on DM list, pressing back to reach main navigation tabs.")
        d.press("back")
        time.sleep(1.5)

    profile_tab_button = d(resourceId=PROFILE_TAB_RESID)  # Bottom profile tab
    if not safe_click(profile_tab_button):
        print(f"ERROR: Profile tab/button '{PROFILE_TAB_RESID}' not found.")
        return False
    time.sleep(3)  # Wait for profile to load

    # Verify own profile by checking username in header (specific ID for own profile)
    # Own profile username header ID might be different from other users' profile headers.
    profile_header_el = d(resourceId="com.instagram.android:id/action_bar_large_title_auto_size")
    if profile_header_el.wait(timeout=5):
        header_text = profile_header_el.info.get('text', '')
        if bot_username.lower() == header_text.lower():
            print("Successfully on own profile.")
            return True
    alt_profile_header_el = d(resourceId=PROFILE_USERNAME_HEADER_TEXT_RESID)  # Fallback to general profile header
    if alt_profile_header_el.wait(timeout=1) and bot_username.lower() in alt_profile_header_el.info.get('text',
                                                                                                        '').lower():
        print("Successfully on own profile (using alternative header ID).")
        return True
    print(
        f"ERROR: Navigated to profile tab, but header username does not match '{bot_username}'. Found: '{header_text if 'header_text' in locals() else 'N/A'}' or via alt ID.")
    return False


def get_bot_profile_info(d, bot_username):
    """Scrapes basic profile information (name, bio, follower/following count) for the bot's own account."""
    if not go_to_own_profile(d, bot_username):  # Ensure we are on the correct profile page
        print(f"Failed to navigate to own profile ({bot_username}) for scraping info.")
        return {}
    print(f"Scraping profile info for {bot_username}...")
    info = {"username": bot_username}  # Start with known username
    # Scrape various fields if they exist
    full_name_el = d(resourceId=PROFILE_FULL_NAME_TEXT_RESID)
    if full_name_el.exists: info["full_name"] = full_name_el.info.get('text')
    bio_el = d(resourceId=PROFILE_BIO_TEXT_RESID)
    if bio_el.exists: info["biography"] = bio_el.info.get('text')
    # TODO: Verify PROFILE_FOLLOWER_COUNT_TEXT_RESID and PROFILE_FOLLOWING_COUNT_TEXT_RESID are correct and robust.
    follower_el = d(resourceId=PROFILE_FOLLOWER_COUNT_TEXT_RESID)
    if follower_el.exists: info["follower_count"] = follower_el.info.get('text', '').replace(',', '')
    following_el = d(resourceId=PROFILE_FOLLOWING_COUNT_TEXT_RESID)
    if following_el.exists: info["following_count"] = following_el.info.get('text', '').replace(',', '')
    print(f"Bot profile info scraped: {info}")
    return info


def send_dm_from_profile(d, target_username, message_text):
    """
    Attempts to send a DM by navigating to a user's profile and using the 'Send message' option.
    NOTE: This function might be less reliable than search_and_open_dm_with_user.
    Its current implementation has an issue where the final send action is unreachable.
    """
    # TODO: Review if this function is still needed. If so, fix the control flow to ensure message sending.
    if not go_to_user_profile(d, target_username):
        print(f"Failed to navigate to '{target_username}'s profile. Cannot send DM from profile.")
        return False

    options_menu_btn = d(description=PROFILE_OPTIONS_MENU_BUTTON_DESC)
    if not safe_click(options_menu_btn):
        print(
            f"ERROR: Could not find/click profile options menu (desc: '{PROFILE_OPTIONS_MENU_BUTTON_DESC}') for '{target_username}'.")
        return False
    time.sleep(1.5)  # Wait for action sheet

    # Find "Send message" option in the action sheet by its text.
    # PROFILE_SEND_MESSAGE_OPTION_TEXT is the resource ID of the TextViews in the action sheet.
    send_message_option_el = None
    action_sheet_rows = d(resourceId=PROFILE_SEND_MESSAGE_OPTION_TEXT)
    if action_sheet_rows.exists:
        for i in range(action_sheet_rows.count):
            row_text_view = action_sheet_rows[i]
            if row_text_view.info:  # Check if info is available
                current_text = row_text_view.info.get('text', '').lower()
                print(f"Checking action sheet item: '{current_text}'")
                if "send message" in current_text:  # Match "send message" text
                    send_message_option_el = row_text_view
                    print(f"Found 'Send message' option: '{current_text}'")
                    break

    if not send_message_option_el:
        print(
            f"ERROR: Could not find 'Send message' text within elements with ID '{PROFILE_SEND_MESSAGE_OPTION_TEXT}'.")
        if d(resourceId=PROFILE_OPTIONS_MENU_BUTTON_DESC).exists:  # Check if profile options still visible
            print("Attempting to close action sheet with a back press.")
            d.press("back")
        return False

    if not safe_click(send_message_option_el):
        print(f"ERROR: Could not click the identified 'Send message' option.")
        if d(resourceId=PROFILE_OPTIONS_MENU_BUTTON_DESC).exists:
            print("Attempting to close action sheet with a back press after failed click.")
            d.press("back")
        return False

    print("Clicked 'Send message' option. Waiting for DM chat screen to open...")
    time.sleep(3.5)  # Wait for DM screen

    # Verify correct chat screen is open
    header_el_verify = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
    opened_correct_chat = False
    header_identifier_verify = None  # Initialize
    if header_el_verify.wait(timeout=5):  # Increased timeout
        header_identifier_verify = _get_element_identifier(header_el_verify.info)
        if header_identifier_verify and target_username.lower() in header_identifier_verify.lower():
            opened_correct_chat = True
            print(
                f"Successfully navigated to DM screen with '{target_username}' from profile. Header: '{header_identifier_verify}'")

    if not opened_correct_chat:
        print(f"ERROR: Opened a chat, but header ('{header_identifier_verify}') does not match '{target_username}'.")
        d.press("back")  # Go back if verification failed
        return False  # This return makes the send_dm_in_open_thread call below unreachable.

    # FIXME: The following line is currently unreachable due to the return False above.
    return send_dm_in_open_thread(d, message_text)


def search_and_open_dm_with_user(d, target_username, bot_username):
    """
    Finds an existing DM thread or creates a new one with target_username.
    'bot_username' is passed for consistency but not directly used in this function's logic.
    """
    ensure_instagram_open(d)
    print(f"Trying to find or start DM with '{target_username}'...")
    if not go_to_dm_list(d):  # Ensure on DM list screen
        return False

    # 1. Try to open existing thread from DM list (quick check)
    if open_thread_by_username(d, target_username, max_scrolls=1):
        print(f"Opened existing DM thread with '{target_username}' from list.")
        return True

    # 2. If not found, attempt to create a new chat
    print(f"Thread with '{target_username}' not found in initial DM list. Attempting to create new chat.")
    new_chat_btn = d(description=DM_LIST_NEW_CHAT_BUTTON_DESC)
    if not safe_click(new_chat_btn):
        print(f"ERROR: New chat button (desc: '{DM_LIST_NEW_CHAT_BUTTON_DESC}') not found in DM list.")
        return False
    print("Clicked 'New message' button. Waiting for New Chat screen...")
    time.sleep(1.5)

    search_input_selector = d(resourceId=NEW_CHAT_TO_FIELD_INPUT_RESID)  # "To:" field
    if not safe_click(search_input_selector):  # Click to focus
        print(f"WARN: safe_click failed for search input field '{NEW_CHAT_TO_FIELD_INPUT_RESID}'. Checking existence.")
        if not search_input_selector.exists:
            print(f"ERROR: Search input field '{NEW_CHAT_TO_FIELD_INPUT_RESID}' not found. Cannot type username.")
            d.press("back")  # Go back from new chat screen
            return False
        print(f"Field '{NEW_CHAT_TO_FIELD_INPUT_RESID}' exists despite click issues. Attempting to set text.")

    search_input_selector.set_text(target_username)  # Type username
    print(f"Set text '{target_username}' into New Chat search. Waiting for results...")
    time.sleep(2)  # Wait for results

    # Click the matching user from search results
    user_results_containers = d(resourceId=NEW_CHAT_USER_RESULT_ITEM_CONTAINER_RESID)
    user_selected_and_navigated = False
    if user_results_containers.exists:
        for i in range(user_results_containers.count):
            container = user_results_containers[i]
            username_el = container.child(resourceId=NEW_CHAT_USER_RESULT_USERNAME_TEXT_RESID)
            if username_el.exists:
                current_username_text = username_el.info.get('text', '').lower()
                print(f"Checking search result: '{current_username_text}'")
                if target_username.lower() == current_username_text:  # Exact match
                    print(f"Found exact match for '{target_username}'. Clicking user entry.")
                    # Click the username element or its container.
                    # TODO: Confirm if NEW_CHAT_USER_RESULT_SELECT_ELEMENT_RESID is needed or if clicking username_el/container is enough.
                    if safe_click(username_el) or safe_click(container):
                        user_selected_and_navigated = True
                        break
                    else:
                        print(f"ERROR: Failed to click username or container for '{target_username}'.")
                        continue  # Try next if click fails but more results exist

    if not user_selected_and_navigated:
        print(f"ERROR: User '{target_username}' not found in new chat search results, or failed to click.")
        d.press("back")  # Go back from new chat screen
        return False

    print(f"Clicked on '{target_username}'. Expecting to be on chat screen...")
    time.sleep(2)  # Wait for chat screen to load

    # Verify on chat screen with correct user
    header_el_verify = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
    if header_el_verify.wait(timeout=7):
        header_identifier_verify = _get_element_identifier(header_el_verify.info)
        if header_identifier_verify and target_username.lower() in header_identifier_verify.lower():
            print(
                f"Successfully navigated to chat screen with '{target_username}'. Header: '{header_identifier_verify}'")
            return True  # Chat is open and ready
        else:
            print(
                f"WARN: Navigated to a chat screen, but header ('{header_identifier_verify}') does not match '{target_username}'.")
    else:
        print(
            f"ERROR: Did not land on expected chat screen with '{target_username}' (header '{DM_CHAT_HEADER_USERNAME_TEXT_RESID}' not found).")

    # Error recovery: attempt to return to a known state
    print("Failed to verify chat screen for new chat. Attempting to return to DM list.")
    # TODO: Make this error recovery more robust. Multiple back presses might be needed.
    d.press("back")
    time.sleep(0.5)
    # current_activity = d.app_current().get('activity') # For debugging what screen it's on
    # print(f"Current activity after first back: {current_activity}")
    return False


def return_to_dm_list_from_thread(d):
    """Attempts to return to DM list from an open thread, with verification."""
    print("Attempting to return to DM list from an open thread by pressing back...")
    d.press("back")
    time.sleep(1.5)  # Allow UI to transition

    # Verify return to DM list by checking for known elements
    dm_list_header = d(resourceId=DM_LIST_HEADER_TEXT_RESID)
    new_chat_button = d(description=DM_LIST_NEW_CHAT_BUTTON_DESC)  # Alternative check

    if dm_list_header.wait(timeout=3) or new_chat_button.wait(timeout=3):
        print("Successfully returned to DM list screen.")
        return True
    else:
        print(
            "WARN: After pressing back, DM list screen elements not immediately found. Attempting full go_to_dm_list as fallback.")
        return go_to_dm_list(d)  # Fallback to more comprehensive navigation if simple back fails


def check_for_unread_dm_threads(d_device):
    """
    On the DM list screen, checks visible threads for an unread indicator (blue dot).
    Returns a list of usernames from threads marked as unread.
    """
    print("Checking for unread DM threads on current screen...")
    unread_thread_usernames = []

    if not go_to_dm_list(d_device):  # Ensure we are on the DM list screen
        print("ERROR: Could not navigate to DM list. Cannot check for unread threads.")
        return []

    thread_container_selector = d_device(resourceId=DM_THREAD_ITEM_CONTAINER_RESID)

    if thread_container_selector.exists:
        num_containers = thread_container_selector.count
        print(f"Found {num_containers} DM thread containers on screen. Checking each for unread status...")

        for i in range(num_containers):
            container = thread_container_selector[i]
            # Check for the unread indicator (blue dot) within this thread container
            unread_indicator = container.child(resourceId=DM_THREAD_ITEM_UNREAD_INDICATOR_RESID)

            if unread_indicator.exists:
                # If unread, get the username from the same container
                username_element = container.child(resourceId=DM_THREAD_ITEM_USERNAME_TEXT_RESID)
                if username_element.exists:
                    username = username_element.info.get('text')
                    if username:
                        print(f"Found unread thread with username: {username}")
                        unread_thread_usernames.append(username)
                    else:
                        print("WARN: Found unread indicator, but username element has no text.")
                else:
                    print("WARN: Found unread indicator, but could not find username element in the same container.")
    else:
        print("No DM thread containers found on the screen.")

    if not unread_thread_usernames:
        print("No unread DM threads found among the visible items.")
    else:
        print(f"Finished checking. Found {len(unread_thread_usernames)} unread thread(s): {unread_thread_usernames}")

    return unread_thread_usernames