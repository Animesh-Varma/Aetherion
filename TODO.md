# Project TODO List

## Unimplemented Features & Enhancements

### Core Functionality
*   **`fetch_followers_followings_func`**: The UI automation logic in `uiautomator2_utils.py` for `fetch_followers_followings` is currently a stub. Implement the necessary UI interactions to reliably fetch follower and following lists for a target user.
*   **LLM Function Integration**: Several functions declared for Gemini in `Main.py` lack corresponding UI automation hooks or are not actively used in the new uiautomator2 implementation:
    *   `pause_response_func`: While keyword-based pause/resume exists, the LLM-triggered `pause_response_func` is not implemented via UI actions.
    *   `resume_response_func`: Similar to pausing, the LLM-triggered `resume_response_func` is not implemented via UI actions.
    *   `target_thread_func`: UI automation to switch focus to a specific thread based on an LLM command needs to be implemented.
    *   `list_threads_func`: UI automation to list active threads based on an LLM command needs to be implemented.
    *   `view_dms_func`: UI automation to view DMs in a thread based on an LLM command needs to be implemented.
*   **Reliable multiple API calls for function call confirmation**: The second API call doesn't consistently reply with the status of the function call.
*   **Reliable way to relay messages(DM's)**: Find a more robust way to send messages(DM) to a specific user with accuracy.
*   **Split long message responses**: Since Instagram has a limit on message length, split long responses into multiple parts.

#### Update README.md
