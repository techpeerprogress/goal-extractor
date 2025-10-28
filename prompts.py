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

EXTRACT_QUANTIFIABLE_GOALS = """
# Extract Goals (Quantifiable and Non-Quantifiable)

**Task:** Find ALL goals/commitments that participants commit to, then classify them as quantifiable or not.

**Output Format:**
### [Participant Name]
**Quantifiable Goals:**
[Goal 1: "I will make 5 sales calls this week"]
[Goal 2: "Post 3 times on LinkedIn"]
[If none: "No quantifiable goals mentioned"]

**Non-Quantifiable Goals:**
[Goal 1: "I plan to do outreach"]
[Goal 2: "I want to network more"]
[Goal 3: "Plan to play basketball"]
[If none: "No non-quantifiable goals mentioned"]
---

**Rules:**
- **Quantifiable**: Has specific numbers, deadlines, or measurable outcomes (e.g., "make 5 calls", "post 3 times", "jog 10km")
- **Non-Quantifiable**: Vague goals without specific metrics or numbers (e.g., "plan to do outreach", "want to network more", "plan to play basketball", "plan to jog" without distance)
- **MUST INCLUDE**: All goals that participants commit to, even if not quantifiable - mark them as "Non-Quantifiable Goals"
- **MUST EXCLUDE**: 
  - Attendance information (who attended/didn't attend meetings)
  - Scheduling information (meeting times, availability)
  - Personal life circumstances not related to commitments
  - Information that's purely observational or informational
- When in doubt about whether something is a goal vs. information, ask: "Did the person commit to DOING this?" If yes, include it (as quantifiable or non-quantifiable). If no, exclude it.

**Examples of Non-Quantifiable Goals to INCLUDE:**
- "I plan to do outreach" ✓
- "I want to network more" ✓
- "Plan to play basketball" ✓
- "Plan to jog 10km" → Quantifiable (has specific distance)
- "Plan to jog" → Non-quantifiable (no specific distance mentioned)

**Examples to EXCLUDE:**
- "John attended the meeting" ✗ (attendance info)
- "The meeting was scheduled for 3pm" ✗ (scheduling info)
- "Mary mentioned she's traveling next week" ✗ (personal circumstance, not a commitment)
- Main Room sessions ✗ (if this transcript is from a Main Room, exclude all goals)

**IMPORTANT:** This prompt should NOT be used for "Main Room" transcripts. Main Room sessions are informational and should not have goals extracted.

Transcript:
{transcript}
"""

MARKETING_ACTIVITY_EXTRACTION = """
# Extract Marketing Activities

**Task:** Find marketing activities by participant and classify them.

**Categories:**
- **Network Activation**: Outreach to existing relationships/referrals
- **LinkedIn**: New relationships or engagement on LinkedIn
- **Cold Outreach**: Contacting strangers outside LinkedIn

**Output Format:**
Name: [Participant Name]
- Network Activation: [activity, qty if mentioned]
- LinkedIn: [activity, qty if mentioned]
- Cold Outreach: [activity, qty if mentioned]

**Example:**
Name: Juliana
- Network Activation: DM'd 5 past clients on LinkedIn
- LinkedIn: Posted twice to increase visibility

Transcript:
{transcript}
"""

PIPELINE_OUTCOME_EXTRACTION = """
# Extract Pipeline Outcomes

**Task:** Find business outcomes (meetings, proposals, clients) by participant.

**Output Format:**
Name: [Participant Name]
Meetings: [#]
Proposals: [#]
Clients: [#]
Notes: [brief context]

**Example:**
Name: Chris
Meetings: 3
Proposals: 1
Clients: 0
Notes: Three discovery calls, one proposal sent

---

Transcript:
{transcript}
"""

CHALLENGE_STRATEGY_EXTRACTION = """
# Extract Challenges & Strategies

**Task:** Find participant challenges and strategies shared during the call.

**Output Format:**
Name: [Participant Name]
Challenge: [Core challenge in 1-2 sentences]
Category: [Challenge category]
Strategies/Tips:
- [Who shared it: summary + strategy type]

**Challenge Categories:**
- Clarity - Unclear goals/positioning
- Lead Generation - Not enough leads
- Sales & Conversion - Trouble converting
- Systems & Operations - Process issues
- Time & Focus - Overwhelm/priorities
- Team & Delegation - Hiring/management
- Mindset/Emotional - Fear/perfectionism
- Scaling & Offers - Growth bottlenecks
- Other - Doesn't fit above

**Strategy Types:**
- Mindset Reframe - Perspective shift
- Tactical Process - Step-by-step method
- Tool/Resource - Specific tool/template
- Connection/Referral - Intro/networking
- Framework/Model - Structure/methodology

**Example:**
Name: Juliana
Challenge: Unclear how to structure recurring CFO services offer
Category: Scaling & Offers
Strategies/Tips:
- Tanya: Create simple recurring retainer anchored on one outcome (Tactical Process)
- Kevin: Talk to 3 current clients to identify monthly service (Tactical Process)

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
# Extract Stuck Signals

**Task:** Find when participants express being stuck, stalled, or not making progress.

**Output Format:**
### [PARTICIPANT NAME]
**Stuck Summary:** [What kind of stuckness and why]
**Exact Quotes:** [1-3 revealing quotes]
**Timestamp:** (Start–End)
**Classification:** [Momentum Drop/Emotional Block/Overwhelm/Decision Paralysis/Repeating Goal/Other]
**Suggested Nudge:** [Light-touch suggestion]

**Classifications:**
- **Momentum Drop:** Lost rhythm/progress temporarily
- **Emotional Block:** Frustration, fear, perfectionism loops
- **Overwhelm:** Too many things, unclear priorities
- **Decision Paralysis:** Unsure which path to take
- **Repeating Goal:** Same goal multiple weeks without movement
- **Other:** Doesn't fit above

**Example:**
### Mack Earnhardt
**Stuck Summary:** Felt completely stuck for two weeks, can't get off "Square Zero"
**Exact Quotes:** 
- "I have felt completely stuck for the last two weeks"
- "I just can't seem to get… off of Square Zero"
**Timestamp:** (48m 45s–49m 44s)
**Classification:** Momentum Drop + Emotional Block
**Suggested Nudge:** Book momentum reset session, break into 1-2 micro-goals

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