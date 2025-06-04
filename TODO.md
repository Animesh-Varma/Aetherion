# Project TODO List

## 🐞 Fixes
- [ ] fetch_followers_followings is currently a stub and requires implementation.
- [ ] Optimize response time
- [ ] For larger responses sent by the bot it counts them as being sent by the user
- [ ] Reimplement functions available for Instagrapi implementation for UIAutomator2 implementation
    - [ ] pause_response: LLM/user/owner-triggered pause_response, each with different lift rules (special instance for owner)
    - [ ] resume_response: keyword-based resume_response function to resume auto response without wasting API usage 
    - [ ] target_thread: Select thread for manual function calls (Only callable by owner)
    - [ ] list_threads: list all open threads (Only callable by owner)
    - [ ] view_dms: view DMs in a thread (Only callable by owner)
- [x] Self-calling of notify_owner function by LLM without explicit mention working inconsistency
- [x] Fix the response order of multiple unread threads
- [x] Reliable multiple API calls for function call confirmation
- [x] Fix message history and phrasing issues

---

## 🔧 Improvements/Features
- [ ] Split long message responses
- [ ] Optimize system prompts
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
- [x] Check for new messages before sending a response from the API

---

## 📚 Documentation
- [ ] Review README.md 
- [x] Review README.md (June 4, 2025)

---

## 🧹 Chores
- [ ] Update requirements.txt

---

> TODO tracking started on May 31, 2025
