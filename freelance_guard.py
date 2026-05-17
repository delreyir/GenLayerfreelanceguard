# { "Depends": "py-genlayer:test" }
# ══════════════════════════════════════════════════════════════════════════════
#  FreelanceGuard — AI-Powered Freelance Dispute Resolver
#  An Intelligent Contract built on GenLayer
#
#  ✅ REAL GenLayer SDK (verified against docs.genlayer.com 2025):
#     · gl.nondet.web.render(url, mode='text')      → live web fetch, no oracle
#     · gl.nondet.exec_prompt(prompt, ...)           → LLM call inside consensus
#     · gl.vm.run_nondet_unsafe(leader_fn, val_fn)   → Optimistic Democracy
#     · @gl.public.write.payable                     → receive GEN tokens
#     · gl.message.value / gl.message.sender_account → tx context
#     · emit_transfer(address, amount)               → send GEN tokens
#     · TreeMap[K,V] / DynArray[T]                   → persistent on-chain storage
#
#  ⚠️  CRITICAL RULES (from official docs):
#     1. Web/LLM calls MUST be inside an inner function — never directly in method
#     2. You CANNOT access `self` inside a nondet block — capture locals first
#     3. Always reassign modified objects back: self.jobs[id] = job
#     4. Use TreeMap not dict, DynArray not list for persistent state
# ══════════════════════════════════════════════════════════════════════════════

from genlayer import *
from dataclasses import dataclass
import json


# ── Data Structure ─────────────────────────────────────────────────────────────

@dataclass
class Job:
    """A freelance job stored on-chain."""
    job_id:         int
    client:         str    # verified via gl.message.sender_account
    freelancer:     str    # assigned at job creation
    title:          str
    criteria:       str    # plain-English — read directly by LLM
    budget:         u256   # GEN tokens in escrow (u256 = GenLayer native uint)
    submission_url: str    # fetched live at evaluation time
    verdict:        str    # "pending" | "accepted" | "rejected"
    reason:         str    # LLM explanation stored on-chain
    is_submitted:   bool


# ── Contract ───────────────────────────────────────────────────────────────────

class FreelanceGuard(gl.Contract):
    """
    FreelanceGuard — trustless escrow with AI dispute resolution.

    GenLayer features used:
      · Live web access   → gl.nondet.web.render()
      · LLM reasoning     → gl.nondet.exec_prompt()
      · Consensus         → gl.vm.run_nondet_unsafe()
      · Native payments   → @gl.public.write.payable + emit_transfer()
    """

    # On-chain persistent state — TreeMap/DynArray required (not dict/list)
    jobs:            TreeMap[int, Job]
    next_id:         int
    client_jobs:     TreeMap[str, DynArray[int]]
    freelancer_jobs: TreeMap[str, DynArray[int]]

    def __init__(self):
        self.next_id = 0
        self.jobs = TreeMap()
        self.client_jobs = TreeMap()
        self.freelancer_jobs = TreeMap()

    # ── Method 1: Client posts a job ───────────────────────────────────────────

    @gl.public.write.payable
    def post_job(
        self,
        freelancer_address: str,
        title: str,
        criteria: str,
    ) -> int:
        """
        Create a job and lock GEN tokens in escrow.

        Send GEN with this transaction — that becomes the budget.
        The criteria field is plain English: "A deployed React app with
        a hero section and contact form." The LLM reads it as-is.

        Returns: job_id (int) — save this for future calls.
        """
        assert gl.message.value > 0, "Must send GEN to fund the escrow"
        assert len(criteria.strip()) >= 20, "Criteria too short — be descriptive"

        job_id = self.next_id
        self.next_id += 1

        job = Job(
            job_id         = job_id,
            client         = gl.message.sender_account,  # verified caller
            freelancer     = freelancer_address,
            title          = title,
            criteria       = criteria,
            budget         = gl.message.value,           # GEN locked here
            submission_url = "",
            verdict        = "pending",
            reason         = "",
            is_submitted   = False,
        )
        self.jobs[job_id] = job

        # Index by address for convenience reads
        if gl.message.sender_account not in self.client_jobs:
            self.client_jobs[gl.message.sender_account] = DynArray()
        self.client_jobs[gl.message.sender_account].append(job_id)

        if freelancer_address not in self.freelancer_jobs:
            self.freelancer_jobs[freelancer_address] = DynArray()
        self.freelancer_jobs[freelancer_address].append(job_id)

        return job_id

    # ── Method 2: Freelancer submits work ──────────────────────────────────────

    @gl.public.write
    def submit_work(self, job_id: int, submission_url: str) -> None:
        """
        Freelancer submits a public URL pointing to their delivered work.

        The URL is fetched live by every validator at evaluation time —
        no need to copy content into the transaction.
        """
        assert job_id in self.jobs, "Job not found"
        job = self.jobs[job_id]

        # gl.message.sender_account is cryptographically verified — cannot be spoofed
        assert gl.message.sender_account == job.freelancer, \
            "Only the assigned freelancer can submit"
        assert job.verdict == "pending", "Job already resolved"
        assert submission_url.startswith("http"), "Must be a valid public URL"

        job.submission_url = submission_url
        job.is_submitted   = True
        self.jobs[job_id]  = job   # ← must reassign — mutation alone doesn't persist

    # ── Method 3: AI evaluation (core of the contract) ─────────────────────────

    @gl.public.write
    def evaluate_submission(self, job_id: int) -> None:
        """
        Trigger AI evaluation of the submitted work.

        GenLayer flow:
          1. leader_fn() → each validator fetches URL live + calls LLM
          2. validator_fn() → checks if leader and validator agree on verdict
          3. gl.vm.run_nondet_unsafe() → Optimistic Democracy resolves consensus
          4. emit_transfer() → funds released automatically

        Anyone can call this once work is submitted — fully permissionless.
        """
        assert job_id in self.jobs, "Job not found"
        job = self.jobs[job_id]
        assert job.is_submitted, "Freelancer has not submitted work yet"
        assert job.verdict == "pending", "Job already evaluated"

        # ── RULE: Capture locals before nondet block — self not accessible inside ──
        title      = job.title
        criteria   = job.criteria
        submit_url = job.submission_url
        client     = job.client
        freelancer = job.freelancer
        budget     = job.budget

        # ── Leader: fetch URL live + call LLM ─────────────────────────────────
        # ⚠️ RULE: Web/LLM calls must be inside an inner function, not in method body
        def leader_fn() -> str:
            # Fetch the live submission — no oracle, each validator fetches independently
            content = gl.nondet.web.render(submit_url, mode="text")

            prompt = f"""You are an impartial freelance work evaluator on a decentralized platform.

JOB TITLE: {title}

ACCEPTANCE CRITERIA (agreed by client and freelancer):
{criteria}

SUBMISSION URL: {submit_url}

CONTENT FETCHED FROM SUBMISSION:
{content[:3000]}

EVALUATION TASK:
Does the submitted work satisfy ALL of the acceptance criteria above?
Be objective and fair. Minor imperfections are acceptable; missing core
requirements are not.

Respond ONLY with valid JSON. No markdown. No extra text:
{{"verdict": "accepted" or "rejected", "reason": "one clear paragraph"}}"""

            result = gl.nondet.exec_prompt(prompt, response_format="json")

            # Normalize to a stable string for consensus comparison
            return json.dumps({
                "verdict": result.get("verdict", "rejected"),
                "reason":  result.get("reason", "")
            }, sort_keys=True)

        # ── Validator: re-run independently + check equivalence ───────────────
        def validator_fn(leaders_result) -> bool:
            if not isinstance(leaders_result, gl.vm.Return):
                return False

            # Validator runs the same evaluation with its own LLM
            my_raw   = leader_fn()
            leader_d = json.loads(leaders_result.calldata)
            mine_d   = json.loads(my_raw)

            # Equivalence check: do both agree on accept/reject?
            # We compare the decision, not the exact wording of the reason
            return leader_d.get("verdict") == mine_d.get("verdict")

        # ── Optimistic Democracy consensus ────────────────────────────────────
        raw    = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        parsed = json.loads(raw) if isinstance(raw, str) else raw

        verdict = parsed.get("verdict", "rejected").lower()
        reason  = parsed.get("reason", "No reason provided.")

        # ── Update on-chain state ─────────────────────────────────────────────
        job.verdict       = verdict
        job.reason        = reason
        self.jobs[job_id] = job   # ← must reassign

        # ── Auto-release funds based on AI verdict ────────────────────────────
        if verdict == "accepted":
            emit_transfer(freelancer, budget)   # 🎉 pay the freelancer
        else:
            emit_transfer(client, budget)       # 🔄 refund the client

    # ── Read (view) methods ────────────────────────────────────────────────────

    @gl.public.view
    def get_job(self, job_id: int) -> Job:
        """Return full details of a job by ID."""
        assert job_id in self.jobs, "Job not found"
        return self.jobs[job_id]

    @gl.public.view
    def get_client_jobs(self, address: str) -> list:
        """Return all job IDs posted by a given client address."""
        if address not in self.client_jobs:
            return []
        return list(self.client_jobs[address])

    @gl.public.view
    def get_freelancer_jobs(self, address: str) -> list:
        """Return all job IDs assigned to a given freelancer address."""
        if address not in self.freelancer_jobs:
            return []
        return list(self.freelancer_jobs[address])

    @gl.public.view
    def total_jobs(self) -> int:
        """Return total number of jobs ever created."""
        return self.next_id
