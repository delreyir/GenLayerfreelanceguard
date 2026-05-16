# FreelanceGuard — Full Step-by-Step Tutorial

> **Platform:** GenLayer Studio (browser) · **Time:** ~30 minutes · **No install required**

---

## Table of Contents

1. [What is GenLayer?](#1-what-is-genlayer)
2. [The Problem We're Solving](#2-the-problem-were-solving)
3. [How FreelanceGuard Works](#3-how-freelanceguard-works)
4. [Open GenLayer Studio](#4-open-genlayer-studio)
5. [The Contract Code — Annotated](#5-the-contract-code--annotated)
6. [Deploy to Testnet](#6-deploy-to-testnet)
7. [Interact Step by Step](#7-interact-step-by-step)
8. [Read the Verdict On-Chain](#8-read-the-verdict-on-chain)
9. [Concepts Reference](#9-concepts-reference)
10. [Common Mistakes to Avoid](#10-common-mistakes-to-avoid)

---

## 1. What is GenLayer?

GenLayer is a blockchain where validator nodes — each powered by a different AI model — reach consensus on decisions that require reasoning, not just arithmetic.

**Traditional smart contracts** can only execute deterministic logic: `if balance > 100 { transfer() }`. They are blind to the outside world without an oracle.

**GenLayer Intelligent Contracts** can:
- Fetch any live public URL (`gl.nondet.web.render`)
- Call a language model with a prompt (`gl.nondet.exec_prompt`)
- Evaluate unstructured, natural-language criteria
- Reach consensus across multiple validators using the **Equivalence Principle**

| | Traditional Smart Contract | GenLayer Intelligent Contract |
|---|---|---|
| Live web access | ❌ Requires oracle | ✅ `gl.nondet.web.render()` |
| LLM calls | ❌ Not possible | ✅ `gl.nondet.exec_prompt()` |
| Natural language logic | ❌ Structured only | ✅ Plain-English criteria |
| Consensus mechanism | Deterministic | Optimistic Democracy |
| Language | Solidity / Rust | **Python** |

---

## 2. The Problem We're Solving

Every freelance platform has the same problem: **disputes**.

- A client says the work wasn't delivered as agreed
- The freelancer disagrees
- A human moderator reviews the case — slow (3–10 days), expensive (20% fee), opaque (no audit trail)

**FreelanceGuard eliminates the moderator.** The contract fetches the delivered work, evaluates it against the agreed criteria using AI validators, and releases funds automatically. The entire process is on-chain, auditable, and irreversible.

---

## 3. How FreelanceGuard Works

```
CLIENT                    CONTRACT                  FREELANCER
  │                          │                          │
  │──── post_job(value) ────>│                          │
  │     (GEN locked)         │                          │
  │                          │<──── submit_work(url) ───│
  │                          │                          │
  │              evaluate_submission() ──────────────>  │
  │                          │                          │
  │              gl.nondet.web.render(url)               │
  │              [each validator fetches independently]  │
  │                          │                          │
  │              gl.nondet.exec_prompt(criteria+content) │
  │              [each validator calls their own LLM]    │
  │                          │                          │
  │              Optimistic Democracy                    │
  │              [supermajority consensus on verdict]    │
  │                          │                          │
  │<─── if rejected ─────────│                          │
  │     emit_transfer(client)│                          │
  │                          │──── if accepted ─────────│
  │                          │     emit_transfer(freelancer)
```

---

## 4. Open GenLayer Studio

1. Go to **[https://studio.genlayer.com](https://studio.genlayer.com)**
2. The Studio opens with:
   - A test wallet pre-loaded with testnet GEN (no faucet needed)
   - A file explorer (left panel)
   - A code editor (center)
   - A transaction/deploy panel (right)
3. No MetaMask, no CLI, no local setup required.

---

## 5. The Contract Code — Annotated

### 5.1 The required header

```python
# { "Depends": "py-genlayer:test" }
```

Every Intelligent Contract must start with this line. It declares the GenVM SDK version. Without it, the contract will not deploy correctly.

### 5.2 Imports

```python
from genlayer import *
from dataclasses import dataclass
import json
```

`from genlayer import *` imports the entire GenLayer SDK: `gl`, `TreeMap`, `DynArray`, `u256`, `emit_transfer`, and everything else you need.

### 5.3 The data structure

```python
@dataclass
class Job:
    job_id:         int
    client:         str    # wallet address
    freelancer:     str    # wallet address
    title:          str
    criteria:       str    # plain English — read directly by LLM
    budget:         u256   # GEN tokens in escrow
    submission_url: str    # fetched live at evaluation
    verdict:        str    # "pending" | "accepted" | "rejected"
    reason:         str    # LLM explanation
    is_submitted:   bool
```

The `criteria` field is **plain English text** — no encoding. The LLM reads it directly and evaluates the submission against it.

### 5.4 Contract state

```python
class FreelanceGuard(gl.Contract):
    jobs:            TreeMap[int, Job]
    next_id:         int
    client_jobs:     TreeMap[str, DynArray[int]]
    freelancer_jobs: TreeMap[str, DynArray[int]]
```

> ⚠️ **Critical:** Use `TreeMap[K, V]` instead of Python `dict` and `DynArray[T]` instead of Python `list`. Regular Python dicts and lists are not persisted between transactions. This is the #1 beginner mistake.

### 5.5 post_job() — payable escrow

```python
@gl.public.write.payable
def post_job(self, freelancer_address: str, title: str, criteria: str) -> int:
    assert gl.message.value > 0, "Must send GEN to fund the escrow"
    # ...
    job = Job(
        client = gl.message.sender_account,  # verified caller
        budget = gl.message.value,           # GEN locked in escrow
        # ...
    )
    self.jobs[job_id] = job
    return job_id
```

- `@gl.public.write.payable` — allows receiving GEN tokens
- `gl.message.value` — amount sent with the transaction
- `gl.message.sender_account` — verified wallet address of caller

### 5.6 submit_work() — access control

```python
@gl.public.write
def submit_work(self, job_id: int, submission_url: str) -> None:
    job = self.jobs[job_id]
    assert gl.message.sender_account == job.freelancer, "Only the freelancer can submit"
    job.submission_url = submission_url
    job.is_submitted   = True
    self.jobs[job_id]  = job   # ← must reassign — mutation alone doesn't persist
```

> ⚠️ After modifying a `Job` from a `TreeMap`, you must reassign it back. Mutating the local copy in-place does not update on-chain storage.

### 5.7 evaluate_submission() — the core GenLayer feature

This is where everything comes together.

**Step 1 — Capture locals before entering nondet block:**
```python
# ⚠️ You cannot access `self` inside inner functions — capture first
title      = job.title
criteria   = job.criteria
submit_url = job.submission_url
```

**Step 2 — Define the leader function (web fetch + LLM):**
```python
# ⚠️ Web and LLM calls MUST be inside an inner function
def leader_fn() -> str:
    content = gl.nondet.web.render(submit_url, mode="text")  # live fetch, no oracle
    prompt  = f"""...(criteria)...(content)..."""
    result  = gl.nondet.exec_prompt(prompt, response_format="json")
    return json.dumps({"verdict": result["verdict"]}, sort_keys=True)
```

**Step 3 — Define the validator function (equivalence check):**
```python
def validator_fn(leaders_result) -> bool:
    if not isinstance(leaders_result, gl.vm.Return):
        return False
    my_raw   = leader_fn()                     # validator runs own LLM
    leader_d = json.loads(leaders_result.calldata)
    mine_d   = json.loads(my_raw)
    return leader_d["verdict"] == mine_d["verdict"]  # compare decision, not wording
```

**Step 4 — Run Optimistic Democracy:**
```python
raw    = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
parsed = json.loads(raw)
```

**Step 5 — Release funds:**
```python
if parsed["verdict"] == "accepted":
    emit_transfer(freelancer, budget)   # pay the freelancer
else:
    emit_transfer(client, budget)       # refund the client
```

---

## 6. Deploy to Testnet

1. In GenLayer Studio, make sure `freelance_guard.py` is open
2. Click **Deploy** in the right panel
3. No constructor arguments required — click Confirm
4. Wait ~5 seconds for the transaction to finalize
5. Copy the contract address that appears

---

## 7. Interact Step by Step

### Step 1 — Post a job (as client)

In "Write Methods", expand `post_job`:

```
freelancer_address: "0xYOUR_SECOND_TEST_ADDRESS"
title: "Build a working calculator web app"
criteria: "A deployed web calculator accessible at the submitted URL.
           Must support addition, subtraction, multiplication, and division.
           Must work in a browser without any installation."
value (GEN to send): 10
```

Click **Run**. This creates Job ID `0` and locks 10 GEN in escrow.

### Step 2 — Submit work (as freelancer)

Switch to your second test account in Studio. Call `submit_work`:

```
job_id: 0
submission_url: "https://codepen.io/your-calculator"
```

Use any real, publicly accessible URL. The contract will fetch it live.

### Step 3 — Trigger evaluation

Call `evaluate_submission`:

```
job_id: 0
```

Watch the transaction status move through:
```
Pending → Proposing → Committing → Revealing → Finalized
```

Click the transaction hash to see:
- **Leader receipt** — what the first validator's LLM produced
- **Validator receipts** — each voter's comparison result
- **Votes** — agree / disagree from each validator

---

## 8. Read the Verdict On-Chain

Call `get_job(0)` and inspect the result:

```json
{
  "verdict": "accepted",
  "reason": "The submitted calculator is deployed and functional. All four operations work correctly. The interface loads without installation.",
  "budget": 0
}
```

`budget: 0` means the GEN was transferred — if accepted, to the freelancer; if rejected, back to the client.

---

## 9. Concepts Reference

| Concept | Explanation |
|---|---|
| **Intelligent Contract** | Python class extending `gl.Contract`. Can fetch web, call LLMs, and make subjective decisions on-chain. |
| **`gl.nondet.web.render(url)`** | Fetches a public URL at runtime. Each validator fetches independently. No oracle needed. |
| **`gl.nondet.exec_prompt(prompt)`** | Calls an LLM with a text prompt. Each validator uses their own model (GPT-4, Claude, LLaMA…). |
| **Optimistic Democracy** | Leader proposes result, validators verify. Supermajority consensus → finalized. |
| **Equivalence Principle** | Two validators' outputs are "equivalent" if they agree semantically — not necessarily identical text. |
| **`gl.vm.run_nondet_unsafe()`** | Runs the full consensus round with your custom leader and validator logic. |
| **`emit_transfer(address, amount)`** | Sends GEN tokens from the contract to any address. |
| **`TreeMap[K,V]`** | On-chain persistent mapping. Use instead of Python `dict`. |
| **`DynArray[T]`** | On-chain persistent array. Use instead of Python `list`. |
| **`gl.message.sender_account`** | Verified wallet address of the current transaction caller. |
| **`gl.message.value`** | GEN tokens sent with the current transaction (for payable methods). |

---

## 10. Common Mistakes to Avoid

### Mistake 1: LLM/web call outside inner function

```python
# ❌ WRONG
@gl.public.write
def evaluate(self):
    result = gl.nondet.exec_prompt("...")   # ERROR — must be inside inner fn

# ✅ CORRECT
@gl.public.write
def evaluate(self):
    def leader_fn():
        return gl.nondet.exec_prompt("...")
    result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
```

### Mistake 2: Accessing self inside nondet block

```python
# ❌ WRONG
def leader_fn():
    content = gl.nondet.web.render(self.url)   # ERROR — self not accessible

# ✅ CORRECT
url = self.url   # capture before
def leader_fn():
    content = gl.nondet.web.render(url)        # use captured local
```

### Mistake 3: Not reassigning to TreeMap

```python
# ❌ WRONG
job = self.jobs[job_id]
job.verdict = "accepted"   # NOT saved on-chain

# ✅ CORRECT
job = self.jobs[job_id]
job.verdict = "accepted"
self.jobs[job_id] = job    # ← this line is required
```

### Mistake 4: Using dict/list for persistent state

```python
# ❌ WRONG — lost after transaction
class MyContract(gl.Contract):
    jobs: dict   # not persisted

# ✅ CORRECT — persisted on-chain
class MyContract(gl.Contract):
    jobs: TreeMap[int, Job]
```

---

*Built for the GenLayer Educational Content mission — "From Zero to GenLayer"*  
*Verified against [docs.genlayer.com](https://docs.genlayer.com)*
