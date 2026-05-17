<div align="center">

# FreelanceGuard

### AI-Powered Freelance Dispute Resolution on GenLayer

**An Intelligent Contract that fetches live work submissions, evaluates them with AI validators, and releases funds automatically — no moderator, no oracle, no trust required.**

[![Visit Site](https://img.shields.io/badge/Visit%20Site-gen--layerfreelanceguard.vercel.app-ff6b35?style=for-the-badge)](https://gen-layerfreelanceguard.vercel.app)
[![GenLayer](https://img.shields.io/badge/Built%20on-GenLayer-7c3aed?style=for-the-badge)](https://genlayer.com)
[![Python](https://img.shields.io/badge/Language-Python-3b82f6?style=for-the-badge)](https://docs.genlayer.com)

</div>

---

## What's inside the site

| Section | What you'll learn |
|---|---|
| 🧠 **What is GenLayer** | AI-native blockchain — how it compares to Ethereum |
| ⚙️ **How it works** | 5-step flow from job post to automatic fund release |
| 🏗️ **Architecture** | Layer-by-layer diagram — validators, consensus, web fetch |
| 💻 **Annotated code** | Full contract broken into tabs with line-by-line explanation |
| 🚀 **Deploy guide** | Step-by-step using GenLayer Studio — browser only, no install |
| 📖 **Concepts glossary** | Every GenLayer primitive explained simply |
| 🧪 **20-question quiz** | Test your understanding with instant feedback |

---

## The contract — 3 GenLayer features in one

```python
# 1. Fetch live web data — no oracle
content = gl.nondet.web.render(submission_url, mode="text")

# 2. Evaluate with AI inside consensus
result = gl.nondet.exec_prompt(prompt, response_format="json")

# 3. Release funds automatically
emit_transfer(freelancer, budget)   # or refund client
```

---

## Try it yourself

1. Open **[studio.genlayer.com](https://studio.genlayer.com)** — no install needed
2. Paste `freelance_guard.py` → Deploy
3. Call `post_job()` → `submit_work()` → `evaluate_submission()`
4. Watch AI validators reach consensus and release funds

---

## Files

| File | Description |
|---|---|
| `freelance_guard.py` | The Intelligent Contract — deploy this in GenLayer Studio |
| `index.html` | Full educational site |
| `TUTORIAL.md` | Complete written tutorial |
| `Architecture.svg` | System architecture diagram |

---

<div align="center">

*Submitted for the GenLayer Educational Content Mission*  
*[docs.genlayer.com](https://docs.genlayer.com) · [studio.genlayer.com](https://studio.genlayer.com)*

</div>
