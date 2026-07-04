# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from genlayer import *


class AgoraGrants(gl.Contract):
    # ---- state (all strings / u256, JSON-in-string values) ----
    proposals: TreeMap[str, str]     # id -> proposal record JSON
    members: TreeMap[str, str]       # address -> member record JSON
    proposal_count: u256
    member_count: u256
    treasury: u256                   # virtual GEN units
    allocated: u256
    released: u256
    quorum: u256

    def __init__(self, treasury: int, quorum: int):
        self.proposal_count = u256(0)
        self.member_count = u256(0)
        self.treasury = u256(treasury)
        self.allocated = u256(0)
        self.released = u256(0)
        self.quorum = u256(quorum)

    # =================== helpers ===================

    def _get_proposal(self, proposal_id: str) -> dict:
        raw = self.proposals.get(str(proposal_id))
        if raw is None:
            raise gl.vm.UserError("Proposal not found")
        try:
            return json.loads(raw)
        except Exception:
            raise gl.vm.UserError("Corrupt proposal record")

    def _save_proposal(self, proposal_id: str, record: dict) -> None:
        self.proposals[str(proposal_id)] = str(json.dumps(record))

    def _get_member(self, address: str) -> dict | None:
        raw = self.members.get(str(address))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def _save_member(self, address: str, record: dict) -> None:
        self.members[str(address)] = str(json.dumps(record))

    def _require_member(self, address: str) -> dict:
        m = self._get_member(address)
        if m is None:
            raise gl.vm.UserError("Join the DAO first")
        return m

    # =================== writes: membership ===================

    @gl.public.write
    def join_dao(self) -> None:
        sender = str(gl.message.sender_address)
        if self._get_member(sender) is not None:
            raise gl.vm.UserError("Already a member")
        self._save_member(sender, {
            "joined": True, "reputation": 0, "submitted": 0, "completed": 0
        })
        self.member_count = u256(int(self.member_count) + 1)

    # =================== writes: proposals ===================

    @gl.public.write
    def create_proposal(self, title: str, summary: str, project_url: str,
                        budget: int, milestones_json: str) -> None:
        sender = str(gl.message.sender_address)
        member = self._require_member(sender)

        if not title or not summary or not project_url:
            raise gl.vm.UserError("Missing fields")
        if budget <= 0:
            raise gl.vm.UserError("Budget must be positive")
        if int(self.allocated) + budget > int(self.treasury):
            raise gl.vm.UserError("Budget exceeds unallocated treasury")

        try:
            milestones_in = json.loads(milestones_json)
        except Exception:
            raise gl.vm.UserError("Milestones must be valid JSON")
        if not isinstance(milestones_in, list) or not (2 <= len(milestones_in) <= 4):
            raise gl.vm.UserError("Provide 2 to 4 milestones")

        milestones = []
        base = budget // len(milestones_in)
        for i, m in enumerate(milestones_in):
            t = str(m.get("title", "")).strip()
            d = str(m.get("deliverable", "")).strip()
            if not t or not d:
                raise gl.vm.UserError("Every milestone needs a title and deliverable")
            tranche = base if i < len(milestones_in) - 1 else budget - base * (len(milestones_in) - 1)
            milestones.append({
                "title": t, "deliverable": d, "status": "LOCKED",
                "evidence_url": "", "verdict_reason": "", "tranche": tranche
            })

        pid = str(int(self.proposal_count) + 1)
        self.proposal_count = u256(int(pid))
        self._save_proposal(pid, {
            "id": pid, "title": str(title), "summary": str(summary),
            "project_url": str(project_url), "proposer": sender,
            "budget": budget, "status": "SUBMITTED",
            "votes_yes": 0, "votes_no": 0, "voters": [],
            "diligence": {}, "milestones": milestones
        })
        member["submitted"] = int(member.get("submitted", 0)) + 1
        self._save_member(sender, member)

    # =================== writes: AI screening ===================

    @gl.public.write
    def screen_proposal(self, proposal_id: str) -> None:
        record = self._get_proposal(proposal_id)
        if record["status"] != "SUBMITTED":
            raise gl.vm.UserError("Proposal already screened")

        title = record["title"]
        summary = record["summary"]
        url = record["project_url"]
        milestones_text = " | ".join(
            m["title"] + ": " + m["deliverable"] for m in record["milestones"]
        )
        budget = record["budget"]

        def do_screening() -> str:
            page_text = ""
            try:
                fetch_url = url
                if "github.com/" in url:
                    parts = url.split("github.com/")[1].strip("/").split("/")
                    if len(parts) >= 1 and parts[0]:
                        fetch_url = "https://api.github.com/users/" + parts[0] + "/repos?sort=updated&per_page=10"
                    if len(parts) >= 2 and parts[1]:
                        fetch_url = "https://api.github.com/repos/" + parts[0] + "/" + parts[1]
                page_text = gl.nondet.web.render(fetch_url, mode="text")
                if page_text is None:
                    page_text = ""
                page_text = str(page_text)[:4000]
            except Exception:
                page_text = "FETCH_FAILED"

            prompt = (
                "You are a grant due-diligence analyst for a DAO. Assess this proposal.\n"
                "PROPOSAL TITLE: " + title + "\n"
                "SUMMARY: " + summary + "\n"
                "REQUESTED BUDGET: " + str(budget) + " GEN\n"
                "MILESTONES: " + milestones_text + "\n"
                "PROJECT LINK CONTENT (may be FETCH_FAILED): " + page_text + "\n\n"
                "Respond ONLY with JSON, no markdown, exactly these keys:\n"
                '{"score": <integer 1-10 feasibility/credibility>, '
                '"strengths": "<one or two sentences>", '
                '"risks": "<one or two sentences>", '
                '"recommendation": "<FUND or REJECT>"}'
            )
            try:
                result = gl.nondet.exec_prompt(prompt, response_format="json")
                if isinstance(result, dict):
                    return json.dumps(result)
                return str(result)
            except Exception:
                return json.dumps({"score": 0, "strengths": "",
                                   "risks": "Screening failed - AI unavailable",
                                   "recommendation": "RETRY"})

        criteria = (
            "The output must be valid JSON with keys score, strengths, risks, recommendation. "
            "score must be an integer 1-10 or 0 on failure. recommendation must be FUND, REJECT or RETRY. "
            "Validators may word strengths and risks differently and give scores within 2 points of "
            "each other - these differences are acceptable. A failed fetch or RETRY output is a valid result."
        )

        try:
            raw = gl.eq_principle.prompt_non_comparative(
                do_screening,
                task="Perform due diligence on a DAO grant proposal and output a JSON verdict",
                criteria=criteria
            )
        except Exception:
            return  # consensus failed entirely; state untouched, retry later

        try:
            diligence = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(diligence, dict):
                return
        except Exception:
            return

        if str(diligence.get("recommendation", "")) == "RETRY":
            return  # preserve SUBMITTED so screening can be retried

        record["diligence"] = {
            "score": int(diligence.get("score", 0)),
            "strengths": str(diligence.get("strengths", "")),
            "risks": str(diligence.get("risks", "")),
            "recommendation": str(diligence.get("recommendation", "REJECT"))
        }
        record["status"] = "SCREENED"
        self._save_proposal(proposal_id, record)

    # =================== writes: voting ===================

    @gl.public.write
    def vote(self, proposal_id: str, support: bool) -> None:
        sender = str(gl.message.sender_address)
        self._require_member(sender)
        record = self._get_proposal(proposal_id)
        if record["status"] != "SCREENED":
            raise gl.vm.UserError("Voting is not open for this proposal")
        if sender in record["voters"]:
            raise gl.vm.UserError("Already voted")
        record["voters"].append(sender)
        if support:
            record["votes_yes"] = int(record["votes_yes"]) + 1
        else:
            record["votes_no"] = int(record["votes_no"]) + 1
        self._save_proposal(proposal_id, record)

    @gl.public.write
    def finalize_vote(self, proposal_id: str) -> None:
        record = self._get_proposal(proposal_id)
        if record["status"] != "SCREENED":
            raise gl.vm.UserError("Nothing to finalize")
        total = int(record["votes_yes"]) + int(record["votes_no"])
        if total < int(self.quorum):
            raise gl.vm.UserError("Quorum not reached: " + str(total) + "/" + str(int(self.quorum)))
        if int(record["votes_yes"]) > int(record["votes_no"]):
            budget = int(record["budget"])
            if int(self.allocated) + budget > int(self.treasury):
                record["status"] = "REJECTED"
            else:
                record["status"] = "APPROVED"
                self.allocated = u256(int(self.allocated) + budget)
                record["milestones"][0]["status"] = "ACTIVE"
        else:
            record["status"] = "REJECTED"
        self._save_proposal(proposal_id, record)

    # =================== writes: milestones ===================

    @gl.public.write
    def submit_evidence(self, proposal_id: str, milestone_index: int, evidence_url: str) -> None:
        sender = str(gl.message.sender_address)
        record = self._get_proposal(proposal_id)
        if sender != record["proposer"]:
            raise gl.vm.UserError("Only the proposer submits evidence")
        if record["status"] != "APPROVED":
            raise gl.vm.UserError("Proposal is not funded")
        ms = record["milestones"]
        if milestone_index < 0 or milestone_index >= len(ms):
            raise gl.vm.UserError("Bad milestone index")
        m = ms[milestone_index]
        if m["status"] not in ("ACTIVE", "FAILED"):
            raise gl.vm.UserError("Milestone is not open for evidence")
        if not evidence_url:
            raise gl.vm.UserError("Evidence URL required")
        m["evidence_url"] = str(evidence_url)
        m["status"] = "PENDING_REVIEW"
        self._save_proposal(proposal_id, record)

    @gl.public.write
    def verify_milestone(self, proposal_id: str, milestone_index: int) -> None:
        record = self._get_proposal(proposal_id)
        if record["status"] != "APPROVED":
            raise gl.vm.UserError("Proposal is not funded")
        ms = record["milestones"]
        if milestone_index < 0 or milestone_index >= len(ms):
            raise gl.vm.UserError("Bad milestone index")
        m = ms[milestone_index]
        if m["status"] != "PENDING_REVIEW":
            raise gl.vm.UserError("No evidence pending review")

        deliverable = m["deliverable"]
        evidence_url = m["evidence_url"]
        project_title = record["title"]

        def do_verification() -> str:
            page_text = ""
            try:
                fetch_url = evidence_url
                if "github.com/" in evidence_url:
                    parts = evidence_url.split("github.com/")[1].strip("/").split("/")
                    if len(parts) >= 2 and parts[0] and parts[1]:
                        fetch_url = "https://api.github.com/repos/" + parts[0] + "/" + parts[1]
                page_text = gl.nondet.web.render(fetch_url, mode="text")
                if page_text is None:
                    page_text = ""
                page_text = str(page_text)[:4000]
            except Exception:
                page_text = "FETCH_FAILED"

            prompt = (
                "You are verifying a grant milestone for a DAO. Be strict but fair.\n"
                "PROJECT: " + project_title + "\n"
                "PROMISED DELIVERABLE: " + deliverable + "\n"
                "EVIDENCE URL: " + evidence_url + "\n"
                "FETCHED EVIDENCE CONTENT (may be FETCH_FAILED): " + page_text + "\n\n"
                "If content is FETCH_FAILED or empty, verdict must be UNREACHABLE.\n"
                "Otherwise judge whether the evidence plausibly satisfies the promised deliverable.\n"
                "Respond ONLY with JSON, no markdown, exactly these keys:\n"
                '{"verdict": "<PASSED or FAILED or UNREACHABLE>", '
                '"reason": "<one or two sentences>"}'
            )
            try:
                result = gl.nondet.exec_prompt(prompt, response_format="json")
                if isinstance(result, dict):
                    return json.dumps(result)
                return str(result)
            except Exception:
                return json.dumps({"verdict": "UNREACHABLE",
                                   "reason": "Verification failed - AI unavailable"})

        criteria = (
            "The output must be valid JSON with keys verdict and reason. "
            "verdict must be PASSED, FAILED or UNREACHABLE. Validators may word the reason "
            "differently - that is acceptable as long as the verdict is justified by the evidence. "
            "UNREACHABLE is the correct verdict whenever the evidence could not be fetched."
        )

        try:
            raw = gl.eq_principle.prompt_non_comparative(
                do_verification,
                task="Verify whether milestone evidence satisfies the promised deliverable and output a JSON verdict",
                criteria=criteria
            )
        except Exception:
            return  # consensus failure; milestone stays PENDING_REVIEW for retry

        try:
            verdict = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(verdict, dict):
                return
        except Exception:
            return

        v = str(verdict.get("verdict", "UNREACHABLE"))
        reason = str(verdict.get("reason", ""))

        if v == "PASSED":
            m["status"] = "PASSED"
            m["verdict_reason"] = reason
            self.released = u256(int(self.released) + int(m["tranche"]))
            if milestone_index + 1 < len(ms):
                ms[milestone_index + 1]["status"] = "ACTIVE"
            else:
                record["status"] = "COMPLETE"
                proposer = self._get_member(record["proposer"])
                if proposer is not None:
                    proposer["reputation"] = int(proposer.get("reputation", 0)) + 1
                    proposer["completed"] = int(proposer.get("completed", 0)) + 1
                    self._save_member(record["proposer"], proposer)
        elif v == "FAILED":
            m["status"] = "FAILED"
            m["verdict_reason"] = reason
        else:  # UNREACHABLE — keep PENDING_REVIEW untouched for retry
            m["verdict_reason"] = "Evidence unreachable - resubmit or retry: " + reason

        self._save_proposal(proposal_id, record)

    # =================== views (JSON strings) ===================

    @gl.public.view
    def get_stats(self) -> str:
        return json.dumps({
            "members": int(self.member_count),
            "treasury": int(self.treasury),
            "allocated": int(self.allocated),
            "released": int(self.released),
            "proposals": int(self.proposal_count),
            "quorum": int(self.quorum)
        })

    @gl.public.view
    def get_all_proposals(self) -> str:
        out = []
        for i in range(1, int(self.proposal_count) + 1):
            raw = self.proposals.get(str(i))
            if raw is None:
                continue
            try:
                p = json.loads(raw)
            except Exception:
                continue
            out.append({
                "id": p.get("id"), "title": p.get("title"),
                "proposer": p.get("proposer"), "budget": p.get("budget"),
                "status": p.get("status"),
                "votes_yes": p.get("votes_yes"), "votes_no": p.get("votes_no")
            })
        return json.dumps(out)

    @gl.public.view
    def get_proposal(self, proposal_id: str) -> str:
        raw = self.proposals.get(str(proposal_id))
        if raw is None:
            return json.dumps(None)
        return raw

    @gl.public.view
    def get_member(self, address: str) -> str:
        raw = self.members.get(str(address))
        if raw is None:
            return json.dumps({"joined": False, "reputation": 0, "submitted": 0, "completed": 0})
        return raw
