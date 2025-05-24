import datetime
import Main
import config  # To potentially modify config values if Main.py uses them directly
from unittest.mock import patch
import types  # Added for SimpleNamespace

SIMULATED_OWNER_USERNAME = "sim_owner"
SIMULATED_BOT_USERNAME = "sim_bot"
# Static usernames for other simulated users, can be constants too if preferred
ALICE_USERNAME = "alice"
BOB_USERNAME = "bob"


class MockInstagrapiClient:
    # Class attributes for fixed PKs and other user details if not customized by instance
    # Or, generate PKs dynamically if usernames are fully dynamic
    USER_PK_MAP = {
        SIMULATED_OWNER_USERNAME: 1001,
        SIMULATED_BOT_USERNAME: 1002,
        ALICE_USERNAME: 1003,
        BOB_USERNAME: 1004,
    }

    DEFAULT_USER_PROFILES = {
        ALICE_USERNAME: {
            "full_name": "Alice Wonderland", "follower_count": 200, "is_private": False, "is_verified": False,
            "biography": "Curiouser and curiouser!"
        },
        BOB_USERNAME: {
            "full_name": "Bob The Builder", "follower_count": 300, "is_private": True, "is_verified": False,
            "biography": "Can we fix it? Yes, we can!"
        }
    }

    def __init__(self, bot_username=SIMULATED_BOT_USERNAME, owner_username=SIMULATED_OWNER_USERNAME):
        self.OWNER_USERNAME = owner_username
        self.BOT_USERNAME = bot_username

        # Dynamically create simulated_users for this instance
        self.simulated_users = {
            self.OWNER_USERNAME: {
                "pk": self.USER_PK_MAP.get(self.OWNER_USERNAME, 1001),  # Fallback PK if not in map
                "username": self.OWNER_USERNAME,
                "full_name": "Simulated Owner",
                "follower_count": 100,
                "is_private": False,
                "is_verified": False,
                "biography": "Just a simulated owner.",
            },
            self.BOT_USERNAME: {
                "pk": self.USER_PK_MAP.get(self.BOT_USERNAME, 1002),  # Fallback PK
                "username": self.BOT_USERNAME,
                "full_name": "Simulated Bot",
                "follower_count": 50,
                "is_private": False,
                "is_verified": False,
                "biography": "Beep boop, I am a bot.",
            },
            ALICE_USERNAME: {
                "pk": self.USER_PK_MAP[ALICE_USERNAME],
                "username": ALICE_USERNAME,
                **self.DEFAULT_USER_PROFILES[ALICE_USERNAME]
            },
            BOB_USERNAME: {
                "pk": self.USER_PK_MAP[BOB_USERNAME],
                "username": BOB_USERNAME,
                **self.DEFAULT_USER_PROFILES[BOB_USERNAME]
            }
        }

        self.bot_id = None  # Set in login_by_sessionid
        self.owner_id = None  # Set in login_by_sessionid
        self.username = None  # Bot's username, set in login_by_sessionid
        self.message_id_counter = 0
        self.threads = {}
        self.currently_active_thread_for_input = None  # Added for thread selection
        # Note: Thread pre-population moved to login_by_sessionid to ensure IDs are set

    def _get_user_by_pk(self, pk):
        pk = int(pk)
        for user_data in self.simulated_users.values():
            if user_data["pk"] == pk:
                return user_data
        return None

    def _get_user_by_username(self, username):
        return self.simulated_users.get(username)

    def _create_mock_user_object(self, user_data_dict):  # Renamed param for clarity
        if not user_data_dict:
            return None

        mock_attributes = {
            "pk": user_data_dict.get("pk"),
            "username": user_data_dict.get("username"),
            "full_name": user_data_dict.get("full_name"),
            "follower_count": user_data_dict.get("follower_count"),
            "is_private": user_data_dict.get("is_private", False),
            "is_verified": user_data_dict.get("is_verified", False),
            "biography": user_data_dict.get("biography", "")
        }
        return types.SimpleNamespace(**mock_attributes)

    def login_by_sessionid(self, session_id):
        # Uses instance specific BOT_USERNAME and OWNER_USERNAME
        self.bot_id = self.simulated_users[self.BOT_USERNAME]["pk"]
        self.owner_id = self.simulated_users[self.OWNER_USERNAME]["pk"]
        self.username = self.BOT_USERNAME  # The client logs in as the bot

        # Add this line:
        self.user_id = self.bot_id

        print(f"Mock login successful as {self.username} (ID: {self.user_id})")

        # Now that IDs are set, pre-populate threads if empty
        if not self.threads:
            owner_user_obj = self._create_mock_user_object(self.simulated_users[self.OWNER_USERNAME])
            bot_user_obj = self._create_mock_user_object(self.simulated_users[self.BOT_USERNAME])
            alice_user_obj = self._create_mock_user_object(self.simulated_users[ALICE_USERNAME])

            if owner_user_obj and bot_user_obj and alice_user_obj:
                mock_thread_1_id = "mock_thread_1"
                self.threads[mock_thread_1_id] = {
                    "id": mock_thread_1_id,
                    "users": [bot_user_obj, owner_user_obj, alice_user_obj],
                    "messages": [
                        types.SimpleNamespace(**{
                            "id": self._get_next_message_id(),
                            "user_id": owner_user_obj.pk if owner_user_obj else None,
                            "thread_id": mock_thread_1_id,
                            "text": "Welcome to the simulated chat!",
                            "timestamp": datetime.datetime.now() - datetime.timedelta(minutes=5),
                            "item_type": "text",
                        })
                    ],
                }
                mock_thread_2_id = "mock_thread_2"  # For owner and Bob
                bob_user_obj = self._create_mock_user_object(self.simulated_users[BOB_USERNAME])
                if bob_user_obj:
                    self.threads[mock_thread_2_id] = {
                        "id": mock_thread_2_id,
                        "users": [bot_user_obj, owner_user_obj, bob_user_obj],
                        "messages": [],
                    }

    def _get_next_message_id(self):
        self.message_id_counter += 1
        return str(self.message_id_counter)

    def user_info_v1(self, user_id_str):  # user_id_str is actually user_id (pk)
        try:
            user_id = int(user_id_str)  # user_id_str is pk
        except ValueError:
            return None
        user_data = self._get_user_by_pk(user_id)
        return self._create_mock_user_object(user_data)

    def user_info_by_username_v1(self, username):
        user_data = self._get_user_by_username(username)
        return self._create_mock_user_object(user_data)

    def user_id_from_username(self, username):
        user_data = self._get_user_by_username(username)
        if user_data:
            return user_data["pk"]
        return None

    def direct_send(self, text, user_ids=None, thread_ids=None):
        print("\n--- SIMULATOR: Outgoing Message (direct_send) ---")
        print(f"Attempting to send: '{text}'")
        if user_ids:
            print(f"To User IDs: {user_ids}")
        if thread_ids:
            print(f"To Thread IDs: {thread_ids}")

        if thread_ids and isinstance(thread_ids, list):
            for thread_id_target in thread_ids:
                if thread_id_target in self.threads:
                    new_msg = {
                        "id": self._get_next_message_id(),
                        "user_id": self.bot_id,
                        "thread_id": thread_id_target,
                        "text": text,
                        "timestamp": datetime.datetime.now(),
                        "item_type": "text",
                    }
                    self.threads[thread_id_target]["messages"].append(new_msg)
                    print(
                        f"[SIMULATOR] Message from bot (via direct_send) added to virtual history of thread '{thread_id_target}'.")
                else:
                    print(f"[SIMULATOR] Thread ID '{thread_id_target}' not found for direct_send.")
        elif user_ids:
            # This part remains less implemented as it's not the primary focus of direct_messages
            print(
                f"[SIMULATOR] direct_send to user_ids {user_ids} - thread finding/creation not fully implemented here.")
        print("--- SIMULATOR: End Outgoing Message (direct_send) ---\n")

    def user_followers(self, user_id_str, amount=10):  # user_id_str is pk
        try:
            user_id = int(user_id_str)
        except ValueError:
            return {}
        user_data = self._get_user_by_pk(user_id)
        if not user_data:
            return {}

        followers = {}
        if user_data["username"] == self.OWNER_USERNAME:
            alice_data = self.simulated_users[ALICE_USERNAME]
            followers[alice_data["pk"]] = self._create_mock_user_object(alice_data)
        elif user_data["username"] == self.BOT_USERNAME:
            bob_data = self.simulated_users[BOB_USERNAME]
            followers[bob_data["pk"]] = self._create_mock_user_object(bob_data)

        return dict(list(followers.items())[:amount])

    def user_following(self, user_id_str, amount=10):  # user_id_str is pk
        try:
            user_id = int(user_id_str)
        except ValueError:
            return {}
        user_data = self._get_user_by_pk(user_id)
        if not user_data:
            return {}

        following = {}
        if user_data["username"] == self.OWNER_USERNAME:
            bob_data = self.simulated_users[BOB_USERNAME]
            following[bob_data["pk"]] = self._create_mock_user_object(bob_data)
        elif user_data["username"] == self.BOT_USERNAME:
            alice_data = self.simulated_users[ALICE_USERNAME]
            following[alice_data["pk"]] = self._create_mock_user_object(alice_data)

        return dict(list(following.items())[:amount])

    def list_simulated_threads_for_user_selection(self):
        """Prints available threads and returns a mapping for user selection."""
        print("\n--- SIMULATOR: Thread Selection ---")
        print("Available Threads for Interaction:")
        if not self.threads:
            print("  No simulated threads available.")
            print("-----------------------------------")
            return {}

        selection_map = {}
        for i, (thread_id, thread_data) in enumerate(self.threads.items()):
            # User objects (u) are SimpleNamespace, so access username via attribute
            user_names = [u.username for u in thread_data.get("users", [])]
            print(f"  {i + 1}. Thread ID: '{thread_id}' (Users: {', '.join(user_names)})")
            selection_map[str(i + 1)] = thread_id
        print("-----------------------------------")
        return selection_map

    def direct_threads(self, amount=10):
        if self.owner_id is None:
            print("[SIMULATOR] Error: Owner ID not set. Call login_by_sessionid first.")
            return []

        owner_user_data = self._get_user_by_pk(self.owner_id)
        if not owner_user_data:
            print("[SIMULATOR] Error: Owner user data not found.")
            return []
        inviter_obj = self._create_mock_user_object(owner_user_data)

        mock_threads_list = []
        for thread_id, thread_data in self.threads.items():
            # Ensure users in thread_data['users'] are converted to SimpleNamespace if accessed with dot notation later
            # The current direct_threads implementation correctly uses _create_mock_user_object for users,
            # so they will be SimpleNamespace objects.
            users_list = [u for u in
                          thread_data['users']]  # Users should already be SimpleNamespace from pre-population

            mock_thread_obj = {
                "id": thread_id,
                "users": users_list,
                "last_activity_at": datetime.datetime.now(),
                "viewer_id": self.bot_id,  # This is just a pk (int)
                "inviter": inviter_obj,  # This should be a SimpleNamespace object
                "items": thread_data.get("messages", [])[-amount:]
            }
            # Convert to SimpleNamespace if Main.py expects thread objects to also have attribute access
            # For now, direct_threads returns a list of dicts, which Main.py seems to handle.
            # If Main.py expects thread.users[0].username etc., then users_list must contain SimpleNamespaces.
            # This is handled by how threads are populated in login_by_sessionid using _create_mock_user_object.
            mock_threads_list.append(types.SimpleNamespace(**mock_thread_obj))
            if len(mock_threads_list) >= amount:
                break
        return mock_threads_list

    def direct_messages(self, thread_id, amount=20, cursor=None):
        # Check if this thread is selected for input
        if not self.currently_active_thread_for_input or thread_id != self.currently_active_thread_for_input:
            return []

        print("\n==============================================")
        print("=== SIMULATOR: New Message Input Cycle ===")
        print(f"=== Target Thread for this cycle: {thread_id} ===")
        print("==============================================")

        if thread_id not in self.threads:
            print(f"[SIMULATOR] Error: Actively selected thread ID '{thread_id}' not found in self.threads.")
            return []

        print(f"\n--- Recent Messages in Thread '{thread_id}' (max 5 shown) ---")
        if self.threads[thread_id]["messages"]:
            for msg in self.threads[thread_id]["messages"][-5:]:
                sender_username = "UnknownSender"
                # msg.user_id is used to fetch the user dict
                sender_user_data_dict = self._get_user_by_pk(msg.user_id)
                if sender_user_data_dict:
                    sender_username = sender_user_data_dict["username"]  # Accessing username from the dict

                # Access timestamp and text as attributes from SimpleNamespace msg object
                timestamp_str = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(msg.timestamp,
                                                                                          datetime.datetime) else str(
                    msg.timestamp)
                print(f"  [{timestamp_str}] {sender_username}: {msg.text}")
        else:
            print("  No messages in this thread yet.")
        print("----------------------------------------------------")

        sim_user_names_prompt = f"{self.OWNER_USERNAME}, {ALICE_USERNAME}, {BOB_USERNAME}, or '{self.BOT_USERNAME}'"
        sender_username_input = input(
            f"[PROMPT] Enter sender username for thread '{thread_id}' (e.g., {sim_user_names_prompt}, or 'quit'/'exit'): ").strip()

        if sender_username_input.lower() in ['quit', 'exit']:
            print(
                f"[SIMULATOR] User chose to quit interaction for thread '{thread_id}'. Returning to thread selection.")
            raise SystemExit(f"User quit interaction for thread {thread_id}")

        sender_user_data = self._get_user_by_username(sender_username_input)
        if not sender_user_data:
            print(
                f"[SIMULATOR] Error: User '{sender_username_input}' not found in simulated users for thread '{thread_id}'.")
            return []

        message_text = input(
            f"[PROMPT] Enter message for thread '{thread_id}' (from {sender_username_input}): ").strip()

        if not message_text:
            print("[SIMULATOR] Message text cannot be empty.")
            return []

        new_message_id = self._get_next_message_id()
        sender_pk = sender_user_data["pk"]

        message_attributes = {
            "id": new_message_id,
            "user_id": sender_pk,  # This is the pk of the sender (e.g., alice, sim_owner)
            "thread_id": thread_id,  # This is the thread_id of the current thread being processed
            "text": message_text,
            "timestamp": datetime.datetime.now(),  # This is a datetime object
            "item_type": "text"
            # Add any other attributes Main.py might expect from a message object
        }
        new_message_obj = types.SimpleNamespace(**message_attributes)

        if thread_id in self.threads:
            # Storing the SimpleNamespace object directly in the messages list
            self.threads[thread_id]["messages"].append(new_message_obj)
            print(
                f"[SIMULATOR] CLI input processed. Message from '{sender_username_input}' (User ID: {sender_pk}) added to virtual history of thread '{thread_id}'.")
        else:
            print(f"[SIMULATOR] Error: Thread ID '{thread_id}' disappeared unexpectedly during message sending.")
            return []

        return [new_message_obj]


if __name__ == '__main__':
    print(">>> SIMULATOR: Starting Instagram Bot Simulation...")
    print("=====================================================")

    mock_client = MockInstagrapiClient(
        bot_username=SIMULATED_BOT_USERNAME,
        owner_username=SIMULATED_OWNER_USERNAME
    )

    Main.cl = mock_client
    print(f">>> SIMULATOR: Patched Main.cl with MockInstagrapiClient instance.")

    Main.OWNER_USERNAME = SIMULATED_OWNER_USERNAME
    config.OWNER_USERNAME = SIMULATED_OWNER_USERNAME
    print(f">>> SIMULATOR: Updated Main.OWNER_USERNAME and config.OWNER_USERNAME to '{SIMULATED_OWNER_USERNAME}'.")

    print("\n>>> SIMULATOR: Calling Main.login()...")
    if Main.login():
        print("<<< SIMULATOR: Main.login() successful (simulated).")
        print("\n>>> SIMULATOR: Calling Main.print_user_info()...")
        Main.print_user_info()
        print("<<< SIMULATOR: Main.print_user_info() finished.")

        while True:
            active_threads_map = mock_client.list_simulated_threads_for_user_selection()
            if not active_threads_map:
                print(">>> SIMULATOR: No simulated threads available. Exiting simulation.")
                break

            user_choice = input(
                "[PROMPT] Enter thread number to interact with (or 'quit' to exit simulation): ").strip().lower()
            if user_choice == 'quit':
                print(">>> SIMULATOR: User chose to quit simulation.")
                break

            chosen_thread_id = active_threads_map.get(user_choice)
            if not chosen_thread_id:
                print(">>> SIMULATOR: Invalid thread selection. Please try again.")
                continue

            mock_client.currently_active_thread_for_input = chosen_thread_id
            print(f"\n>>> SIMULATOR: Selected thread for interaction: {chosen_thread_id}.")
            print(
                f">>> SIMULATOR: Handing control to Main.auto_respond() for one cycle (or until 'quit' from sender prompt).")
            print(
                "             (You will be prompted for sender and message ONLY when this thread is processed by Main.auto_respond)")

            try:
                Main.auto_respond()
            except SystemExit as e:
                print(
                    f"\n<<< SIMULATOR: Returned from Main.auto_respond() for thread '{chosen_thread_id}'. Reason: {e}")
                print("             Returning to thread selection menu...")
            except Exception as e:
                print(
                    f"\n<<< SIMULATOR: An unexpected error occurred during Main.auto_respond for thread '{chosen_thread_id}': {e}")
                import traceback

                traceback.print_exc()

            mock_client.currently_active_thread_for_input = None
            print("=====================================================")
    else:
        print("<<< SIMULATOR: Main.login() failed (simulated). Exiting simulation.")

    print("\n>>> SIMULATOR: Simulation Ended Gracefully.")
    print("=====================================================")
