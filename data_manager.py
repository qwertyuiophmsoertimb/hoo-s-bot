import json
import os
from config import INITIAL_PLAYER_PROFILE

# Global dictionary to hold all user data in memory
user_data = {}

def load_user_data():
    """Loads user data from 'userdata.json' into memory."""
    global user_data
    try:
        if os.path.exists("userdata.json"):
            with open("userdata.json", "r") as f:
                user_data = json.load(f)
            print(f"DEBUG: Loaded {len(user_data)} user profiles from userdata.json.")
        else:
            print("DEBUG: userdata.json not found. Starting with empty user_data.")
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode userdata.json: {e}. Starting with empty user_data.")
        user_data = {} # Reset to empty to prevent corrupted data issues
    except Exception as e:
        print(f"ERROR: An unexpected error occurred loading userdata.json: {e}. Starting with empty user_data.")
        user_data = {} # Reset to empty

def save_user_data():
    """Saves the current in-memory user data to 'userdata.json'."""
    try:
        with open("userdata.json", "w") as user_data_file:
            json.dump(user_data, user_data_file, indent=4)
        print(f"DEBUG: Successfully saved userdata.json. {len(user_data)} users data written.")
    except IOError as e:
        print(f"ERROR: Failed to write userdata.json: {e}")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during userdata.json save: {e}")

def get_user_data(user_id: int) -> dict:
    """
    Retrieves a user's persistent data, initializing it with a default profile if not found.
    Ensures the returned dictionary is a deep copy to prevent accidental modification of the global
    user_data dict without explicit update calls.
    """
    user_id_str = str(user_id)
    if user_id_str not in user_data:
        # Create a deep copy of the initial profile to ensure independence
        new_profile = json.loads(json.dumps(INITIAL_PLAYER_PROFILE))
        user_data[user_id_str] = new_profile
        print(f"DEBUG: Initialized new profile for user {user_id_str}. Saving to file.")
        save_user_data() # Save when new user data is initialized
    return user_data[user_id_str]

def update_user_data(user_id: int, user_data_obj: dict):
    """
    Updates a user's persistent data in memory.
    This function should be called after modifying a user's data obtained via get_user_data.
    """
    user_id_str = str(user_id)
    user_data[user_id_str] = user_data_obj
    save_user_data() # Save immediately after any update

# Load data when the module is imported
load_user_data()
