-- Add missing columns to quantifiable_goals table for source tracking
-- Run this in your Supabase SQL Editor

-- Add source_type column
ALTER TABLE peer_progress.quantifiable_goals 
ADD COLUMN IF NOT EXISTS source_type TEXT CHECK (source_type IN ('ai_extraction', 'human_input', 'member_update', 'qa_clarification', 'system_generated')) DEFAULT 'ai_extraction';

-- Add source_details column
ALTER TABLE peer_progress.quantifiable_goals 
ADD COLUMN IF NOT EXISTS source_details JSONB;

-- Add updated_by column
ALTER TABLE peer_progress.quantifiable_goals 
ADD COLUMN IF NOT EXISTS updated_by TEXT;

-- Add updated_at column
ALTER TABLE peer_progress.quantifiable_goals 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Also add the same columns to goal_progress_tracking table
ALTER TABLE peer_progress.goal_progress_tracking 
ADD COLUMN IF NOT EXISTS source_type TEXT CHECK (source_type IN ('ai_extraction', 'human_input', 'member_update', 'qa_clarification', 'system_generated')) DEFAULT 'ai_extraction';

ALTER TABLE peer_progress.goal_progress_tracking 
ADD COLUMN IF NOT EXISTS source_details JSONB;

ALTER TABLE peer_progress.goal_progress_tracking 
ADD COLUMN IF NOT EXISTS updated_by TEXT;

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_schema = 'peer_progress' 
AND table_name = 'quantifiable_goals' 
ORDER BY ordinal_position;

-- Add columns for marketing activity & pipeline outcomes on transcript_analysis
ALTER TABLE peer_progress.transcript_analysis
ADD COLUMN IF NOT EXISTS marketing_activities_json JSONB;

ALTER TABLE peer_progress.transcript_analysis
ADD COLUMN IF NOT EXISTS pipeline_outcomes_json JSONB;

-- Add column for stuck/frustrated signals extraction
ALTER TABLE peer_progress.transcript_analysis
ADD COLUMN IF NOT EXISTS stuck_signals_json JSONB;

-- Add column for challenges & strategies extraction
ALTER TABLE peer_progress.transcript_analysis
ADD COLUMN IF NOT EXISTS challenges_strategies_json JSONB;

-- Helpful index to avoid duplicate lookups being slow
CREATE INDEX IF NOT EXISTS idx_quant_goals_session_participant
ON peer_progress.quantifiable_goals (transcript_session_id, participant_name);

-- === MEMBERS TABLE ===
CREATE TABLE IF NOT EXISTS peer_progress.members (
    member_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    status TEXT NOT NULL, -- active, renewed, paused, dropped_requested, dropped_ghosting, not_renewed
    risk_tier TEXT, -- high, medium, on_track, crushing - computed
    group_code TEXT,
    renewal_date DATE,
    niche TEXT,
    marketing_types JSONB,
    first_client_date DATE,
    current_week_goal TEXT,
    join_date DATE DEFAULT now()
);

-- === GROUPS TABLE ===
CREATE TABLE IF NOT EXISTS peer_progress.groups (
    group_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_code TEXT UNIQUE NOT NULL,
    call_day TEXT, -- e.g., 'Wednesday', for custom week window
    call_time TIME,
    timezone TEXT
);

-- === ATTENDANCE TABLE ===
CREATE TABLE IF NOT EXISTS peer_progress.attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(member_id),
    group_id UUID REFERENCES peer_progress.groups(group_id),
    date DATE NOT NULL,
    status TEXT NOT NULL, -- present, absent, unknown, excused
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_attendance_member ON peer_progress.attendance (member_id, date);

-- === GOAL EVENTS TABLE ===
CREATE TABLE IF NOT EXISTS peer_progress.goal_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(member_id),
    group_id UUID REFERENCES peer_progress.groups(group_id),
    event_type TEXT NOT NULL, -- goal_set, goal_update, goal_completed
    goal_text TEXT,
    is_quantifiable BOOLEAN,
    ts TIMESTAMPTZ DEFAULT now(),
    source TEXT NOT NULL,
    extra JSONB
);
CREATE INDEX IF NOT EXISTS idx_goal_events_member ON peer_progress.goal_events (member_id, ts);

-- === ACTIVITY TABLE ===
CREATE TABLE IF NOT EXISTS peer_progress.activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(member_id),
    group_id UUID REFERENCES peer_progress.groups(group_id),
    subtype TEXT NOT NULL, -- meeting_booked, proposal_sent, client_closed, goal_set, goal_update, goal_completed, attendance, marketing_touch
    count INTEGER,
    channel TEXT, -- linkedin, network_activation, cold_outreach
    ts TIMESTAMPTZ DEFAULT now(),
    source TEXT, -- slack, transcript, manual
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_activity_member ON peer_progress.activity (member_id, ts);

-- === COACHING & CONTEXT TABLE ===
CREATE TABLE IF NOT EXISTS peer_progress.coaching_and_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(member_id),
    ts TIMESTAMPTZ DEFAULT now(),
    source TEXT,
    summary TEXT,
    tags JSONB,
    verbatim_quote TEXT,
    next_steps TEXT,
    link_ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_coaching_member ON peer_progress.coaching_and_context (member_id, ts);
