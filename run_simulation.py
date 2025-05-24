import datetime
import Main
import config # To potentially modify config values if Main.py uses them directly
from unittest.mock import patch

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
            "full_name": "Alice Wonderland", "follower_count": 200, "is_private": False, "is_verified": False
        },
        BOB_USERNAME: {
            "full_name": "Bob The Builder", "follower_count": 300, "is_private": True, "is_verified": False
        }
    }


    def __init__(self, bot_username=SIMULATED_BOT_USERNAME, owner_username=SIMULATED_OWNER_USERNAME):
        self.OWNER_USERNAME = owner_username
        self.BOT_USERNAME = bot_username
        
        # Dynamically create simulated_users for this instance
        self.simulated_users = {
            self.OWNER_USERNAME: {
                "pk": self.USER_PK_MAP.get(self.OWNER_USERNAME, 1001), # Fallback PK if not in map
                "username": self.OWNER_USERNAME,
                "full_name": "Simulated Owner",
                "follower_count": 100,
                "is_private": False,
                "is_verified": False,
            },
            self.BOT_USERNAME: {
                "pk": self.USER_PK_MAP.get(self.BOT_USERNAME, 1002), # Fallback PK
                "username": self.BOT_USERNAME,
                "full_name": "Simulated Bot",
                "follower_count": 50,
                "is_private": False,
                "is_verified": False,
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
        
        self.bot_id = None # Set in login_by_sessionid
        self.owner_id = None # Set in login_by_sessionid
        self.username = None # Bot's username, set in login_by_sessionid
        self.message_id_counter = 0
        self.threads = {}
        # Note: Thread pre-population moved to login_by_sessionid to ensure IDs are set

    def _get_user_by_pk(self, pk):
        pk = int(pk) 
        for user_data in self.simulated_users.values():
            if user_data["pk"] == pk:
                return user_data
        return None

    def _get_user_by_username(self, username):
        return self.simulated_users.get(username)


    def _create_mock_user_object(self, user_data):
        if not user_data:
            return None
        # Using a simple dictionary to represent the UserShort/User object
        # In a real scenario, this would be an instance of a class
        return {
            "pk": user_data["pk"],
            "username": user_data["username"],
            "full_name": user_data["full_name"],
            "follower_count": user_data["follower_count"],
            "is_private": user_data["is_private"],
            "is_verified": user_data["is_verified"],
        }

    def login_by_sessionid(self, session_id):
        # Uses instance specific BOT_USERNAME and OWNER_USERNAME
        self.bot_id = self.simulated_users[self.BOT_USERNAME]["pk"]
        self.owner_id = self.simulated_users[self.OWNER_USERNAME]["pk"]
        self.username = self.BOT_USERNAME # The client logs in as the bot
        print(f"Mock login successful as {self.username} (ID: {self.bot_id})")

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
                        {
                            "id": self._get_next_message_id(),
                            "user_id": owner_user_obj["pk"], # Owner sends the first message
                            "thread_id": mock_thread_1_id,
                            "text": "Welcome to the simulated chat!",
                            "timestamp": datetime.datetime.now() - datetime.timedelta(minutes=5),
                            "item_type": "text",
                        }
                    ],
                }
                mock_thread_2_id = "mock_thread_2" # For owner and Bob
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

    def user_info_v1(self, user_id_str): # user_id_str is actually user_id (pk)
        try:
            user_id = int(user_id_str) # user_id_str is pk
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
        print(f"[SIMULATOR] Direct send called. Text: '{text}', User IDs: {user_ids}, Thread IDs: {thread_ids}")
        if thread_ids and isinstance(thread_ids, list):
            for thread_id in thread_ids:
                if thread_id in self.threads:
                    new_msg = {
                        "id": self._get_next_message_id(),
                        "user_id": self.bot_id, 
                        "thread_id": thread_id,
                        "text": text,
                        "timestamp": datetime.datetime.now(),
                        "item_type": "text",
                    }
                    self.threads[thread_id]["messages"].append(new_msg)
                    print(f"[SIMULATOR] Message added to thread {thread_id}")
                else:
                    print(f"[SIMULATOR] Thread ID {thread_id} not found for direct_send.")
        elif user_ids: 
            print(f"[SIMULATOR] direct_send to user_ids {user_ids} - thread finding/creation not fully implemented here.")

    def user_followers(self, user_id_str, amount=10): # user_id_str is pk
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

    def user_following(self, user_id_str, amount=10): # user_id_str is pk
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
            users_list = [self._create_mock_user_object(self._get_user_by_pk(u['pk'])) if isinstance(u, dict) and 'pk' in u else u for u in thread_data['users']]
            
            mock_thread_obj = {
                "id": thread_id,
                "users": users_list, 
                "last_activity_at": datetime.datetime.now(), 
                "viewer_id": self.bot_id,
                "inviter": inviter_obj, 
                "items": thread_data.get("messages", [])[-amount:] 
            }
            mock_threads_list.append(mock_thread_obj)
            if len(mock_threads_list) >= amount:
                break
        return mock_threads_list

    def direct_messages(self, thread_id, amount=20, cursor=None):
        print("\n--- New Message Simulation ---")
        
        if thread_id not in self.threads:
            print(f"[SIMULATOR] Error: Thread ID '{thread_id}' not found.")
            return []

        print(f"\n--- Existing messages for thread '{thread_id}' ---")
        if self.threads[thread_id]["messages"]:
            for msg in self.threads[thread_id]["messages"][-5:]: 
                sender_username = "Unknown"
                sender_user_data = self._get_user_by_pk(msg["user_id"])
                if sender_user_data:
                    sender_username = sender_user_data["username"]
                print(f"  {sender_username} ({msg['timestamp']}): {msg['text']}")
        else:
            print("  No messages yet.")
        print("--------------------------------------")

        # Prepare list of simulated users for the prompt
        sim_user_names_prompt = f"{self.OWNER_USERNAME}, {ALICE_USERNAME}, {BOB_USERNAME}, or '{self.BOT_USERNAME}'"
        sender_username_input = input(f"Enter sender username (e.g., {sim_user_names_prompt}, or 'quit'/'exit' to stop): ").strip()
        
        if sender_username_input.lower() in ['quit', 'exit']:
            print("[SIMULATOR] Exiting simulation as requested...")
            raise SystemExit("Simulation terminated by user.")

        sender_user_data = self._get_user_by_username(sender_username_input)
        if not sender_user_data:
            print(f"[SIMULATOR] Error: User '{sender_username_input}' not found in simulated users.")
            return [] 

        message_text = input(f"Enter message for thread '{thread_id}' (from {sender_username_input}): ").strip()

        if not message_text:
            print("[SIMULATOR] Message text cannot be empty.")
            return []

        new_message_id = self._get_next_message_id()
        sender_pk = sender_user_data["pk"]

        new_message_obj = {
            "id": new_message_id,
            "user_id": sender_pk,
            "thread_id": thread_id,
            "text": message_text,
            "timestamp": datetime.datetime.now(),
            "item_type": "text", 
        }

        if thread_id in self.threads:
            self.threads[thread_id]["messages"].append(new_message_obj)
            print(f"[SIMULATOR] Message from {sender_username_input} added to thread '{thread_id}'.")
        else:
            print(f"[SIMULATOR] Error: Thread ID '{thread_id}' disappeared unexpectedly.")
            return []

        return [new_message_obj]


if __name__ == '__main__':
    print("Starting Instagram Bot Simulation...")

    # 1. Instantiate the Mock Client
    mock_client = MockInstagrapiClient(
        bot_username=SIMULATED_BOT_USERNAME,
        owner_username=SIMULATED_OWNER_USERNAME
    )

    # 2. Patch Main.cl 
    Main.cl = mock_client
    print(f"Patched Main.cl with MockInstagrapiClient instance.")

    # 3. Patch config variables
    Main.OWNER_USERNAME = SIMULATED_OWNER_USERNAME
    print(f"Updated Main.OWNER_USERNAME to '{SIMULATED_OWNER_USERNAME}'.")
    
    config.OWNER_USERNAME = SIMULATED_OWNER_USERNAME
    # config.BOT_NAME = SIMULATED_BOT_USERNAME # If Main.py uses config.BOT_NAME
    print(f"Updated config.OWNER_USERNAME to '{SIMULATED_OWNER_USERNAME}'.")
    # API_KEY for Gemini is not touched to allow live calls if needed.

    # 4. Run the bot's login function
    print("Calling Main.login()...")
    try:
        if Main.login(): 
            print("Main.login() successful (simulated).")

            # 5. Print user info
            print("Calling Main.print_user_info()...")
            Main.print_user_info()

            # 6. Start the auto-responder
            print("Calling Main.auto_respond()...")
            print("--- SIMULATION STARTED ---")
            print(f"Simulating messages. Enter 'quit' or 'exit' as sender username in the prompt below to stop.")
            Main.auto_respond() # This will now loop using mock_client.direct_messages

        else:
            print("Main.login() failed (simulated). Exiting.")
    except SystemExit as e:
        print(f"Simulation exited: {e}")
    except Exception as e:
        print(f"An error occurred during simulation: {e}")
        import traceback
        traceback.print_exc()

    print("--- SIMULATION ENDED ---")
