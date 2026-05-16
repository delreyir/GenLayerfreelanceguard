# FreelanceGuard — AI-Powered Freelance Dispute Resolution on GenLayer

> **Educational submission for:** From Zero to GenLayer — Introductory Tutorial Mission  
> **Difficulty:** Beginner → Intermediate · **Time:** ~30 min · **Platform:** GenLayer Studio (browser, no install)

---

## What is this?

**FreelanceGuard** is a complete **Intelligent Contract** built on [GenLayer](https://genlayer.com) that replaces the human moderator in freelance disputes with AI validators.

When a freelancer submits work, the contract:
1. **Fetches the submitted URL live** — no oracle required (`gl.nondet.web.render`)
2. **Evaluates the content with an LLM** against plain-English criteria (`gl.nondet.exec_prompt`)
3. **Reaches consensus** across multiple validator nodes — each using a different AI model
4. **Releases funds automatically** — to the freelancer if accepted, refunded to client if rejected

No human moderator. No platform fee. No trusted intermediary.

---

## Repository structure

```
freelanceguard/
├── contracts/
│   └── freelance_guard.py   ← The Intelligent Contract (deploy this)
├── assets/
│   └── architecture.svg     ← System architecture diagram
├── docs/
│   └── TUTORIAL.md          ← Full step-by-step tutorial
└── README.md
```

---

## Architecture

![FreelanceGuard Architecture](assets/architecture.svg)

| Layer | Component | GenLayer API |
|---|---|---|
| 0 | Client / Freelancer wallets | `gl.message.sender_account`, `gl.message.value` |
| 1 | FreelanceGuard.py (Intelligent Contract) | `gl.Contract`, `TreeMap`, `DynArray` |
| 2 | Live web fetch | `gl.nondet.web.render(url, mode="text")` |
| 2 | LLM evaluation | `gl.nondet.exec_prompt(prompt, response_format="json")` |
| 3 | Validator nodes (GPT-4, Claude, LLaMA…) | `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)` |
| 4 | Optimistic Democracy consensus | Supermajority vote on equivalence |
| 5 | Automatic fund release | `emit_transfer(address, amount)` |

---

## Quick start (GenLayer Studio)

1. Go to **[studio.genlayer.com](https://studio.genlayer.com)** — no install needed
2. Create a new file: `freelance_guard.py`
3. Paste the contract from `contracts/freelance_guard.py`
4. Click **Deploy** — no constructor args
5. Call `post_job()` and send GEN to create a job
6. Call `submit_work()` with a public URL
7. Call `evaluate_submission()` and watch Optimistic Democracy run
8. Call `get_job()` to read the AI verdict and check fund release

See `docs/TUTORIAL.md` for the full annotated walkthrough.

---

## Key GenLayer concepts demonstrated

| Concept | What it does | Used in |
|---|---|---|
| `@gl.public.write.payable` | Method can receive GEN tokens | `post_job()` |
| `gl.message.value` | Amount of GEN sent with transaction | `post_job()` |
| `gl.message.sender_account` | Verified caller wallet address | `submit_work()` |
| `gl.nondet.web.render()` | Fetch live URL — no oracle | `evaluate_submission()` |
| `gl.nondet.exec_prompt()` | Call LLM inside consensus | `evaluate_submission()` |
| `gl.vm.run_nondet_unsafe()` | Custom Optimistic Democracy logic | `evaluate_submission()` |
| `emit_transfer()` | Send GEN to any address | `evaluate_submission()` |
| `TreeMap[K,V]` | Persistent on-chain mapping | Contract state |
| `DynArray[T]` | Persistent on-chain array | Contract state |

---

## Critical rules (avoid common mistakes)

```python
# ❌ WRONG — LLM/web call directly in method body
@gl.public.write
def evaluate(self, job_id: int) -> None:
    result = gl.nondet.exec_prompt("...")   # ERROR

# ✅ CORRECT — inside an inner function
@gl.public.write
def evaluate(self, job_id: int) -> None:
    def leader_fn():
        return gl.nondet.exec_prompt("...")
    result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
```

```python
# ❌ WRONG — accessing self inside nondet block
def leader_fn():
    content = gl.nondet.web.render(self.url)   # ERROR — self not available

# ✅ CORRECT — capture locals before the block
url = job.submission_url   # capture before
def leader_fn():
    content = gl.nondet.web.render(url)        # use local
```

```python
# ❌ WRONG — mutating TreeMap entry in place
job = self.jobs[job_id]
job.verdict = "accepted"   # NOT persisted

# ✅ CORRECT — reassign back to TreeMap
job = self.jobs[job_id]
job.verdict = "accepted"
self.jobs[job_id] = job   # ← required
```

---

## Resources

- [GenLayer Docs](https://docs.genlayer.com)
- [GenLayer Studio](https://studio.genlayer.com)
- [Discord](https://discord.gg/8Jm4v89VAu)
- [GitHub (GenLayer Labs)](https://github.com/genlayerlabs)

---

*Built for the GenLayer Educational Content mission.*
