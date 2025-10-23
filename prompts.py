EXTRACT_COMMITMENTS = """
Task: Extract goal commitments from a mastermind call transcript

Input: Transcript of a mastermind call with multiple participants

Process:
For each participant who speaks, identify:
1. Their full name
2. Summary of what they discussed (max 100 words)
3. Their exact commitment for next week (direct quote)
4. Timestamp of the commitment (if available)

Output format:
### [Participant Name]

**What They Discussed:**
[Summary in 2-3 sentences, max 100 words]

**Their Commitment for Next Week:**
[Exact quote OR "No specific commitment made"]

**Exact Quote:**
"[Direct quote from transcript]" OR "N/A"

**Timestamp:**
[Time in transcript] OR "N/A"

---

Constraints:
- Only extract explicit commitments (not implied or suggested)
- Use exact quotes from the transcript
- If no commitment is made, state "No specific commitment made"
- Include all participants who speak
- Separate each participant with "---"

Verify: Each participant has all 4 fields filled

Transcript:
{transcript}
"""


CLASSIFY_COMMITMENTS = """
Task: Classify goal commitments by quantifiability

Input: List of participant commitments extracted from a transcript

Classification Rules:
- **Quantifiable**: Has a specific number OR verifiable completion point OR clear deadline
- **Not Quantifiable**: Vague goal without measurable criteria
- **No Goal**: No commitment was made
- **Decision Pending**: Waiting on external factors

Process:
For each participant commitment, add:
1. Classification (one of the 4 types above)
2. Reason for classification (one sentence)
3. How to make it quantifiable (only if "Not Quantifiable")

Output format:
### [Participant Name]

[Keep original "What They Discussed" and "Commitment" sections]

**Classification:**
[Quantifiable/Not Quantifiable/No Goal/Decision Pending]

**Why This Classification:**
[One clear sentence explaining the classification]

**How to Make It Quantifiable:**
[Specific suggestion with numbers/deadlines] OR "N/A"

---

Constraints:
- Only one classification per person
- "Quantifiable" must have measurable criteria
- Suggestions must include specific numbers or deadlines
- Keep original content intact
- Be strict: when in doubt, classify as "Not Quantifiable"

Verify: Each participant has classification and reason

Extracted Commitments:
{commitments}
"""

EXTRACT_QUANTIFIABLE_GOALS = """
Task: Extract ONLY quantifiable business/professional goals from mastermind call transcript

Input: Transcript of a mastermind call with multiple participants

Process:
For each participant, identify ONLY goals that meet these criteria:
1. **Business/Professional Focus**: Related to business growth, client acquisition, revenue, marketing, etc.
2. **Quantifiable**: Has specific numbers, deadlines, or measurable outcomes
3. **Actionable**: Something they will DO, not just discuss or consider
4. **Future-Oriented**: A commitment for next week/month, not past accomplishments

EXCLUDE:
- Personal life circumstances (childcare, travel, family issues)
- General discussions or updates
- Past accomplishments or current status
- Vague statements without specific numbers/deadlines
- Attendance or scheduling information

Output format:
### [Participant Name]
**Quantifiable Goals:**
[Goal 1: "Specific goal with numbers/deadlines"]
[Goal 2: "Another specific goal with measurable outcome"]
[If none: "No quantifiable goals mentioned"]
---

CRITICAL: Each goal MUST be on its own line starting with [Goal X: and ending with ]

Constraints:
- ONLY extract business/professional goals
- MUST have specific numbers, deadlines, or measurable outcomes
- EXCLUDE personal life circumstances and attendance information
- EXCLUDE vague statements without clear metrics
- Be selective: when in doubt, exclude it

Verify: Each goal has specific numbers/deadlines and is business-focused

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
Task: Create personalized accountability nudge messages

Input: Classified goal commitments from a mastermind call

Process:
For each participant with "Not Quantifiable" or "No Goal" classification:
1. Acknowledge something positive from their discussion
2. Point out the missing quantifiable goal
3. Suggest 3 specific alternative goals with numbers/deadlines
4. Ask if they want accountability

Output format:
### [Participant Name]

[Keep all previous sections]

**Personalized Accountability Nudge Message:**

> @[Name] [Acknowledgment of their work/discussion]
> 
> I noticed you didn't set a **quantifiable goal** during the call. [Empathetic context]
> 
> Here are a few options you could lock in:
> 
> • [Emoji] [Specific goal with number/deadline]
> 
> • [Emoji] [Specific goal with number/deadline]
> 
> • [Emoji] [Specific goal with number/deadline]
> 
> Do you want me to hold you accountable to one of these for next week's check-in?

---

Constraints:
- Only create messages for "Not Quantifiable" or "No Goal"
- For "Quantifiable" goals, set field to "N/A"
- Max 150 words per message
- Friendly, encouraging tone
- Each suggestion must have specific numbers or deadlines
- Use relevant emojis (✍️, 📞, 🧭, 📝, etc.)

Verify: Messages only for non-quantifiable goals, "N/A" for quantifiable goals

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