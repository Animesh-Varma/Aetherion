# Project TODO List

## 🐞 Fixes
- [ ] Optimize response time
- [ ] Support back-to-back multiple function calls in a single response
- [ ] Reimplement functions from the Instagrapi implementation for UIAutomator2 implementation:
    - [ ] `list_threads`: List all open threads (only callable by owner)
    - [ ] `view_dms`: View DMs in a thread (only callable by owner)
    - [ ] `fetch_followers_followings`: Fetch followers and followings of any given account, if visible to the bot (currently a stub)
    - [x] `pause_response`: Owner/user-triggered pause, each with different lift rules (special instance for owner) (June 16, 2025)
    - [x] `resume_response`: Keyword-based resume function to minimize API usage (June 16, 2025)
- [x] Split long message responses (June 18, 2025)
- [x] Fix response order for multiple unread threads (June 5, 2025)
- [x] Messages sent via function calls were being counted as user-sent instead of bot-sent (June 5, 2025)
- [x] Large responses sent by the bot were incorrectly counted as user messages (June 5, 2025)
- [x] Ensure reliable API confirmation for multiple function calls (June 4, 2025)
- [x] Fix message history tracking and phrasing issues (June 4, 2025)
- [x] `notify_owner` function self-calling inconsistently without explicit prompt (June 4, 2025)

---

## 🔧 Improvements/Features
- [ ] Add multimodal capabilities
- [ ] Accept message requests
- [ ] Enable inter-thread communication and response tone memory
- [ ] Share all visible UI elements with the LLM upon error for better troubleshooting
- [ ] Optimize system prompts
- [ ] Upgrade from `google.generativeai` to `python-genai` **(Before August 31, 2025)**
- [ ] Enable bot to recognize updates made to itself
- [ ] Support runtime editing without stopping the bot
- [ ] Associate Instagram display names with usernames
- [ ] Enable natural typing input instead of pasting text
- [ ] Integrate with Ollama
- [ ] Follow/unfollow accounts
- [ ] Implement goal decomposition for complex tasks
- [ ] Add time-based auto triggers
- [ ] Cycle API keys to bypass quota limits
- [ ] Notify subscribed users on login/logout events
- [ ] Implement instance-level compartmentalization for users, owners, and function calls with privilege separation
- [x] Identify the DM sender while using the `send_message` function (June 5, 2025)
- [x] Owner messages should exclude the username and be rephrased by the bot (June 5, 2025)
- [x] Send a message before and after a function call (June 5, 2025)
- [x] Improve bot vs. user message distinction logic (June 5, 2025)
- [x] Check for new messages before sending a response via the API (June 4, 2025)

---

## 📚 Documentation
- [ ] Review `README.md`
- [x] Review `README.md` (June 4, 2025)

---

## 🧹 Chores
- [ ] Update `requirements.txt`
- [ ] Merge `uiautomator2_imp` branch with `master`
- [x] Update `TODO.md` with dates for completed tasks (June 18, 2025)

---

> TODO tracking started on May 31, 2025
