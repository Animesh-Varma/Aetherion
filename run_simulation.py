import datetime
import Main  # Assuming your main file is Main.py
import config
from unittest.mock import patch


# Define SimpleMockObject at the beginning of run_simulation.py
class SimpleMockObject:
    def __init__(self, **data):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, SimpleMockObject(**value))  # Recursively convert dicts
            elif isinstance(value, list):
                # Recursively convert dicts within lists
                setattr(self, key, [SimpleMockObject(**i) if isinstance(i, dict) else i for i in value])
            else:
                setattr(self, key, value)

    def __getattr__(self, name):
        # This allows an object to behave more like a dict for __getitem__ if needed,
        # but primarily for attribute access.
        # Returns None if attribute is missing, similar to some instagrapi optional fields.
        # If an attribute is genuinely expected (like .pk in this case) and missing
        # from the mock data, this will result in 'NoneType' object has no attribute 'pk',
        # which would indicate an issue in the mock data itself.
        return self.__dict__.get(name)

    def __repr__(self):
        return f"SimpleMockObject({self.__dict__})"


SIMULATED_OWNER_USERNAME = "sim_owner"
SIMULATED_BOT_USERNAME = "sim_bot"
ALICE_USERNAME = "alice"
BOB_USERNAME = "bob"


class MockInstagrapiClient:
    USER_PK_MAP = {
        SIMULATED_OWNER_USERNAME: 1001,
        SIMULATED_BOT_USERNAME: 1002,
        ALICE_USERNAME: 1003,
        BOB_USERNAME: 1004,
    }

    DEFAULT_USER_PROFILES = {
        ALICE_USERNAME: {
            "pk": USER_PK_MAP[ALICE_USERNAME],  # Ensure pk is part of the dict
            "username": ALICE_USERNAME,
            "full_name": "Alice Wonderland", "follower_count": 200, "is_private": False, "is_verified": False
        },
        BOB_USERNAME: {
            "pk": USER_PK_MAP[BOB_USERNAME],  # Ensure pk is part of the dict
            "username": BOB_USERNAME,
            "full_name": "Bob The Builder", "follower_count": 300, "is_private": True, "is_verified": False
        }
    }

    def __init__(self, bot_username=SIMULATED_BOT_USERNAME, owner_username=SIMULATED_OWNER_USERNAME):
        self.OWNER_USERNAME = owner_username
        self.BOT_USERNAME = bot_username

        # Internal storage of user data as dictionaries
        self.simulated_users = {
            self.OWNER_USERNAME: {
                "pk": self.USER_PK_MAP.get(self.OWNER_USERNAME, 1001),
                "username": self.OWNER_USERNAME,
                "full_name": "Simulated Owner",
                "follower_count": 100,
                "is_private": False,
                "is_verified": False,
            },
            self.BOT_USERNAME: {
                "pk": self.USER_PK_MAP.get(self.BOT_USERNAME, 1002),
                "username": self.BOT_USERNAME,
                "full_name": "Simulated Bot",
                "follower_count": 50,
                "is_private": False,
                "is_verified": False,
            },
            ALICE_USERNAME: self.DEFAULT_USER_PROFILES[ALICE_USERNAME],
            BOB_USERNAME: self.DEFAULT_USER_PROFILES[BOB_USERNAME]
        }

        self.bot_id = None
        self.owner_id = None
        self.username = None
        self.user_id = None  # Will be set to bot_id after login
        self.message_id_counter = 0
        self.threads = {}  # Internal storage of thread data as dictionaries

    def _get_user_by_pk(self, pk):
        pk = int(pk)
        for user_data_dict in self.simulated_users.values():
            if user_data_dict["pk"] == pk:
                return user_data_dict  # Return raw dict
        return None

    def _get_user_by_username(self, username):
        return self.simulated_users.get(username)  # Return raw dict

    def _create_mock_user_object(self, user_data_dict):
        if not user_data_dict:
            return None
        # *** CRITICAL CHANGE: Return SimpleMockObject instead of dict ***
        return SimpleMockObject(**user_data_dict)

    def login_by_sessionid(self, session_id):
        bot_user_data = self.simulated_users[self.BOT_USERNAME]
        owner_user_data = self.simulated_users[self.OWNER_USERNAME]

        self.bot_id = bot_user_data["pk"]
        self.owner_id = owner_user_data["pk"]
        self.username = self.BOT_USERNAME
        self.user_id = self.bot_id  # Main.py expects cl.user_id to be set
        print(f"Mock login successful as {self.username} (ID: {self.bot_id})")

        if not self.threads:  # Pre-populate threads using raw dicts for internal storage
            alice_user_data = self.simulated_users[ALICE_USERNAME]
            bob_user_data = self.simulated_users[BOB_USERNAME]

            mock_thread_1_id = "mock_thread_1"
            self.threads[mock_thread_1_id] = {
                "id": mock_thread_1_id,
                "users": [bot_user_data, owner_user_data, alice_user_data],  # List of user dicts
                "messages": [
                    {  # message dict
                        "id": self._get_next_message_id(),
                        "user_id": owner_user_data["pk"],
                        "thread_id": mock_thread_1_id,
                        "text": "Welcome to the simulated chat!",
                        "timestamp": datetime.datetime.now() - datetime.timedelta(minutes=5),
                        "item_type": "text",
                    }
                ],
            }
            mock_thread_2_id = "mock_thread_2"
            self.threads[mock_thread_2_id] = {
                "id": mock_thread_2_id,
                "users": [bot_user_data, owner_user_data, bob_user_data],  # List of user dicts
                "messages": [],
            }

    def _get_next_message_id(self):
        self.message_id_counter += 1
        return str(self.message_id_counter)

    def user_info_v1(self, user_id_input):  # user_id_input is PK (can be str or int)
        user_data_dict = self._get_user_by_pk(int(str(user_id_input)))  # Robust conversion
        return self._create_mock_user_object(user_data_dict)  # Returns SimpleMockObject

    def user_info_by_username_v1(self, username):
        user_data_dict = self._get_user_by_username(username)
        return self._create_mock_user_object(user_data_dict)  # Returns SimpleMockObject

    def user_id_from_username(self, username):
        user_data = self._get_user_by_username(username)
        if user_data:
            return user_data["pk"]  # Returns int PK
        return None

    def direct_send(self, text, user_ids=None, thread_ids=None):
        print(f"[SIMULATOR] Direct send called. Text: '{text}', User IDs: {user_ids}, Thread IDs: {thread_ids}")
        if thread_ids and isinstance(thread_ids, list):
            for thread_id in thread_ids:
                if thread_id in self.threads:
                    new_msg_dict = {  # Store as dict internally
                        "id": self._get_next_message_id(),
                        "user_id": self.bot_id,
                        "thread_id": thread_id,
                        "text": text,
                        "timestamp": datetime.datetime.now(),
                        "item_type": "text",
                    }
                    self.threads[thread_id]["messages"].append(new_msg_dict)
                    print(f"[SIMULATOR] Message from bot added to thread {thread_id}: {text}")
                else:
                    print(f"[SIMULATOR] Thread ID {thread_id} not found for direct_send.")
        elif user_ids:
            if self.owner_id in user_ids:
                print(f"[SIMULATOR] Owner ({self.OWNER_USERNAME}) was targeted by a direct_send with text: {text}")
            else:
                print(
                    f"[SIMULATOR] direct_send to user_ids {user_ids} - thread finding/creation not fully implemented here.")

    def user_followers(self, user_id_input, amount=10):
        try:
            user_id = int(str(user_id_input))
        except ValueError:
            return {}
        user_data_dict = self._get_user_by_pk(user_id)
        if not user_data_dict:
            return {}

        followers_output = {}  # Store PK: SimpleMockObject
        if user_data_dict["username"] == self.OWNER_USERNAME:
            alice_data_dict = self.simulated_users[ALICE_USERNAME]
            followers_output[alice_data_dict["pk"]] = self._create_mock_user_object(alice_data_dict)
        elif user_data_dict["username"] == self.BOT_USERNAME:
            bob_data_dict = self.simulated_users[BOB_USERNAME]
            followers_output[bob_data_dict["pk"]] = self._create_mock_user_object(bob_data_dict)

        return dict(list(followers_output.items())[:amount])

    def user_following(self, user_id_input, amount=10):
        try:
            user_id = int(str(user_id_input))
        except ValueError:
            return {}
        user_data_dict = self._get_user_by_pk(user_id)
        if not user_data_dict:
            return {}

        following_output = {}  # Store PK: SimpleMockObject
        if user_data_dict["username"] == self.OWNER_USERNAME:
            bob_data_dict = self.simulated_users[BOB_USERNAME]
            following_output[bob_data_dict["pk"]] = self._create_mock_user_object(bob_data_dict)
        elif user_data_dict["username"] == self.BOT_USERNAME:
            alice_data_dict = self.simulated_users[ALICE_USERNAME]
            following_output[alice_data_dict["pk"]] = self._create_mock_user_object(alice_data_dict)

        return dict(list(following_output.items())[:amount])

    def direct_threads(self, amount=10):
        if self.owner_id is None:
            print("[SIMULATOR] Error: Owner ID not set. Call login_by_sessionid first.")
            return []

        output_threads_list = []
        for thread_id, thread_data_dict in self.threads.items():  # thread_data_dict is the raw dict from self.threads
            # Convert user dicts stored in thread_data_dict['users'] to SimpleMockObjects for output
            users_obj_list = [self._create_mock_user_object(user_d) for user_d in thread_data_dict['users']]

            # Convert message dicts to SimpleMockObjects for output
            message_obj_list = [SimpleMockObject(**msg_d) for msg_d in thread_data_dict.get("messages", [])]

            inviter_user_data_dict = self._get_user_by_pk(self.owner_id)
            inviter_obj = self._create_mock_user_object(inviter_user_data_dict)

            # Data to construct the SimpleMockObject for the thread
            thread_constructor_data = {
                "id": thread_id,
                "users": users_obj_list,
                "last_activity_at": datetime.datetime.now(),
                "viewer_id": self.bot_id,
                "inviter": inviter_obj,
                "items": message_obj_list[-amount:]
            }
            output_threads_list.append(SimpleMockObject(**thread_constructor_data))
            if len(output_threads_list) >= amount:
                break
        return output_threads_list

    def direct_messages(self, thread_id, amount=20, cursor=None):
        print("\n--- New Message Simulation ---")
        if thread_id not in self.threads:
            print(f"[SIMULATOR] Error: Thread ID '{thread_id}' not found.")
            return []

        print(f"\n--- Existing messages for thread '{thread_id}' (last 5) ---")
        if self.threads[thread_id]["messages"]:
            for msg_dict in self.threads[thread_id]["messages"][-5:]:
                sender_username = "Unknown"
                sender_user_data = self._get_user_by_pk(msg_dict["user_id"])
                if sender_user_data:
                    sender_username = sender_user_data["username"]
                print(f"  {sender_username} ({msg_dict['timestamp']}): {msg_dict['text']}")
        else:
            print("  No messages yet.")
        print("--------------------------------------")

        sim_user_names_prompt = f"{self.OWNER_USERNAME}, {ALICE_USERNAME}, {BOB_USERNAME}, or '{self.BOT_USERNAME}' (for testing self-message)"
        sender_username_input = input(
            f"Enter sender username (e.g., {sim_user_names_prompt}, or 'quit'/'exit' to stop): ").strip()

        if sender_username_input.lower() in ['quit', 'exit']:
            print("[SIMULATOR] Exiting simulation as requested...")
            raise SystemExit("Simulation terminated by user.")

        sender_user_data_dict = self._get_user_by_username(sender_username_input)
        if not sender_user_data_dict:
            print(f"[SIMULATOR] Error: User '{sender_username_input}' not found. Try again.")
            return self.direct_messages(thread_id, amount, cursor)

        message_text = input(f"Enter message for thread '{thread_id}' (from {sender_username_input}): ").strip()
        if not message_text:
            print("[SIMULATOR] Message text cannot be empty. Assuming no new message.")
            return []

        new_message_id = self._get_next_message_id()
        sender_pk = sender_user_data_dict["pk"]

        new_message_data_dict = {  # This is a dict for internal storage
            "id": new_message_id,
            "user_id": sender_pk,
            "thread_id": thread_id,
            "text": message_text,
            "timestamp": datetime.datetime.now(),
            "item_type": "text",
        }

        self.threads[thread_id]["messages"].append(new_message_data_dict)
        print(f"[SIMULATOR] Message from {sender_username_input} added to thread '{thread_id}'.")

        # Return newly added message as a SimpleMockObject
        return [SimpleMockObject(**new_message_data_dict)]


if __name__ == '__main__':
    print("Starting Instagram Bot Simulation...")

    mock_client = MockInstagrapiClient(
        bot_username=SIMULATED_BOT_USERNAME,
        owner_username=SIMULATED_OWNER_USERNAME
    )

    Main.cl = mock_client
    print(f"Patched Main.cl with MockInstagrapiClient instance.")

    Main.OWNER_USERNAME = SIMULATED_OWNER_USERNAME
    config.OWNER_USERNAME = SIMULATED_OWNER_USERNAME  # Ensure config is also patched if Main imports from it directly
    print(f"Updated Main.OWNER_USERNAME and config.OWNER_USERNAME to '{SIMULATED_OWNER_USERNAME}'.")

    # Patch BOT_NAME if it's used by Main.py from config
    # Main.BOT_NAME = SIMULATED_BOT_USERNAME
    # config.BOT_NAME = SIMULATED_BOT_USERNAME
    # print(f"Updated Main.BOT_NAME and config.BOT_NAME to '{SIMULATED_BOT_USERNAME}'.")

    print("Calling Main.login()...")
    try:
        if Main.login():
            print("Main.login() successful (simulated).")
            print("Calling Main.print_user_info()...")
            Main.print_user_info()
            print("Calling Main.auto_respond()...")
            print("--- SIMULATION STARTED ---")
            print(f"Simulating messages. Enter 'quit' or 'exit' as sender username in the prompt below to stop.")
            Main.auto_respond()
        else:
            print("Main.login() failed (simulated). Exiting.")  # This should not happen with the fix
    except SystemExit as e:
        print(f"Simulation exited: {e}")
    except Exception as e:
        print(f"An error occurred during simulation: {e}")
        import traceback

        traceback.print_exc()

    print("--- SIMULATION ENDED ---")