# uiautomator2_utils.py
# Helper functions for Instagram UI Automation.

import uiautomator2 as u2
import time
from datetime import datetime

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
DM_LIST_ACTUAL_SEARCH_EDITTEXT_RESID = "com.instagram.android:id/row_thread_composer_edittext" # Often an EditText appears after activating search. Find its ID.

DM_THREAD_ITEM_CONTAINER_RESID = "com.instagram.android:id/row_inbox_container"
DM_THREAD_ITEM_USERNAME_TEXT_RESID = "com.instagram.android:id/row_inbox_username"
DM_THREAD_ITEM_SNIPPET_TEXT_RESID = "com.instagram.android:id/row_inbox_digest"
DM_THREAD_ITEM_TIMESTAMP_TEXT_RESID = "com.instagram.android:id/row_inbox_timestamp"
DM_THREAD_ITEM_UNREAD_INDICATOR_RESID = "com.instagram.android:id/thread_indicator_status_dot"

DM_LIST_NEW_CHAT_BUTTON_DESC = "New message"  # Using content-desc

# III. Inside an Active DM Chat/Thread Screen
DM_CHAT_HEADER_USERNAME_TEXT_RESID = "com.instagram.android:id/header_subtitle"  # User confirmed this holds username in content-desc
DM_CHAT_MESSAGE_BUBBLE_CONTAINER_RESID = "com.instagram.android:id/direct_text_message_text_parent"
DM_CHAT_MESSAGE_TEXT_VIEW_RESID = "com.instagram.android:id/direct_text_message_text_view"
DM_CHAT_MESSAGE_SENDER_NAME_TEXT_RESID = "com.instagram.android:id/username"  # For groups

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
        time.sleep(5)


def go_to_home(d):
    ensure_instagram_open(d)
    home_button = d(resourceId=HOME_TAB_RESID)
    if not safe_click(home_button):
        print(f"WARN: Could not navigate to Home using ID '{HOME_TAB_RESID}'.")
    time.sleep(2)


def go_to_dm_list(d):
    ensure_instagram_open(d)
    go_to_home(d)
    dm_button = d(resourceId=DM_INBOX_ICON_RESID)
    if not safe_click(dm_button, timeout=10):
        print(f"ERROR: DM icon '{DM_INBOX_ICON_RESID}' not found on home screen.")
        return False
    print("Navigated to DM list.")
    time.sleep(3)
    if d(resourceId=DM_LIST_HEADER_TEXT_RESID).wait(timeout=5):
        return True
    print("WARN: DM list header not found after clicking DM icon.")
    return False


def _get_element_identifier(ui_object_info):
    """Helper to get content-desc or text from ui_object.info"""
    if not ui_object_info:
        return None
    return ui_object_info.get('contentDescription') or ui_object_info.get('text')


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


def get_messages_from_open_thread(d, bot_username, max_messages=20, max_scrolls_up=3):
    print("Fetching messages from open thread...")
    messages = []
    processed_msg_hashes = set()
    peer_username_el = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
    peer_username = "UnknownPeer"
    if peer_username_el.exists:
        peer_username_info = peer_username_el.info
        peer_username = _get_element_identifier(peer_username_info) or 'UnknownPeer'

    for i in range(max_scrolls_up + 1):
        message_bubbles = d(resourceId=DM_CHAT_MESSAGE_BUBBLE_CONTAINER_RESID)
        if not message_bubbles.exists:
            if i == 0: print("No message bubbles found in open thread.")
            break
        current_screen_messages = []
        for bubble_idx in range(message_bubbles.count):
            bubble = message_bubbles[bubble_idx]
            text_el = bubble.child(resourceId=DM_CHAT_MESSAGE_TEXT_VIEW_RESID)
            if text_el.exists:
                text = text_el.info['text']
                msg_hash = hash(text + str(bubble.info['bounds']))
                if msg_hash in processed_msg_hashes: continue
                processed_msg_hashes.add(msg_hash)
                screen_width = d.window_size()[0]
                is_outgoing = bubble.info['bounds']['left'] > screen_width / 2
                sender_ui_name = bot_username if is_outgoing else peer_username
                sender_name_explicit_el = bubble.child(resourceId=DM_CHAT_MESSAGE_SENDER_NAME_TEXT_RESID)
                if sender_name_explicit_el.exists:  # For group chats, sender name might be explicitly shown
                    sender_ui_name = sender_name_explicit_el.info['text']
                current_screen_messages.append({
                    "id": msg_hash, "user_id": sender_ui_name,
                    "text": text, "timestamp": datetime.now()
                })
        messages.extend(current_screen_messages)
        messages = list({m['id']: m for m in messages}.values())
        if len(messages) >= max_messages or i == max_scrolls_up: break
        d.swipe_ext("down", scale=0.5, duration=0.3)  # Swipe down on chat to scroll content up
        time.sleep(1.5)
    print(f"Fetched {len(messages)} messages from open thread.")
    return sorted(messages, key=lambda x: x['timestamp'])


def send_dm_in_open_thread(d, message_text):
    input_field = d(resourceId=DM_CHAT_INPUT_FIELD_RESID)
    send_button = d(resourceId=DM_CHAT_SEND_BUTTON_RESID)
    if not safe_click(input_field):
        print(f"ERROR: DM input field '{DM_CHAT_INPUT_FIELD_RESID}' not found.")
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
    time.sleep(2)
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
    time.sleep(4)  # Wait for search results to load

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
    profile_tab_button = d(resourceId=PROFILE_TAB_RESID)
    if not safe_click(profile_tab_button):
        print(f"ERROR: Profile tab/button '{PROFILE_TAB_RESID}' not found.")
        return False
    time.sleep(3)
    if d(resourceId=PROFILE_USERNAME_HEADER_TEXT_RESID, text=bot_username).wait(
            timeout=5):  # Assuming header text matches username
        print("Successfully on own profile.")
        return True
    print(f"ERROR: Navigated to profile tab, but header username does not match '{bot_username}'.")
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
    if header_el_verify.wait(timeout=7):  # Increased timeout
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

def search_and_open_dm_with_user(d, target_username, bot_username): # bot_username is not used here but good for consistency
    ensure_instagram_open(d)
    print(f"Trying to find/start DM with {target_username}...")
    if not go_to_dm_list(d):
        return False

    # 1. Try to find and open existing thread from DM list (quick check)
    if open_thread_by_username(d, target_username, max_scrolls=1):
        print(f"Opened existing DM thread with {target_username} from list.")
        return True

    # 2. If not found in initial DM list, attempt to create a new chat using the user-provided flow
    print(f"Thread with {target_username} not found in initial DM list. Attempting to create new chat following specified flow.")

    # Step 1: Click New message (has content desc)
    new_chat_btn = d(description=DM_LIST_NEW_CHAT_BUTTON_DESC) # Using content-desc as per your constant
    if not safe_click(new_chat_btn):
        print(f"ERROR: New chat button (desc: '{DM_LIST_NEW_CHAT_BUTTON_DESC}') not found in DM list.")
        return False
    print("Clicked 'New message' button. Waiting for New Chat screen...")
    time.sleep(2.5) # Allow time for the new chat screen to load

    # Step 2: Click and type the username in (com.instagram.android:id/search_edit_text)(resource id)
    # NEW_CHAT_TO_FIELD_INPUT_RESID is "com.instagram.android:id/search_edit_text"
    search_field_new_chat = d(resourceId=NEW_CHAT_TO_FIELD_INPUT_RESID)
    if not safe_click(search_field_new_chat): # Click to focus
        print(f"ERROR: 'To:' field ('{NEW_CHAT_TO_FIELD_INPUT_RESID}') not found or not clickable in new chat screen.")
        # If clicking fails, sometimes the field is already focused or needs a different interaction
        # As a fallback, try sending keys directly if element exists
        if not search_field_new_chat.exists:
            d.press("back") # Go back if field truly not found
            return False
        print(f"WARN: Could not click '{NEW_CHAT_TO_FIELD_INPUT_RESID}', attempting to send keys directly.")

    d.clear_text() # Clear any pre-existing text
    d.send_keys(target_username)
    print(f"Typed '{target_username}' into New Chat search. Waiting for results...")
    time.sleep(3.5) # Allow time for search results to populate

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
                    if safe_click(username_el): # Click the username TextView directly
                        user_selected_and_navigated = True
                        break # Exit loop once user is clicked
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
        d.press("back") # Go back from the new chat screen
        return False

    print(f"Clicked on {target_username}. Expecting to be on chat screen...")
    time.sleep(3.5) # Wait for the chat screen to fully load after selection

    # Step 4 & 5 are handled by verifying we are on the chat screen and then the main bot loop will use send_dm_in_open_thread
    # Verify we are on the chat screen with the correct user
    header_el_verify = d(resourceId=DM_CHAT_HEADER_USERNAME_TEXT_RESID)
    if header_el_verify.wait(timeout=7): # Increased timeout for screen transition
        header_identifier_verify = _get_element_identifier(header_el_verify.info)
        if header_identifier_verify and target_username.lower() in header_identifier_verify.lower():
            print(f"Successfully navigated to chat screen with {target_username}. Header: {header_identifier_verify}")
            # The main bot loop will now handle sending the message using send_dm_in_open_thread
            # if the 'send_message' function was called by Gemini.
            return True # Indicate that the chat is open and ready.
        else:
            print(f"WARN: Navigated to a chat screen, but header identifier '{header_identifier_verify}' does not match '{target_username}'.")
    else:
        print(f"ERROR: Did not land on the expected chat screen with {target_username} after selection (header element '{DM_CHAT_HEADER_USERNAME_TEXT_RESID}' not found or timed out).")

    # If verification fails, attempt to go back to a known state (DM list)
    print("Failed to verify chat screen for new chat. Returning to DM list.")
    d.press("back") # Try to go back from whatever screen it's on
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