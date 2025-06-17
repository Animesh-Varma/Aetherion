# Project TODO List

## 🐞 Fixes
- [ ] Optimize response time
- [ ] Back-to-back multiple function calls in a single response
- [ ] Reimplement functions available for Instagrapi implementation for UIAutomator2 implementation
    - [ ] list_threads: list all open threads (Only callable by owner)
    - [ ] view_dms: view DMs in a thread (Only callable by owner)
    - [ ] fetch_followers_followings: fetch followers and followings of any given account if visible to bot (currently a stub)
    - [x] pause_response: User/owner-triggered pause_response, each with different lift rules (special instance for owner) (dd/06/25)
    - [x] resume_response: keyword-based resume_response function to resume auto response without wasting API usage (dd/06/25)
- [x] For messages sent through function call, it counts them as being sent by the user though they are sent by the bot. (dd/mm/25)
- [x] Self-calling of notify_owner function by LLM without explicit mention working inconsistency (dd/mm/25)
- [x] Fix the response order of multiple unread threads (dd/mm/25)
- [x] Reliable multiple API calls for function call confirmation (dd/mm/25)
- [x] Fix message history and phrasing issues (dd/mm/25)
- [x] Split long message responses (18/06/25)

---

## 🔧 Improvements/Features
- [ ] Add multi-modal capabilities
- [ ] Accept message requests
- [ ] Inter-thread communication and response tone memory 
- [ ] If an error is encountered, share all visible elements with LLM for possible troubleshooting and situational awareness 
- [ ] Optimize system prompts
- [ ] Upgrade from Google.generativeai to python-genai (Before August 31st, 2025) 
- [ ] Allow bot to know updates made to it
- [ ] Change bots source code without actually stopping it (Runtime edit)
- [ ] Create an association between the name and the username of Instagram accounts 
- [ ] Natural typing input for Instagram instead of pasting text 
- [ ] Ollama integration
- [ ] Follow/unfollow accounts
- [ ] Implement goal decomposition for complex tasks
- [ ] Times-based auto trigger
- [ ] Implement API key cycling to bypass quota limits
- [ ] Login and Logoff notification for subscribed users
- [ ] compartmentalized with different instances for each user, owner, and function calling each with different privileges
- [x] Improve bot and user msg distinction logic (dd/mm/25)
- [x] Message before function call (dd/mm/25)
- [x] Check for new messages before sending a response from the API (dd/mm/25)
- [x] Messages from the owner shouldn't include the owner's username and should be rephrased when sent by the bot (dd/mm/25)
- [x] Identification of the sender of a DM using the send_message function (dd/mm/25)

---

## 📚 Documentation
- [ ] Review README.md 
- [x] Review README.md (04/06/25)

---

## 🧹 Chores
- [ ] Update requirements.txt
- [ ] Update TODO.md with dates for completed tasks 

---

> TODO tracking started on May 31, 2025
