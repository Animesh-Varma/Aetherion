# Project TODO List

## Unimplemented Features & Enhancements

### Core Functionality
*   **`fetch_followers_followings_func`**: The UI automation logic in `uiautomator2_utils.py` for `fetch_followers_followings` is currently a stub. Implement the necessary UI interactions to reliably fetch follower and following lists for a target user.
*   **LLM Function Integration**: Several functions declared for Gemini in `Main.py` lack corresponding UI automation hooks or are not actively used:
    *   `pause_response_func`: While keyword-based pause/resume exists, the LLM-triggered `pause_response_func` is not implemented via UI actions.
    *   `resume_response_func`: Similar to pausing, the LLM-triggered `resume_response_func` is not implemented via UI actions.
    *   `target_thread_func`: UI automation to switch focus to a specific thread based on an LLM command needs to be implemented.
    *   `list_threads_func`: UI automation to list active threads based on an LLM command needs to be implemented.
    *   `view_dms_func`: UI automation to view DMs in a thread based on an LLM command needs to be implemented.

### UI Automation Robustness (from `uiautomator2_utils.py` inline TODOs)
*   **Selector Verification**:
    *   `DM_LIST_SEARCH_INPUT_FIELD_RESID`: Verify and potentially improve the selector for the DM list search input field.
    *   `NEW_CHAT_USER_RESULT_SELECT_ELEMENT_RESID`: The selector for user results in a new chat (`android.widget.FrameLayout`) is very generic. Investigate for a more specific and reliable selector.
    *   `GENERAL_SEARCH_RESULT_ITEM_CONTAINER_CLASS`: The selector for user items in general search results (`android.widget.LinearLayout`) is generic. Investigate for a more specific and reliable selector.
*   **User Profile Navigation**:
    *   `go_to_user_profile`: Enhance the robustness of finding users in general search results. Consider handling cases where the exact username match isn't immediately visible or if multiple results appear.
*   **DM Initiation**:
    *   `send_dm_from_profile`: Review the necessity of this function. If kept, fix the control flow issue (potential unreachable code) and ensure its robustness. Consider if `search_and_open_dm_with_user` is sufficient.
*   **Error Recovery**:
    *   `search_and_open_dm_with_user`: Improve error recovery, especially if intermediate steps in finding or creating a new chat fail.
*   **Profile Info Scraping**:
    *   `get_bot_profile_info`: Verify the selectors for follower (`PROFILE_FOLLOWER_COUNT_TEXT_RESID`) and following (`PROFILE_FOLLOWING_COUNT_TEXT_RESID`) counts, as these can change with UI updates.
*   **Fix msg retrieval errors/repetition**

## Code Quality & Maintenance
*   Review and address any `FIXME` comments in the codebase.
*   Periodically review UI selectors in `uiautomator2_utils.py` as Instagram updates can break them.
