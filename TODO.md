# Project TODO List

## 🐞 Fixes
- [ ] fetch_followers_followings is currently a stub and requires implementation.
- [ ] Fix the response order of multiple unread responses
- [ ] Reimplement functions available for Instagrapi implementation for UIAutomator2 implementation
    - [ ] pause_response: LLM/user/owner-triggered pause_response, each with different lift rules (special instance for owner)
    - [ ] resume_response: keyword-based resume_response function to resume auto response without wasting API usage 
    - [ ] target_thread: Select thread for manual function calls (Only callable by owner)
    - [ ] list_threads: list all open threads (Only callable by owner)
    - [ ] view_dms: view DMs in a thread (Only callable by owner)
- [x] Reliable multiple API calls for function call confirmation

---

## 🔧 Improvements/Features
- [ ] Split long message responses
- [ ] Check for new messages before sending a response from the API
- [ ] Create an association between the name and the username of Instagram accounts 
- [ ] natural typing output
- [ ] Ollama integration

---

## 📚 Documentation
- [ ] Review README.md 
- [x] Review README.md (June 4, 2025)

---

## 🧹 Chores
- [ ] Update requirements.txt

---

> TODO tracking started on May 31, 2025
