# Project TODO List

## 🐞 Fixes
- [ ] Optimize response time
- [ ] Reimplement functions available for Instagrapi implementation for UIAutomator2 implementation
    - [ ] pause_response: LLM/user/owner-triggered pause_response, each with different lift rules (special instance for owner)
    - [ ] resume_response: keyword-based resume_response function to resume auto response without wasting API usage 
    - [ ] target_thread: Select thread for manual function calls (Only callable by owner)
    - [ ] list_threads: list all open threads (Only callable by owner)
    - [ ] view_dms: view DMs in a thread (Only callable by owner)
    - [ ] fetch_followers_followings: fetch followers and followings of any given account if visible to bot (currently a stub)
- [x] For messages sent through function call, it counts them as being sent by the user though they are sent by the bot.
- [x] For larger responses sent by the bot it counts them as being sent by the user
- [x] Self-calling of notify_owner function by LLM without explicit mention working inconsistency
- [x] Fix the response order of multiple unread threads
- [x] Reliable multiple API calls for function call confirmation
- [x] Fix message history and phrasing issues

---

## 🔧 Improvements/Features
- [ ] Split long message responses
- [ ] Accept message requests
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
- [x] Improve bot and user msg distinction logic 
- [x] Message before function call
- [x] Check for new messages before sending a response from the API
- [x] Messages from the owner shouldn't include the owner's username and should be rephrased when sent by the bot
- [x] Identification of the sender of a DM using the send_message function 

---

## 📚 Documentation
- [ ] Review README.md 
- [x] Review README.md (June 4, 2025)

---

## 🧹 Chores
- [ ] Update requirements.txt

---

> TODO tracking started on May 31, 2025
