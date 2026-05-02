# Agent2 Demo Script — YC Video + Twitter

Target: 1:30-2:00 min. One take, screen recording with voiceover.

## Setup Before Recording

```bash
rm -rf /tmp/agent2-demo
# Pre-validate the OpenRouter key works
export $(grep -v '^#' .env | xargs)
uv run python -c "
from shared.config import Settings
s = Settings.from_env()
assert s.has_llm_key, 'No key!'
print('Key OK:', s.openrouter_api_key[:15] + '...')
"
```

## Twitter Hook (first 3 seconds)

**On screen:** Terminal with `getagent2.dev` visible
**Voiceover:** "One command. Your domain expert becomes a production AI agent."

---

## Scene 1: The Install (0:00-0:15)

**On screen:** Clean terminal, type:
```bash
curl -fsSL https://getagent2.dev/install.sh | bash
```

**Show:** The ASCII logo, stage counters, "Agent2 is ready!"

**Voiceover:** "Agent2 installs in 60 seconds. Git, Python, Docker — it checks
everything and sets up your stack."

**Cut to:** Setup wizard already running (pre-recorded, speed up 2x)

---

## Scene 2: The Brain Clone Interview (0:15-1:00)

**On screen:** `uv run agent2 onboard --agentic --overwrite`

The LLM interviewer asks questions. You answer with these pre-written responses:

### Roleplay: Procurement Compliance Officer

**Q: "What's your professional role?"**
A: "I'm a procurement compliance officer. 12 years experience. I review purchase
requests and make sure they follow company policy before they get approved."

**Q: "Walk me through how you handle a case."**
A: "First I check who's requesting and what department. Then I look at the amount
and vendor. If it's over 25k I check if there's a competitive quote. I look up
the vendor in our risk database. Then I either approve, ask for more info, or
reject."

**Q: "When do you ask for more information?"**
A: "When the business justification is vague, when there's no competitive quote
for sole-source requests, or when a new vendor hasn't gone through onboarding."

**Q: "When do you reject?"**
A: "Blocked vendor, policy violation, or if the request is clearly fabricated.
That's rare but it happens."

**Q: "What reference materials do you use?"**
A: "Company procurement policy handbook, vendor risk guidelines, and approval
threshold tables. I also check past purchase history for the vendor."

**After 5-6 questions, type:** "done"

**Voiceover:** "The Brain Clone interview extracts how you think. Not a form —
a conversation. It adapts based on your answers."

**Show:** The Agent Spec panel appearing with name, role, tools, knowledge, outcomes.

**Voiceover:** "From that conversation, Agent2 generates a complete production agent."

---

## Scene 3: The Agent Works (1:00-1:30)

**On screen:** The agent is running. Send a test request:
```bash
uv run agent2 run procurement-compliance-officer \
  --text "Purchase request: 50 laptops from Acme Hardware, $42,000, Engineering dept"
```

**Show:** The JSON response with:
- `"status": "approved"` or `"needs_clarification"`
- `"review_steps": ["Check request", "Verify vendor", ...]`
- `"confidence": 0.88`
- `"pending_actions": [{"action": "create_approval_record", ...}]`

**Voiceover:** "The agent doesn't just answer. It reasons through your Chain-of-Thought,
searches your policy books, checks the vendor, and returns a typed, validated decision.
With human approval before any side effects."

---

## Scene 4: The Pitch (1:30-1:45)

**On screen:** getagent2.dev landing page

**Voiceover:** "Agent2 is open source. We've processed 4 million documents and
generated 160k in revenue cloning a 20-year accounting expert. Now we're
open-sourcing the engine. Try it — one command."

**Show:** The curl command prominently

---

## Twitter Post

**Text:**
```
Turn domain experts into production AI agents.

One command installs it. An AI interview extracts how you think.
A typed API comes out the other side.

Open source. MIT licensed. Born from $160k in real revenue.

→ getagent2.dev
```

**Reply to own tweet:**
```
How it works:
1. curl install → setup wizard
2. Brain Clone interview extracts your expertise
3. Agent gets: Chain-of-Thought, tools, knowledge search, typed output
4. Deploy as API — runs 24/7

Not a prompt wrapper. A cloned professional.

GitHub: github.com/duozokker/agent2
```

**Tag:** @garaborocos (Garry Tan) @daltonc (Dalton Caldwell) @jlowin (Jason Lowin, PrefectHQ)
