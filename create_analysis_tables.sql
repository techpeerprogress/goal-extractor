-- Database tables for storing transcript analysis data
-- Run this in your Supabase SQL Editor

-- Ensure extensions required
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Transcript Sessions table - stores session metadata
CREATE TABLE IF NOT EXISTS peer_progress.transcript_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    group_name TEXT,
    session_date DATE,
    raw_transcript TEXT,
    analysis_date TIMESTAMPTZ DEFAULT NOW(),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Transcript Analysis table - stores AI analysis results
CREATE TABLE IF NOT EXISTS peer_progress.transcript_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    extracted_commitments_json JSONB,
    classification_results_json JSONB,
    nudge_messages_json JSONB,
    processing_status TEXT CHECK (processing_status IN ('completed', 'failed', 'processing')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Commitments table - stores individual participant commitments
CREATE TABLE IF NOT EXISTS peer_progress.commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    participant_name TEXT NOT NULL,
    discussion_summary TEXT,
    commitment_text TEXT,
    exact_quote TEXT,
    timestamp_in_transcript TEXT,
    classification TEXT CHECK (classification IN ('quantifiable', 'not_quantifiable', 'no_goal')),
    classification_reason TEXT,
    quantification_suggestion TEXT,
    nudge_message TEXT,
    target_number INTEGER,
    goal_unit TEXT,
    week_start_date DATE,
    deadline_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Goal Progress table - tracks progress on quantifiable goals
CREATE TABLE IF NOT EXISTS peer_progress.goal_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commitment_id UUID REFERENCES peer_progress.commitments(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    member_id UUID REFERENCES peer_progress.members(id),
    progress_value INTEGER DEFAULT 0,
    target_value INTEGER NOT NULL,
    progress_percentage DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN target_value > 0 THEN (progress_value::DECIMAL / target_value::DECIMAL) * 100
            ELSE 0
        END
    ) STORED,
    progress_notes TEXT,
    progress_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Quantifiable Goals table - stores extracted quantifiable goals from transcripts
CREATE TABLE IF NOT EXISTS peer_progress.quantifiable_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    participant_name TEXT NOT NULL,
    group_name TEXT,
    call_date DATE,
    goal_text TEXT NOT NULL,
    target_number DECIMAL(10,2) NOT NULL,
    source_type TEXT CHECK (source_type IN ('ai_extraction', 'human_input', 'member_update', 'qa_clarification', 'system_generated')) DEFAULT 'ai_extraction',
    source_details JSONB,
    updated_by TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Goal Progress Tracking table - tracks progress on quantifiable goals
CREATE TABLE IF NOT EXISTS peer_progress.goal_progress_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quantifiable_goal_id UUID REFERENCES peer_progress.quantifiable_goals(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    member_id UUID REFERENCES peer_progress.members(id),
    current_value DECIMAL(10,2) DEFAULT 0,
    target_value DECIMAL(10,2) NOT NULL,
    status TEXT DEFAULT 'not_started',
    source_type TEXT CHECK (source_type IN ('ai_extraction', 'human_input', 'member_update', 'qa_clarification', 'system_generated')) DEFAULT 'ai_extraction',
    source_details JSONB,
    updated_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Grant permissions to service role
GRANT ALL ON peer_progress.transcript_sessions TO service_role;
GRANT ALL ON peer_progress.transcript_analysis TO service_role;
GRANT ALL ON peer_progress.commitments TO service_role;
GRANT ALL ON peer_progress.goal_progress TO service_role;
GRANT ALL ON peer_progress.quantifiable_goals TO service_role;
GRANT ALL ON peer_progress.goal_progress_tracking TO service_role;
GRANT ALL ON peer_progress.vague_goals_detected TO service_role;
GRANT ALL ON peer_progress.participant_follow_ups TO service_role;
GRANT ALL ON peer_progress.community_posts TO service_role;

-- 8. Enable RLS (Row Level Security)
ALTER TABLE peer_progress.transcript_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.transcript_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.goal_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.quantifiable_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.goal_progress_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.vague_goals_detected ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.participant_follow_ups ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.community_posts ENABLE ROW LEVEL SECURITY;

-- 9. Create policies to allow service role access (only if missing)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'transcript_sessions'
      AND policyname = 'Service role can do everything on transcript_sessions'
  ) THEN
    CREATE POLICY "Service role can do everything on transcript_sessions" ON peer_progress.transcript_sessions
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'transcript_analysis'
      AND policyname = 'Service role can do everything on transcript_analysis'
  ) THEN
    CREATE POLICY "Service role can do everything on transcript_analysis" ON peer_progress.transcript_analysis
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'commitments'
      AND policyname = 'Service role can do everything on commitments'
  ) THEN
    CREATE POLICY "Service role can do everything on commitments" ON peer_progress.commitments
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'goal_progress'
      AND policyname = 'Service role can do everything on goal_progress'
  ) THEN
    CREATE POLICY "Service role can do everything on goal_progress" ON peer_progress.goal_progress
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'quantifiable_goals'
      AND policyname = 'Service role can do everything on quantifiable_goals'
  ) THEN
    CREATE POLICY "Service role can do everything on quantifiable_goals" ON peer_progress.quantifiable_goals
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'goal_progress_tracking'
      AND policyname = 'Service role can do everything on goal_progress_tracking'
  ) THEN
    CREATE POLICY "Service role can do everything on goal_progress_tracking" ON peer_progress.goal_progress_tracking
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'vague_goals_detected'
      AND policyname = 'Service role can do everything on vague_goals_detected'
  ) THEN
    CREATE POLICY "Service role can do everything on vague_goals_detected" ON peer_progress.vague_goals_detected
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'participant_follow_ups'
      AND policyname = 'Service role can do everything on participant_follow_ups'
  ) THEN
    CREATE POLICY "Service role can do everything on participant_follow_ups" ON peer_progress.participant_follow_ups
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'community_posts'
      AND policyname = 'Service role can do everything on community_posts'
  ) THEN
    CREATE POLICY "Service role can do everything on community_posts" ON peer_progress.community_posts
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

-- 10. Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_transcript_sessions_organization ON peer_progress.transcript_sessions(organization_id);
CREATE INDEX IF NOT EXISTS idx_transcript_sessions_date ON peer_progress.transcript_sessions(session_date);
CREATE INDEX IF NOT EXISTS idx_transcript_sessions_group ON peer_progress.transcript_sessions(group_name);

CREATE INDEX IF NOT EXISTS idx_transcript_analysis_session ON peer_progress.transcript_analysis(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_transcript_analysis_organization ON peer_progress.transcript_analysis(organization_id);
CREATE INDEX IF NOT EXISTS idx_transcript_analysis_status ON peer_progress.transcript_analysis(processing_status);

CREATE INDEX IF NOT EXISTS idx_commitments_session ON peer_progress.commitments(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_commitments_member ON peer_progress.commitments(member_id);
CREATE INDEX IF NOT EXISTS idx_commitments_organization ON peer_progress.commitments(organization_id);
CREATE INDEX IF NOT EXISTS idx_commitments_classification ON peer_progress.commitments(classification);
CREATE INDEX IF NOT EXISTS idx_commitments_participant ON peer_progress.commitments(participant_name);

CREATE INDEX IF NOT EXISTS idx_goal_progress_commitment ON peer_progress.goal_progress(commitment_id);
CREATE INDEX IF NOT EXISTS idx_goal_progress_member ON peer_progress.goal_progress(member_id);
CREATE INDEX IF NOT EXISTS idx_goal_progress_organization ON peer_progress.goal_progress(organization_id);
CREATE INDEX IF NOT EXISTS idx_goal_progress_date ON peer_progress.goal_progress(progress_date);

CREATE INDEX IF NOT EXISTS idx_quantifiable_goals_session ON peer_progress.quantifiable_goals(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_quantifiable_goals_member ON peer_progress.quantifiable_goals(member_id);
CREATE INDEX IF NOT EXISTS idx_quantifiable_goals_organization ON peer_progress.quantifiable_goals(organization_id);
CREATE INDEX IF NOT EXISTS idx_quantifiable_goals_participant ON peer_progress.quantifiable_goals(participant_name);

CREATE INDEX IF NOT EXISTS idx_goal_progress_tracking_goal ON peer_progress.goal_progress_tracking(quantifiable_goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_progress_tracking_member ON peer_progress.goal_progress_tracking(member_id);
CREATE INDEX IF NOT EXISTS idx_goal_progress_tracking_organization ON peer_progress.goal_progress_tracking(organization_id);

-- 7. Vague Goals Detection table - tracks goals that need follow-up
CREATE TABLE IF NOT EXISTS peer_progress.vague_goals_detected (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    participant_name TEXT NOT NULL,
    original_goal_text TEXT NOT NULL,
    vagueness_reasons JSONB NOT NULL,
    suggested_quantifications JSONB,
    context_notes TEXT,
    status TEXT DEFAULT 'pending_followup',
    source_type TEXT CHECK (source_type IN ('ai_extraction', 'human_input', 'member_update', 'qa_clarification', 'system_generated')) DEFAULT 'ai_extraction',
    source_details JSONB,
    updated_by TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Participant Follow-ups table - tracks follow-up messages
CREATE TABLE IF NOT EXISTS peer_progress.participant_follow_ups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vague_goal_id UUID REFERENCES peer_progress.vague_goals_detected(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    participant_name TEXT NOT NULL,
    scheduled_date TIMESTAMPTZ NOT NULL,
    sent_date TIMESTAMPTZ,
    follow_up_status TEXT DEFAULT 'scheduled',
    nudge_message TEXT,
    response_data TEXT,
    source_type TEXT CHECK (source_type IN ('ai_extraction', 'human_input', 'member_update', 'qa_clarification', 'system_generated')) DEFAULT 'ai_extraction',
    source_details JSONB,
    updated_by TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vague_goals_session ON peer_progress.vague_goals_detected(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_vague_goals_participant ON peer_progress.vague_goals_detected(participant_name);
CREATE INDEX IF NOT EXISTS idx_vague_goals_status ON peer_progress.vague_goals_detected(status);

CREATE INDEX IF NOT EXISTS idx_follow_ups_vague_goal ON peer_progress.participant_follow_ups(vague_goal_id);
CREATE INDEX IF NOT EXISTS idx_follow_ups_participant ON peer_progress.participant_follow_ups(participant_name);
CREATE INDEX IF NOT EXISTS idx_follow_ups_status ON peer_progress.participant_follow_ups(follow_up_status);
CREATE INDEX IF NOT EXISTS idx_follow_ups_scheduled ON peer_progress.participant_follow_ups(scheduled_date);

-- 9. Community Posts table - tracks posts sent to community platforms
CREATE TABLE IF NOT EXISTS peer_progress.community_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    post_type TEXT CHECK (post_type IN ('summary', 'quantifiable_goals', 'vague_goals')),
    post_content TEXT NOT NULL,
    platform TEXT NOT NULL,
    channel TEXT,
    status TEXT CHECK (status IN ('success', 'failed', 'pending')) DEFAULT 'pending',
    group_name TEXT,
    posted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_community_posts_session ON peer_progress.community_posts(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_community_posts_organization ON peer_progress.community_posts(organization_id);
CREATE INDEX IF NOT EXISTS idx_community_posts_type ON peer_progress.community_posts(post_type);
CREATE INDEX IF NOT EXISTS idx_community_posts_platform ON peer_progress.community_posts(platform);
CREATE INDEX IF NOT EXISTS idx_community_posts_status ON peer_progress.community_posts(status);

-- 11. Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all tables
DROP TRIGGER IF EXISTS update_transcript_sessions_updated_at ON peer_progress.transcript_sessions;
CREATE TRIGGER update_transcript_sessions_updated_at
    BEFORE UPDATE ON peer_progress.transcript_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_transcript_analysis_updated_at ON peer_progress.transcript_analysis;
CREATE TRIGGER update_transcript_analysis_updated_at
    BEFORE UPDATE ON peer_progress.transcript_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_commitments_updated_at ON peer_progress.commitments;
CREATE TRIGGER update_commitments_updated_at
    BEFORE UPDATE ON peer_progress.commitments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_goal_progress_updated_at ON peer_progress.goal_progress;
CREATE TRIGGER update_goal_progress_updated_at
    BEFORE UPDATE ON peer_progress.goal_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 13. Create function to detect vague goals from commitments
CREATE OR REPLACE FUNCTION peer_progress.detect_vague_goals_from_commitment()
RETURNS TRIGGER AS $$
DECLARE
    vagueness_reasons TEXT[] := ARRAY[]::text[];
    suggestions TEXT[] := ARRAY[]::text[];
    is_vague BOOLEAN := FALSE;
BEGIN
    -- Only process if commitment is not quantifiable and has text
    IF NEW.classification = 'not_quantifiable' AND NEW.commitment_text IS NOT NULL 
       AND NEW.commitment_text != 'No specific commitment made' THEN
        
        -- Check for numbers
        IF NOT (NEW.commitment_text ~ '\d+') THEN
            vagueness_reasons := array_append(vagueness_reasons, 'no_numbers');
            is_vague := TRUE;
        END IF;
        
        -- Check for timeframes
        IF NOT (NEW.commitment_text ILIKE '%by%' OR 
                NEW.commitment_text ILIKE '%until%' OR 
                NEW.commitment_text ILIKE '%before%' OR 
                NEW.commitment_text ILIKE '%this week%' OR 
                NEW.commitment_text ILIKE '%next week%' OR 
                NEW.commitment_text ILIKE '%tomorrow%' OR 
                NEW.commitment_text ILIKE '%today%' OR 
                NEW.commitment_text ILIKE '%friday%' OR 
                NEW.commitment_text ILIKE '%monday%') THEN
            vagueness_reasons := array_append(vagueness_reasons, 'no_deadline');
            is_vague := TRUE;
        END IF;
        
        -- Check for vague words
        IF (NEW.commitment_text ILIKE '%some%' OR 
            NEW.commitment_text ILIKE '%few%' OR 
            NEW.commitment_text ILIKE '%many%' OR 
            NEW.commitment_text ILIKE '%better%' OR 
            NEW.commitment_text ILIKE '%more%' OR 
            NEW.commitment_text ILIKE '%improve%' OR 
            NEW.commitment_text ILIKE '%work on%' OR 
            NEW.commitment_text ILIKE '%try to%') THEN
            vagueness_reasons := array_append(vagueness_reasons, 'vague_language');
            is_vague := TRUE;
        END IF;
        
        -- Check if too short/broad
        IF array_length(string_to_array(NEW.commitment_text, ' '), 1) < 4 THEN
            vagueness_reasons := array_append(vagueness_reasons, 'too_broad');
            is_vague := TRUE;
        END IF;
        
        -- Generate suggestions if vague
        IF is_vague THEN
            IF NEW.commitment_text ILIKE '%post%' THEN
                suggestions := ARRAY[
                    'Post 3 times on LinkedIn this week',
                    'Write and publish 2 blog posts by Friday',
                    'Share 1 valuable insight daily for 5 days'
                ];
            ELSIF NEW.commitment_text ILIKE '%call%' THEN
                suggestions := ARRAY[
                    'Make 5 sales calls this week',
                    'Call 3 potential clients by Wednesday',
                    'Follow up with 2 prospects daily'
                ];
            ELSIF NEW.commitment_text ILIKE '%work%' OR NEW.commitment_text ILIKE '%improve%' THEN
                suggestions := ARRAY[
                    'Spend 2 hours daily on this task',
                    'Complete 3 specific improvements by Friday',
                    'Dedicate 1 hour each morning to this goal'
                ];
            ELSE
                suggestions := ARRAY[
                    'Set a specific number target (e.g., ''3'' or ''5'')',
                    'Add a deadline (e.g., ''by Friday'' or ''this week'')',
                    'Define exactly what success looks like'
                ];
            END IF;
            
            -- Insert vague goal record
            INSERT INTO peer_progress.vague_goals_detected (
                transcript_session_id,
                organization_id,
                participant_name,
                original_goal_text,
                vagueness_reasons,
                suggested_quantifications,
                context_notes,
                status,
                source_type,
                source_details,
                updated_by
            ) VALUES (
                NEW.transcript_session_id,
                NEW.organization_id,
                NEW.participant_name,
                NEW.commitment_text,
                to_jsonb(vagueness_reasons),
                to_jsonb(suggestions),
                NEW.discussion_summary,
                'pending_followup',
                'ai_extraction',
                to_jsonb('{"trigger": "commitment_insert", "algorithm": "built_in_vagueness_detection"}'),
                'system'
            );
            
            -- Schedule follow-up
            INSERT INTO peer_progress.participant_follow_ups (
                vague_goal_id,
                organization_id,
                participant_name,
                scheduled_date,
                follow_up_status,
                nudge_message,
                source_type,
                source_details,
                updated_by
            ) VALUES (
                (SELECT id FROM peer_progress.vague_goals_detected 
                 WHERE transcript_session_id = NEW.transcript_session_id 
                 AND participant_name = NEW.participant_name 
                 AND original_goal_text = NEW.commitment_text 
                 ORDER BY created_at DESC LIMIT 1),
                NEW.organization_id,
                NEW.participant_name,
                NOW() + INTERVAL '24 hours',
                'scheduled',
                format('Hi %s! 👋

I noticed your goal from our call: "%s"

To help you succeed, here are some ways to make it more specific:

• %s
• %s  
• %s

Which of these feels right for you? Let me know and I''ll hold you accountable! 💪

Best,
Your Accountability Partner', 
                NEW.participant_name,
                NEW.commitment_text,
                suggestions[1],
                suggestions[2],
                suggestions[3]
                ),
                'ai_extraction',
                to_jsonb('{"trigger": "vague_goal_detection", "auto_scheduled": true}'),
                'system'
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 14. Create trigger on commitments table
DROP TRIGGER IF EXISTS trigger_detect_vague_goals ON peer_progress.commitments;
CREATE TRIGGER trigger_detect_vague_goals
    AFTER INSERT OR UPDATE ON peer_progress.commitments
    FOR EACH ROW
    EXECUTE FUNCTION peer_progress.detect_vague_goals_from_commitment();

-- 15. Member Attendance table - tracks call attendance
CREATE TABLE IF NOT EXISTS peer_progress.member_attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    member_name TEXT NOT NULL,
    group_name TEXT,
    call_date DATE NOT NULL,
    attendance_status TEXT CHECK (attendance_status IN ('present', 'absent', 'excused')) DEFAULT 'present',
    absence_reason TEXT,
    communication_status TEXT CHECK (communication_status IN ('communicated', 'no_communication')) DEFAULT 'no_communication',
    updated_by_success_champion BOOLEAN DEFAULT false,
    success_champion_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 16. Member Risk Assessment table - tracks risk levels and triggers
CREATE TABLE IF NOT EXISTS peer_progress.member_risk_assessment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    assessment_date DATE DEFAULT CURRENT_DATE,
    risk_level TEXT CHECK (risk_level IN ('high_risk', 'medium_risk', 'on_track', 'crushing_it')) DEFAULT 'on_track',
    risk_triggers JSONB, -- Array of trigger reasons
    consecutive_missed_calls INTEGER DEFAULT 0,
    weeks_without_goals INTEGER DEFAULT 0,
    weeks_without_goal_completion INTEGER DEFAULT 0,
    weeks_without_meetings INTEGER DEFAULT 0,
    meetings_scheduled INTEGER DEFAULT 0,
    proposals_out INTEGER DEFAULT 0,
    clients_closed INTEGER DEFAULT 0,
    last_communication_date DATE,
    last_goal_update_date DATE,
    last_meeting_date DATE,
    assessment_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 17. Success Champion Actions table - tracks follow-up actions
CREATE TABLE IF NOT EXISTS peer_progress.success_champion_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    action_type TEXT CHECK (action_type IN ('attendance_followup', 'goal_followup', 'vague_goal_followup', 'intervention', 'coaching')) NOT NULL,
    trigger_reason TEXT NOT NULL,
    action_status TEXT CHECK (action_status IN ('pending', 'in_progress', 'completed', 'escalated')) DEFAULT 'pending',
    priority TEXT CHECK (priority IN ('low', 'medium', 'high', 'urgent')) DEFAULT 'medium',
    assigned_to TEXT, -- Success Champion name
    due_date DATE,
    completed_date DATE,
    action_notes TEXT,
    member_response TEXT,
    outcome TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 18. Member Goals Summary table - weekly goal tracking
CREATE TABLE IF NOT EXISTS peer_progress.member_goals_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    goals_set BOOLEAN DEFAULT false,
    goals_updated BOOLEAN DEFAULT false,
    goals_completed BOOLEAN DEFAULT false,
    meetings_scheduled INTEGER DEFAULT 0,
    proposals_out INTEGER DEFAULT 0,
    clients_closed INTEGER DEFAULT 0,
    accountability_updates INTEGER DEFAULT 0,
    summary_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(member_id, week_start_date)
);

-- Add permissions for new tables
GRANT ALL ON peer_progress.member_attendance TO service_role;
GRANT ALL ON peer_progress.member_risk_assessment TO service_role;
GRANT ALL ON peer_progress.success_champion_actions TO service_role;
GRANT ALL ON peer_progress.member_goals_summary TO service_role;

-- Enable RLS for new tables
ALTER TABLE peer_progress.member_attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.member_risk_assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.success_champion_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.member_goals_summary ENABLE ROW LEVEL SECURITY;

-- Create policies for new tables
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'member_attendance'
      AND policyname = 'Service role can do everything on member_attendance'
  ) THEN
    CREATE POLICY "Service role can do everything on member_attendance" ON peer_progress.member_attendance
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'member_risk_assessment'
      AND policyname = 'Service role can do everything on member_risk_assessment'
  ) THEN
    CREATE POLICY "Service role can do everything on member_risk_assessment" ON peer_progress.member_risk_assessment
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'success_champion_actions'
      AND policyname = 'Service role can do everything on success_champion_actions'
  ) THEN
    CREATE POLICY "Service role can do everything on success_champion_actions" ON peer_progress.success_champion_actions
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'member_goals_summary'
      AND policyname = 'Service role can do everything on member_goals_summary'
  ) THEN
    CREATE POLICY "Service role can do everything on member_goals_summary" ON peer_progress.member_goals_summary
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_member_attendance_session ON peer_progress.member_attendance(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_member_attendance_member ON peer_progress.member_attendance(member_id);
CREATE INDEX IF NOT EXISTS idx_member_attendance_date ON peer_progress.member_attendance(call_date);
CREATE INDEX IF NOT EXISTS idx_member_attendance_status ON peer_progress.member_attendance(attendance_status);

CREATE INDEX IF NOT EXISTS idx_risk_assessment_member ON peer_progress.member_risk_assessment(member_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessment_date ON peer_progress.member_risk_assessment(assessment_date);
CREATE INDEX IF NOT EXISTS idx_risk_assessment_level ON peer_progress.member_risk_assessment(risk_level);

CREATE INDEX IF NOT EXISTS idx_champion_actions_member ON peer_progress.success_champion_actions(member_id);
CREATE INDEX IF NOT EXISTS idx_champion_actions_status ON peer_progress.success_champion_actions(action_status);
CREATE INDEX IF NOT EXISTS idx_champion_actions_priority ON peer_progress.success_champion_actions(priority);
CREATE INDEX IF NOT EXISTS idx_champion_actions_due_date ON peer_progress.success_champion_actions(due_date);

CREATE INDEX IF NOT EXISTS idx_goals_summary_member ON peer_progress.member_goals_summary(member_id);
CREATE INDEX IF NOT EXISTS idx_goals_summary_week ON peer_progress.member_goals_summary(week_start_date);

-- 20. Member Change Log table - tracks all member lifecycle events
CREATE TABLE IF NOT EXISTS peer_progress.member_change_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    change_type TEXT CHECK (change_type IN ('group_assignment', 'group_change', 'renewal', 'pause', 'resume', 'status_change', 'payment_change', 'goal_update', 'attendance_update')) NOT NULL,
    change_category TEXT CHECK (change_category IN ('membership', 'billing', 'engagement', 'goals', 'attendance')) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    change_description TEXT NOT NULL,
    change_reason TEXT,
    changed_by TEXT, -- User who made the change (Success Champion, Admin, System)
    change_source TEXT CHECK (change_source IN ('manual', 'automatic', 'system', 'api')) DEFAULT 'manual',
    effective_date DATE DEFAULT CURRENT_DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 21. Member Status History table - tracks member status changes over time
CREATE TABLE IF NOT EXISTS peer_progress.member_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    status_type TEXT CHECK (status_type IN ('membership_status', 'group_assignment', 'subscription_status', 'payment_status', 'engagement_status')) NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    effective_date DATE NOT NULL,
    expiration_date DATE,
    changed_by TEXT,
    change_reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 22. Member Renewals table - tracks subscription renewals and billing
CREATE TABLE IF NOT EXISTS peer_progress.member_renewals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    renewal_type TEXT CHECK (renewal_type IN ('monthly', 'quarterly', 'annual', 'lifetime')) NOT NULL,
    renewal_date DATE NOT NULL,
    expiration_date DATE NOT NULL,
    amount DECIMAL(10,2),
    currency TEXT DEFAULT 'USD',
    payment_status TEXT CHECK (payment_status IN ('paid', 'pending', 'failed', 'refunded')) DEFAULT 'pending',
    payment_method TEXT,
    invoice_number TEXT,
    notes TEXT,
    processed_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 23. Member Pauses table - tracks pause/resume periods
CREATE TABLE IF NOT EXISTS peer_progress.member_pauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    pause_type TEXT CHECK (pause_type IN ('temporary', 'medical', 'financial', 'personal', 'administrative')) NOT NULL,
    pause_start_date DATE NOT NULL,
    pause_end_date DATE,
    pause_reason TEXT NOT NULL,
    pause_status TEXT CHECK (pause_status IN ('active', 'completed', 'extended', 'cancelled')) DEFAULT 'active',
    resumed_date DATE,
    notes TEXT,
    requested_by TEXT,
    approved_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add permissions for new tables
GRANT ALL ON peer_progress.member_change_log TO service_role;
GRANT ALL ON peer_progress.member_status_history TO service_role;
GRANT ALL ON peer_progress.member_renewals TO service_role;
GRANT ALL ON peer_progress.member_pauses TO service_role;

-- Enable RLS for new tables
ALTER TABLE peer_progress.member_change_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.member_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.member_renewals ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.member_pauses ENABLE ROW LEVEL SECURITY;

-- Create policies for new tables
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'member_change_log'
      AND policyname = 'Service role can do everything on member_change_log'
  ) THEN
    CREATE POLICY "Service role can do everything on member_change_log" ON peer_progress.member_change_log
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'member_status_history'
      AND policyname = 'Service role can do everything on member_status_history'
  ) THEN
    CREATE POLICY "Service role can do everything on member_status_history" ON peer_progress.member_status_history
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'member_renewals'
      AND policyname = 'Service role can do everything on member_renewals'
  ) THEN
    CREATE POLICY "Service role can do everything on member_renewals" ON peer_progress.member_renewals
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'member_pauses'
      AND policyname = 'Service role can do everything on member_pauses'
  ) THEN
    CREATE POLICY "Service role can do everything on member_pauses" ON peer_progress.member_pauses
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_member_change_log_member ON peer_progress.member_change_log(member_id);
CREATE INDEX IF NOT EXISTS idx_member_change_log_type ON peer_progress.member_change_log(change_type);
CREATE INDEX IF NOT EXISTS idx_member_change_log_category ON peer_progress.member_change_log(change_category);
CREATE INDEX IF NOT EXISTS idx_member_change_log_date ON peer_progress.member_change_log(effective_date);
CREATE INDEX IF NOT EXISTS idx_member_change_log_created ON peer_progress.member_change_log(created_at);

CREATE INDEX IF NOT EXISTS idx_member_status_history_member ON peer_progress.member_status_history(member_id);
CREATE INDEX IF NOT EXISTS idx_member_status_history_type ON peer_progress.member_status_history(status_type);
CREATE INDEX IF NOT EXISTS idx_member_status_history_effective ON peer_progress.member_status_history(effective_date);

CREATE INDEX IF NOT EXISTS idx_member_renewals_member ON peer_progress.member_renewals(member_id);
CREATE INDEX IF NOT EXISTS idx_member_renewals_date ON peer_progress.member_renewals(renewal_date);
CREATE INDEX IF NOT EXISTS idx_member_renewals_expiration ON peer_progress.member_renewals(expiration_date);
CREATE INDEX IF NOT EXISTS idx_member_renewals_status ON peer_progress.member_renewals(payment_status);

CREATE INDEX IF NOT EXISTS idx_member_pauses_member ON peer_progress.member_pauses(member_id);
CREATE INDEX IF NOT EXISTS idx_member_pauses_status ON peer_progress.member_pauses(pause_status);
CREATE INDEX IF NOT EXISTS idx_member_pauses_start ON peer_progress.member_pauses(pause_start_date);
CREATE INDEX IF NOT EXISTS idx_member_pauses_end ON peer_progress.member_pauses(pause_end_date);

-- 25. Marketing Activity Extraction table - tracks marketing activities by category
CREATE TABLE IF NOT EXISTS peer_progress.marketing_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    participant_name TEXT NOT NULL,
    group_name TEXT,
    session_date DATE NOT NULL,
    activity_category TEXT CHECK (activity_category IN ('network_activation', 'linkedin', 'cold_outreach')) NOT NULL,
    activity_description TEXT NOT NULL,
    quantity INTEGER,
    quantity_unit TEXT,
    activity_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 26. Pipeline Outcomes table - tracks meetings, proposals, and client wins
CREATE TABLE IF NOT EXISTS peer_progress.pipeline_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    participant_name TEXT NOT NULL,
    group_name TEXT,
    session_date DATE NOT NULL,
    meetings_count INTEGER DEFAULT 0,
    proposals_count INTEGER DEFAULT 0,
    clients_count INTEGER DEFAULT 0,
    outcome_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 27. Marketing Activity Summary table - weekly aggregated view
CREATE TABLE IF NOT EXISTS peer_progress.marketing_activity_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    network_activation_activities INTEGER DEFAULT 0,
    linkedin_activities INTEGER DEFAULT 0,
    cold_outreach_activities INTEGER DEFAULT 0,
    total_meetings INTEGER DEFAULT 0,
    total_proposals INTEGER DEFAULT 0,
    total_clients INTEGER DEFAULT 0,
    activity_effectiveness_score DECIMAL(5,2), -- meetings per activity ratio
    summary_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(member_id, week_start_date)
);

-- Add permissions for new tables
GRANT ALL ON peer_progress.marketing_activities TO service_role;
GRANT ALL ON peer_progress.pipeline_outcomes TO service_role;
GRANT ALL ON peer_progress.marketing_activity_summary TO service_role;

-- Enable RLS for new tables
ALTER TABLE peer_progress.marketing_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.pipeline_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.marketing_activity_summary ENABLE ROW LEVEL SECURITY;

-- Create policies for new tables
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'marketing_activities'
      AND policyname = 'Service role can do everything on marketing_activities'
  ) THEN
    CREATE POLICY "Service role can do everything on marketing_activities" ON peer_progress.marketing_activities
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'pipeline_outcomes'
      AND policyname = 'Service role can do everything on pipeline_outcomes'
  ) THEN
    CREATE POLICY "Service role can do everything on pipeline_outcomes" ON peer_progress.pipeline_outcomes
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'marketing_activity_summary'
      AND policyname = 'Service role can do everything on marketing_activity_summary'
  ) THEN
    CREATE POLICY "Service role can do everything on marketing_activity_summary" ON peer_progress.marketing_activity_summary
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_marketing_activities_session ON peer_progress.marketing_activities(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_marketing_activities_member ON peer_progress.marketing_activities(member_id);
CREATE INDEX IF NOT EXISTS idx_marketing_activities_category ON peer_progress.marketing_activities(activity_category);
CREATE INDEX IF NOT EXISTS idx_marketing_activities_date ON peer_progress.marketing_activities(session_date);

CREATE INDEX IF NOT EXISTS idx_pipeline_outcomes_session ON peer_progress.pipeline_outcomes(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_outcomes_member ON peer_progress.pipeline_outcomes(member_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_outcomes_date ON peer_progress.pipeline_outcomes(session_date);

CREATE INDEX IF NOT EXISTS idx_marketing_summary_member ON peer_progress.marketing_activity_summary(member_id);
CREATE INDEX IF NOT EXISTS idx_marketing_summary_week ON peer_progress.marketing_activity_summary(week_start_date);

-- 29. Challenge & Strategy Extraction tables - tracks challenges and solutions shared
CREATE TABLE IF NOT EXISTS peer_progress.challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    participant_name TEXT NOT NULL,
    group_name TEXT,
    session_date DATE NOT NULL,
    challenge_description TEXT NOT NULL,
    challenge_category TEXT NOT NULL,
    is_explicit_challenge BOOLEAN DEFAULT true,
    challenge_context TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 30. Strategies table - tracks tips and solutions shared
CREATE TABLE IF NOT EXISTS peer_progress.strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    strategy_description TEXT NOT NULL,
    strategy_type TEXT CHECK (strategy_type IN ('mindset_reframe', 'tactical_process', 'tool_resource', 'connection_referral', 'framework_model')) NOT NULL,
    shared_by TEXT NOT NULL,
    target_participant TEXT,
    challenge_id UUID REFERENCES peer_progress.challenges(id) ON DELETE CASCADE,
    is_general_advice BOOLEAN DEFAULT false,
    strategy_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 31. Challenge Categories table - tracks challenge types and frequencies
CREATE TABLE IF NOT EXISTS peer_progress.challenge_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    category_name TEXT NOT NULL,
    category_description TEXT,
    emoji TEXT,
    is_custom_category BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, category_name)
);

-- 32. Strategy Types table - tracks strategy types and effectiveness
CREATE TABLE IF NOT EXISTS peer_progress.strategy_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    type_name TEXT NOT NULL,
    type_description TEXT,
    emoji TEXT,
    usage_count INTEGER DEFAULT 0,
    effectiveness_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, type_name)
);

-- Add permissions for new tables
GRANT ALL ON peer_progress.challenges TO service_role;
GRANT ALL ON peer_progress.strategies TO service_role;
GRANT ALL ON peer_progress.challenge_categories TO service_role;
GRANT ALL ON peer_progress.strategy_types TO service_role;

-- Enable RLS for new tables
ALTER TABLE peer_progress.challenges ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.challenge_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.strategy_types ENABLE ROW LEVEL SECURITY;

-- Create policies for new tables
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'challenges'
      AND policyname = 'Service role can do everything on challenges'
  ) THEN
    CREATE POLICY "Service role can do everything on challenges" ON peer_progress.challenges
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'strategies'
      AND policyname = 'Service role can do everything on strategies'
  ) THEN
    CREATE POLICY "Service role can do everything on strategies" ON peer_progress.strategies
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'challenge_categories'
      AND policyname = 'Service role can do everything on challenge_categories'
  ) THEN
    CREATE POLICY "Service role can do everything on challenge_categories" ON peer_progress.challenge_categories
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'strategy_types'
      AND policyname = 'Service role can do everything on strategy_types'
  ) THEN
    CREATE POLICY "Service role can do everything on strategy_types" ON peer_progress.strategy_types
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_challenges_session ON peer_progress.challenges(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_challenges_member ON peer_progress.challenges(member_id);
CREATE INDEX IF NOT EXISTS idx_challenges_category ON peer_progress.challenges(challenge_category);
CREATE INDEX IF NOT EXISTS idx_challenges_date ON peer_progress.challenges(session_date);

CREATE INDEX IF NOT EXISTS idx_strategies_session ON peer_progress.strategies(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_strategies_type ON peer_progress.strategies(strategy_type);
CREATE INDEX IF NOT EXISTS idx_strategies_shared_by ON peer_progress.strategies(shared_by);
CREATE INDEX IF NOT EXISTS idx_strategies_challenge ON peer_progress.strategies(challenge_id);

CREATE INDEX IF NOT EXISTS idx_challenge_categories_org ON peer_progress.challenge_categories(organization_id);
CREATE INDEX IF NOT EXISTS idx_challenge_categories_usage ON peer_progress.challenge_categories(usage_count);

CREATE INDEX IF NOT EXISTS idx_strategy_types_org ON peer_progress.strategy_types(organization_id);
CREATE INDEX IF NOT EXISTS idx_strategy_types_usage ON peer_progress.strategy_types(usage_count);

-- Insert default challenge categories
INSERT INTO peer_progress.challenge_categories (organization_id, category_name, category_description, emoji, is_custom_category) VALUES
(NULL, 'Clarity', 'Unclear goals, positioning, or priorities', '🧭', false),
(NULL, 'Lead Generation', 'Not enough qualified leads, inconsistent pipeline', '📈', false),
(NULL, 'Sales & Conversion', 'Trouble converting leads, pricing issues, follow-up gaps', '💬', false),
(NULL, 'Systems & Operations', 'Lacking processes, delegation gaps, tool confusion', '🧰', false),
(NULL, 'Time & Focus', 'Overwhelm, poor prioritization, no protected strategy time', '⏰', false),
(NULL, 'Team & Delegation', 'Hiring, training, or management issues', '👥', false),
(NULL, 'Mindset / Emotional', 'Fear, perfectionism, overthinking, burnout', '🧠', false),
(NULL, 'Scaling & Offers', 'Bottlenecks moving from solo to leveraged model, unclear scalable offer', '🪜', false),
(NULL, 'Other', 'Use when it doesn''t fit anywhere else', '🌀', false)
ON CONFLICT DO NOTHING;

-- Insert default strategy types
INSERT INTO peer_progress.strategy_types (organization_id, type_name, type_description, emoji) VALUES
(NULL, 'mindset_reframe', 'A perspective or belief shift', '🧠'),
(NULL, 'tactical_process', 'A step-by-step action or method', '📝'),
(NULL, 'tool_resource', 'A specific tool, template, or resource', '🧰'),
(NULL, 'connection_referral', 'An intro, referral, or networking suggestion', '🔗'),
(NULL, 'framework_model', 'A structure, model, or named methodology', '🧭')
ON CONFLICT DO NOTHING;

-- 34. Stuck/Frustrated/Supported System Tables
-- Stuck signals tracking
CREATE TABLE IF NOT EXISTS peer_progress.stuck_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    participant_name TEXT NOT NULL,
    group_name TEXT,
    session_date DATE NOT NULL,
    stuck_summary TEXT NOT NULL,
    stuck_classification TEXT CHECK (stuck_classification IN ('momentum_drop', 'emotional_block', 'overwhelm', 'decision_paralysis', 'repeating_goal', 'other')) NOT NULL,
    exact_quotes TEXT[] NOT NULL,
    timestamp_start TEXT,
    timestamp_end TEXT,
    suggested_nudge TEXT,
    severity_score INTEGER CHECK (severity_score BETWEEN 1 AND 5) DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Help offers tracking
CREATE TABLE IF NOT EXISTS peer_progress.help_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    offerer_name TEXT NOT NULL,
    group_name TEXT,
    session_date DATE NOT NULL,
    help_description TEXT NOT NULL,
    help_context TEXT,
    exact_quote TEXT NOT NULL,
    timestamp TEXT,
    classification TEXT CHECK (classification IN ('expertise', 'resource', 'general_support', 'introductions', 'review_feedback')) NOT NULL,
    target_participant TEXT,
    domain_expertise TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Call sentiment and group health tracking
CREATE TABLE IF NOT EXISTS peer_progress.call_sentiment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    group_name TEXT,
    session_date DATE NOT NULL,
    sentiment_score DECIMAL(2,1) CHECK (sentiment_score BETWEEN 1.0 AND 5.0) NOT NULL,
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0.0 AND 1.0) NOT NULL,
    rationale TEXT NOT NULL,
    dominant_emotions TEXT[] NOT NULL,
    representative_quotes TEXT[] NOT NULL,
    negative_participant_count INTEGER DEFAULT 0,
    tense_exchange_count INTEGER DEFAULT 0,
    laughter_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Participant sentiment tracking
CREATE TABLE IF NOT EXISTS peer_progress.participant_sentiment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    member_id UUID REFERENCES peer_progress.members(id),
    organization_id UUID REFERENCES peer_progress.organizations(id),
    participant_name TEXT NOT NULL,
    group_name TEXT,
    session_date DATE NOT NULL,
    negativity_score DECIMAL(3,2) CHECK (negativity_score BETWEEN 0.0 AND 1.0) DEFAULT 0.0,
    positivity_score DECIMAL(3,2) CHECK (positivity_score BETWEEN 0.0 AND 1.0) DEFAULT 0.0,
    emotion_tags TEXT[] DEFAULT '{}',
    evidence_quotes TEXT[] DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(transcript_session_id, participant_name)
);

-- Group health flags and alerts
CREATE TABLE IF NOT EXISTS peer_progress.group_health_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    group_name TEXT,
    session_date DATE NOT NULL,
    flag_level TEXT CHECK (flag_level IN ('info', 'warning', 'critical')) NOT NULL,
    flag_reason TEXT NOT NULL,
    flag_category TEXT CHECK (flag_category IN ('low_sentiment', 'multiple_negatives', 'tense_exchanges', 'sentiment_drop', 'stuck_signals', 'conflict_detected')) NOT NULL,
    triggered_by TEXT,
    status TEXT CHECK (status IN ('open', 'acknowledged', 'resolved')) DEFAULT 'open',
    acknowledged_by UUID,
    acknowledged_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Support connections (who helped whom)
CREATE TABLE IF NOT EXISTS peer_progress.support_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_session_id UUID REFERENCES peer_progress.transcript_sessions(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES peer_progress.organizations(id),
    group_name TEXT,
    session_date DATE NOT NULL,
    supporter_name TEXT NOT NULL,
    supported_participant TEXT,
    support_type TEXT CHECK (support_type IN ('help_offer', 'strategy_shared', 'encouragement', 'resource_provided', 'introduction_made')) NOT NULL,
    support_description TEXT NOT NULL,
    follow_up_needed BOOLEAN DEFAULT false,
    follow_up_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add permissions for new tables
GRANT ALL ON peer_progress.stuck_signals TO service_role;
GRANT ALL ON peer_progress.help_offers TO service_role;
GRANT ALL ON peer_progress.call_sentiment TO service_role;
GRANT ALL ON peer_progress.participant_sentiment TO service_role;
GRANT ALL ON peer_progress.group_health_flags TO service_role;
GRANT ALL ON peer_progress.support_connections TO service_role;

-- Enable RLS for new tables
ALTER TABLE peer_progress.stuck_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.help_offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.call_sentiment ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.participant_sentiment ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.group_health_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_progress.support_connections ENABLE ROW LEVEL SECURITY;

-- Create policies for new tables
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'stuck_signals'
      AND policyname = 'Service role can do everything on stuck_signals'
  ) THEN
    CREATE POLICY "Service role can do everything on stuck_signals" ON peer_progress.stuck_signals
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'help_offers'
      AND policyname = 'Service role can do everything on help_offers'
  ) THEN
    CREATE POLICY "Service role can do everything on help_offers" ON peer_progress.help_offers
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'call_sentiment'
      AND policyname = 'Service role can do everything on call_sentiment'
  ) THEN
    CREATE POLICY "Service role can do everything on call_sentiment" ON peer_progress.call_sentiment
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'participant_sentiment'
      AND policyname = 'Service role can do everything on participant_sentiment'
  ) THEN
    CREATE POLICY "Service role can do everything on participant_sentiment" ON peer_progress.participant_sentiment
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'group_health_flags'
      AND policyname = 'Service role can do everything on group_health_flags'
  ) THEN
    CREATE POLICY "Service role can do everything on group_health_flags" ON peer_progress.group_health_flags
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'peer_progress'
      AND tablename = 'support_connections'
      AND policyname = 'Service role can do everything on support_connections'
  ) THEN
    CREATE POLICY "Service role can do everything on support_connections" ON peer_progress.support_connections
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END$$;

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_stuck_signals_session ON peer_progress.stuck_signals(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_stuck_signals_member ON peer_progress.stuck_signals(member_id);
CREATE INDEX IF NOT EXISTS idx_stuck_signals_classification ON peer_progress.stuck_signals(stuck_classification);
CREATE INDEX IF NOT EXISTS idx_stuck_signals_date ON peer_progress.stuck_signals(session_date);

CREATE INDEX IF NOT EXISTS idx_help_offers_session ON peer_progress.help_offers(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_help_offers_classification ON peer_progress.help_offers(classification);
CREATE INDEX IF NOT EXISTS idx_help_offers_offerer ON peer_progress.help_offers(offerer_name);

CREATE INDEX IF NOT EXISTS idx_call_sentiment_session ON peer_progress.call_sentiment(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_call_sentiment_score ON peer_progress.call_sentiment(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_call_sentiment_date ON peer_progress.call_sentiment(session_date);

CREATE INDEX IF NOT EXISTS idx_participant_sentiment_session ON peer_progress.participant_sentiment(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_participant_sentiment_member ON peer_progress.participant_sentiment(member_id);
CREATE INDEX IF NOT EXISTS idx_participant_sentiment_negativity ON peer_progress.participant_sentiment(negativity_score);

CREATE INDEX IF NOT EXISTS idx_group_health_flags_session ON peer_progress.group_health_flags(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_group_health_flags_level ON peer_progress.group_health_flags(flag_level);
CREATE INDEX IF NOT EXISTS idx_group_health_flags_status ON peer_progress.group_health_flags(status);
CREATE INDEX IF NOT EXISTS idx_group_health_flags_date ON peer_progress.group_health_flags(session_date);

CREATE INDEX IF NOT EXISTS idx_support_connections_session ON peer_progress.support_connections(transcript_session_id);
CREATE INDEX IF NOT EXISTS idx_support_connections_supporter ON peer_progress.support_connections(supporter_name);
CREATE INDEX IF NOT EXISTS idx_support_connections_supported ON peer_progress.support_connections(supported_participant);

-- Auto-flagging trigger for group health
CREATE OR REPLACE FUNCTION peer_progress.create_group_health_flags()
RETURNS TRIGGER AS $$
DECLARE
    v_group_id UUID;
    v_avg_sentiment DECIMAL(2,1);
    v_negative_count INTEGER;
    v_tense_count INTEGER;
BEGIN
    -- Get group info
    SELECT ts.group_name INTO v_group_id
    FROM peer_progress.transcript_sessions ts
    WHERE ts.id = NEW.transcript_session_id;
    
    -- Rule 1: Low overall sentiment
    IF NEW.sentiment_score <= 2.0 THEN
        INSERT INTO peer_progress.group_health_flags (
            transcript_session_id, organization_id, group_name, session_date,
            flag_level, flag_reason, flag_category, triggered_by
        ) VALUES (
            NEW.transcript_session_id, NEW.organization_id, NEW.group_name, NEW.session_date,
            'critical', 'Overall sentiment very negative (≤2.0)', 'low_sentiment', 'sentiment_analysis'
        );
    ELSIF NEW.sentiment_score <= 3.0 THEN
        INSERT INTO peer_progress.group_health_flags (
            transcript_session_id, organization_id, group_name, session_date,
            flag_level, flag_reason, flag_category, triggered_by
        ) VALUES (
            NEW.transcript_session_id, NEW.organization_id, NEW.group_name, NEW.session_date,
            'warning', 'Overall sentiment low (≤3.0)', 'low_sentiment', 'sentiment_analysis'
        );
    END IF;
    
    -- Rule 2: Multiple negative participants
    IF NEW.negative_participant_count >= 2 THEN
        INSERT INTO peer_progress.group_health_flags (
            transcript_session_id, organization_id, group_name, session_date,
            flag_level, flag_reason, flag_category, triggered_by
        ) VALUES (
            NEW.transcript_session_id, NEW.organization_id, NEW.group_name, NEW.session_date,
            'warning', format('Multiple participants expressed negative emotions (%s)', NEW.negative_participant_count), 
            'multiple_negatives', 'sentiment_analysis'
        );
    END IF;
    
    -- Rule 3: Tense exchanges
    IF NEW.tense_exchange_count >= 2 THEN
        INSERT INTO peer_progress.group_health_flags (
            transcript_session_id, organization_id, group_name, session_date,
            flag_level, flag_reason, flag_category, triggered_by
        ) VALUES (
            NEW.transcript_session_id, NEW.organization_id, NEW.group_name, NEW.session_date,
            'critical', format('Repeated tense exchanges detected (%s)', NEW.tense_exchange_count), 
            'tense_exchanges', 'sentiment_analysis'
        );
    END IF;
    
    -- Rule 4: Sentiment drop vs last 3 calls (simplified)
    SELECT AVG(sentiment_score) INTO v_avg_sentiment
    FROM peer_progress.call_sentiment cs
    JOIN peer_progress.transcript_sessions ts ON ts.id = cs.transcript_session_id
    WHERE ts.group_name = NEW.group_name 
    AND cs.session_date < NEW.session_date
    ORDER BY cs.session_date DESC
    LIMIT 3;
    
    IF v_avg_sentiment IS NOT NULL AND NEW.sentiment_score <= v_avg_sentiment - 1.0 THEN
        INSERT INTO peer_progress.group_health_flags (
            transcript_session_id, organization_id, group_name, session_date,
            flag_level, flag_reason, flag_category, triggered_by
        ) VALUES (
            NEW.transcript_session_id, NEW.organization_id, NEW.group_name, NEW.session_date,
            'warning', format('Sentiment dropped by ≥1.0 vs last calls (now %.1f, was %.1f)', NEW.sentiment_score, v_avg_sentiment), 
            'sentiment_drop', 'sentiment_analysis'
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for auto-flagging
CREATE TRIGGER trigger_create_group_health_flags
    AFTER INSERT ON peer_progress.call_sentiment
    FOR EACH ROW EXECUTE FUNCTION peer_progress.create_group_health_flags();

-- 35. Verify tables were created
SELECT table_name, table_schema 
FROM information_schema.tables 
WHERE table_schema = 'peer_progress' 
AND table_name IN ('transcript_sessions', 'transcript_analysis', 'commitments', 'goal_progress', 'quantifiable_goals', 'goal_progress_tracking', 'vague_goals_detected', 'participant_follow_ups', 'community_posts', 'member_attendance', 'member_risk_assessment', 'success_champion_actions', 'member_goals_summary', 'member_change_log', 'member_status_history', 'member_renewals', 'member_pauses', 'marketing_activities', 'pipeline_outcomes', 'marketing_activity_summary', 'challenges', 'strategies', 'challenge_categories', 'strategy_types', 'stuck_signals', 'help_offers', 'call_sentiment', 'participant_sentiment', 'group_health_flags', 'support_connections')
ORDER BY table_name;