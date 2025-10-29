EXTRACT_COMMITMENTS = """
# Extract Commitments from Mastermind Call

**Task:** Find what each participant commits to doing next week.

**Output Format:**
### [Participant Name]
**What They Discussed:** [2-3 sentences]
**Commitment:** [Exact quote OR "No specific commitment made"]
**Quote:** "[Direct quote]" OR "N/A"
**Timestamp:** [Time] OR "N/A"
---

**Rules:**
- Only explicit commitments (not implied)
- Use exact quotes
- Include all speakers
- If no commitment, state clearly

**Example:**
### Sarah Johnson
**What They Discussed:** Sarah shared struggles with lead generation and inconsistent outreach.
**Commitment:** "I will make 5 sales calls this week"
**Quote:** "I will make 5 sales calls this week"
**Timestamp:** (15m 30s)

Transcript:
{transcript}
"""


CLASSIFY_COMMITMENTS = """
# Classify Commitments by Quantifiability

**Task:** Determine if each commitment is measurable or needs clarification.

**Output Format:**
### [Participant Name]
[Keep original sections]
**Classification:** [Quantifiable/Not Quantifiable/No Goal/Decision Pending]
**Why:** [One sentence explanation]
**Suggestion:** [How to make quantifiable] OR "N/A"
---

**Rules:**
- **Quantifiable**: Has specific numbers, deadlines, or completion points
- **Not Quantifiable**: Vague without measurable criteria
- **No Goal**: No commitment made
- **Decision Pending**: Waiting on external factors
- Be strict: when in doubt, "Not Quantifiable"

**Example:**
### Sarah Johnson
[Original content preserved]
**Classification:** Quantifiable
**Why:** Contains specific number "5" and clear action "sales calls"
**Suggestion:** N/A

Extracted Commitments:
{commitments}
"""


MARKETING_ACTIVITY_EXTRACTION = """
Extract marketing activities by participant and classify them.

Categories:
- Network Activation: Outreach to existing relationships/referrals (warm intros, past clients, even if on LinkedIn)
- LinkedIn: New relationships or engagement on LinkedIn (new connections, posting, commenting)
- Cold Outreach: Contacting strangers outside LinkedIn (cold emails, cold calls)

Output Format:
Name: [Participant Name]
- Network Activation: [activity, qty if mentioned]
- LinkedIn: [activity, qty if mentioned]
- Cold Outreach: [activity, qty if mentioned]

If no marketing activity: "No marketing activity mentioned."

Examples:
Name: Juliana
- Network Activation: DM'd 5 past clients on LinkedIn
- LinkedIn: Posted twice

Name: Ben
No marketing activity mentioned.

Transcript:
{transcript}
"""

PIPELINE_OUTCOME_EXTRACTION = """
Extract pipeline outcomes per participant: meetings, proposals, clients.

Output Format:
Name: [Participant Name]
Meetings: [#]
Proposals: [#]
Clients: [#]
Notes: [brief context]

Use 0 if not mentioned.

Examples:
Name: Chris
Meetings: 3
Proposals: 1
Clients: 0
Notes: Three discovery calls, one proposal sent

Name: Mackenzie
Meetings: 0
Proposals: 2
Clients: 0
Notes: Two proposals planned

Transcript:
{transcript}
"""

CHALLENGE_STRATEGY_EXTRACTION = """
Extract participant challenges and strategies shared during the call. Tag each challenge with the most relevant category.

Output Format:
Name: [Participant Name]
Challenge: [Summarize core challenge in 1-2 sentences. If implicit, infer clearly.]
Category: [Pick ONE category from list below, or propose NEW CATEGORY if none fit]
Strategies/Tips:
- [Who shared it: short actionable summary + strategy type tag]

Challenge Categories:
- Clarity - Unclear goals, positioning, priorities
- Lead Generation - Not enough qualified leads, inconsistent pipeline
- Sales & Conversion - Trouble converting leads, pricing issues, follow-up gaps
- Systems & Operations - Lacking processes, delegation gaps, tool confusion
- Time & Focus - Overwhelm, poor prioritization, no protected strategy time
- Team & Delegation - Hiring, training, management issues
- Mindset / Emotional - Fear, perfectionism, overthinking, burnout
- Scaling & Offers - Bottlenecks moving from solo to leveraged model, unclear scalable offer
- Other - Doesn't fit above (propose new category if needed like [NEW CATEGORY: Partnerships])

Strategy Type Tags:
- Mindset Reframe - Perspective or belief shift
- Tactical Process - Step-by-step action or method
- Tool / Resource Suggestion - Specific tool, template, or resource
- Connection / Referral - Intro, referral, or networking suggestion
- Framework / Model Shared - Structure, model, or named methodology

Rules:
- Challenge can be explicit or implicit (infer if needed)
- Strategies can come from anyone (facilitator, peers, or themselves)
- Ignore casual chatter and vague venting
- Be concise and actionable

Examples:
Name: Juliana
Challenge: She's unclear on how to structure her recurring offer for CFO services, leading to inconsistent proposals.
Category: Scaling & Offers
Strategies/Tips:
- Tanya suggested creating a simple recurring retainer anchored on one clear outcome. (Tactical Process)
- Kevin recommended talking to 3 current clients this week to identify which service they'd pay for monthly. (Tactical Process)

Name: Jeff
Challenge: Implicit - He's doing a lot of marketing activity but not booking meetings, indicating a messaging misalignment.
Category: Lead Generation
Strategies/Tips:
- Juliana shared how refining her LinkedIn headline led to 5 new calls in 2 weeks. (Tactical Process)
- Tanya advised focusing on one marketing channel for 4 weeks instead of juggling three. (Tactical Process)

Transcript:
{transcript}
"""

GENERATE_NUDGES = """
# Generate Accountability Nudges

**Task:** Create personalized messages for participants without quantifiable goals.

**Output Format:**
### [Participant Name]
[Keep previous sections]
**Nudge Message:**
> @[Name] [Acknowledge their work]
> 
> I noticed you didn't set a **quantifiable goal** during the call.
> 
> Here are a few options:
> • [Emoji] [Goal with number/deadline]
> • [Emoji] [Goal with number/deadline]
> • [Emoji] [Goal with number/deadline]
> 
> Want me to hold you accountable to one of these?

**Rules:**
- Only for "Not Quantifiable" or "No Goal"
- "N/A" for quantifiable goals
- Max 150 words
- Friendly tone
- Specific numbers/deadlines

Classified Commitments:
{classified_commitments}
"""

STUCK_SIGNAL_EXTRACTION = """
You are an expert mastermind transcript analyst. Identify when participants express being stuck, stalled, or not making progress.

Look for:
- Self-reported stuckness: "I'm stuck," "I haven't done anything," "I don't know why," "I can't seem to move forward"
- Implied stuckness: repeating same goal for multiple weeks, "spinning wheels," "lapses," "feeling off"
- Low momentum, overwhelm, confusion, procrastination, emotional blockers

Output Format:
[PARTICIPANT NAME]
Stuck Summary:
[Briefly explain what kind of stuckness and why - motivation lapse, repeating old goals, overwhelm, unclear next steps, emotional stuckness]
Exact Quotes:
[1-3 most revealing quotes verbatim]
Timestamp:
(Start-End)
Stuck Classification:
[Momentum Drop / Emotional Block / Overwhelm / Decision Paralysis / Repeating Goal / Other]
Potential Next Step or Nudge (Optional):
[Light-touch suggestion, e.g., "Book momentum-reset session," "Break into micro-goals," "Pair up for co-working"]

Classifications:
- Momentum Drop: Lost rhythm/progress temporarily ("I haven't done anything for two weeks")
- Emotional Block: Frustration, shame, fear, perfectionism loops ("I don't know why, I just can't get started")
- Overwhelm: Too many things, unclear priorities, capacity issues
- Decision Paralysis: Unsure which path to take
- Repeating Goal: Same goal multiple weeks without movement
- Other: Doesn't fit above

Example:
Mack Earnhardt
Stuck Summary:
Mack felt completely stuck for the last two weeks, describing lapses where he can't get off "Square Zero." He's made no progress on his goals and is still working on the same thing from two weeks ago.
Exact Quotes:
"I have felt completely stuck for the last two weeks."
"I don't feel like I've gotten anything done."
"I just can't seem to get… off of Square Zero."
Timestamp:
(48m 45s–49m 44s)
Stuck Classification:
Momentum Drop + Emotional Block
Potential Next Step or Nudge (Optional):
Book a short momentum reset session and break the work into 1-2 micro-goals to rebuild rhythm.

Transcript:
{transcript}
"""

HELP_OFFER_EXTRACTION = """
# Extract Help Offers

**Task:** Find when participants offer to help, support, or provide expertise to others.

**Output Format:**
### [PARTICIPANT NAME]
**What They Offered:** [Type of help offered]
**Context:** [Why this help is relevant]
**Exact Quote:** "[Exact words used]"
**Timestamp:** (XXm XXs)
**Classification:** [Expertise/Resource/General Support/Introductions/Review & Feedback]

**Classifications:**
- **Expertise:** Knowledge/skill in specific domain
- **Resource:** Document, tool, or contact sharing
- **General Support:** Open-ended help
- **Introductions:** Connecting people
- **Review & Feedback:** Looking over materials

**Example:**
### Jon Benedict
**What They Offered:** Expertise in healthcare, especially HIPAA privacy compliance
**Context:** Jon works with hospitals and has deep HIPAA experience
**Exact Quote:** "If there's anything I can do to support anybody, especially healthcare client or HIPAA privacy question, just reach out"
**Timestamp:** (45m 32s)
**Classification:** Expertise

Transcript:
{transcript}
"""

SENTIMENT_ANALYSIS = """
# Analyze Call Sentiment & Group Health

**Task:** Analyze emotional tone to detect morale shifts and group health.

**Output Format:**
**Sentiment Score:** [1-5]
**Rationale:** [1-2 sentences explaining score]
**Dominant Emotions:** [2-4 emotional tags]
**Representative Quotes:** [1-3 quotes with names]
**Confidence Score:** [0-1]
**Negative Participants:** [List with emotions and evidence]

**Scoring:**
- **5 – High Positive:** Multiple wins, excitement, laughter, celebration
- **4 – Positive:** General optimism, some wins, supportive energy
- **3 – Neutral/Mixed:** Balanced tone, some excitement, some frustrations
- **2 – Negative:** Several stuck/low energy, few wins, venting
- **1 – Very Negative:** Predominantly stuck, frustrated, demoralized

**Example:**
**Sentiment Score:** 4 (Positive)
**Rationale:** Generally upbeat tone with wins shared and supportive responses
**Dominant Emotions:** supportive, optimistic, frustrated, stuck
**Representative Quotes:** 
- Mark Alcazar: "I'm meeting with him tomorrow, like, holy shit, wow—great!"
- Mack Earnhardt: "I have felt completely stuck for the last two weeks."
**Confidence Score:** 0.82
**Negative Participants:**
- Mack Earnhardt: stuck, low energy - "I have felt completely stuck for the last two weeks"

Transcript:
{transcript}
"""

# Load prompts from markdown files if available
import os

_prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')

def _load_prompt_from_file(filename: str) -> str:
    """Load a prompt from a markdown file"""
    filepath = os.path.join(_prompts_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return None

# Try to load GOAL_EXTRACTION from markdown file
_goal_extraction_content = _load_prompt_from_file('goal_extraction.md')
if _goal_extraction_content:
    # The markdown file should be ready to use with {transcript} placeholder
    GOAL_EXTRACTION = _goal_extraction_content.replace('[Transcript goes here]', '{transcript}')
else:
    # Fallback: create a basic prompt if file not found
    GOAL_EXTRACTION = """Extract quantifiable goals from the transcript. Use the format specified in goal_extraction.md.

Transcript:
{transcript}
"""