EXTRACT_COMMITMENTS = """
Find what each participant commits to doing next week.

### [Participant Name]
**What They Discussed:** [2-3 sentences]
**Commitment:** [Exact quote OR "No specific commitment made"]
**Quote:** "[Direct quote]" OR "N/A"
**Timestamp:** [Time] OR "N/A"
---

Rules: Only explicit commitments, use exact quotes, include all speakers.

Transcript:
{transcript}
"""


CLASSIFY_COMMITMENTS = """
Determine if each commitment is measurable or needs clarification.

### [Participant Name]
[Keep original sections]
**Classification:** [Quantifiable/Not Quantifiable/No Goal/Decision Pending]
**Why:** [One sentence explanation]
**Suggestion:** [How to make quantifiable] OR "N/A"
---

Rules: Quantifiable = specific numbers/deadlines, be strict when in doubt.

Extracted Commitments:
{commitments}
"""

EXTRACT_QUANTIFIABLE_GOALS = """
Find ANY commitments, plans, or goals mentioned by participants.

Look for: explicit commitments, conversational commitments, time-based goals, action items.

### [Participant Name]
**Goals with Numbers:**
[Goal 1: "Complete goal text here"]
[Goal 2: "Another goal text"]
[If none: "No specific commitments mentioned"]
---

CRITICAL: Each goal MUST be on its own line starting with [Goal X: and ending with ]

Rules: Include ANY commitment, use exact words, be very inclusive.

Transcript:
{transcript}
"""

MARKETING_ACTIVITY_EXTRACTION = """
Find marketing activities by participant and classify them.

Categories: Network Activation, LinkedIn, Cold Outreach

Name: [Participant Name]
- Network Activation: [activity, qty if mentioned]
- LinkedIn: [activity, qty if mentioned]
- Cold Outreach: [activity, qty if mentioned]

Transcript:
{transcript}
"""

PIPELINE_OUTCOME_EXTRACTION = """
Find business outcomes (meetings, proposals, clients) by participant.

Name: [Participant Name]
Meetings: [#]
Proposals: [#]
Clients: [#]
Notes: [brief context]

Transcript:
{transcript}
"""

CHALLENGE_STRATEGY_EXTRACTION = """
Find participant challenges and strategies shared during the call.

Name: [Participant Name]
Challenge: [Core challenge in 1-2 sentences]
Category: [Challenge category]
Strategies/Tips:
- [Who shared it: summary + strategy type]

Challenge Categories: Clarity, Lead Generation, Sales & Conversion, Systems & Operations, Time & Focus, Team & Delegation, Mindset/Emotional, Scaling & Offers, Other

Strategy Types: Mindset Reframe, Tactical Process, Tool/Resource, Connection/Referral, Framework/Model

Transcript:
{transcript}
"""

GENERATE_NUDGES = """
Create personalized messages for participants without quantifiable goals.

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

Rules: Only for "Not Quantifiable" or "No Goal", max 150 words, friendly tone.

Classified Commitments:
{classified_commitments}
"""

STUCK_SIGNAL_EXTRACTION = """
Find when participants express being stuck, stalled, or not making progress.

### [PARTICIPANT NAME]
**Stuck Summary:** [What kind of stuckness and why]
**Exact Quotes:** [1-3 revealing quotes]
**Timestamp:** (Start–End)
**Classification:** [Momentum Drop/Emotional Block/Overwhelm/Decision Paralysis/Repeating Goal/Other]
**Suggested Nudge:** [Light-touch suggestion]

Classifications: Momentum Drop, Emotional Block, Overwhelm, Decision Paralysis, Repeating Goal, Other

Transcript:
{transcript}
"""

HELP_OFFER_EXTRACTION = """
Find when participants offer to help, support, or provide expertise to others.

### [PARTICIPANT NAME]
**What They Offered:** [Type of help offered]
**Context:** [Why this help is relevant]
**Exact Quote:** "[Exact words used]"
**Timestamp:** (XXm XXs)
**Classification:** [Expertise/Resource/General Support/Introductions/Review & Feedback]

Classifications: Expertise, Resource, General Support, Introductions, Review & Feedback

Transcript:
{transcript}
"""

SENTIMENT_ANALYSIS = """
Analyze emotional tone to detect morale shifts and group health.

**Sentiment Score:** [1-5]
**Rationale:** [1-2 sentences explaining score]
**Dominant Emotions:** [2-4 emotional tags]
**Representative Quotes:** [1-3 quotes with names]
**Confidence Score:** [0-1]
**Negative Participants:** [List with emotions and evidence]

Scoring: 5=High Positive, 4=Positive, 3=Neutral/Mixed, 2=Negative, 1=Very Negative

Transcript:
{transcript}
"""