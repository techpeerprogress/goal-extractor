-- Simple unique constraints to prevent future duplicates
-- Run this in your Supabase SQL Editor

-- Prevent duplicate transcript sessions
ALTER TABLE peer_progress.transcript_sessions 
ADD CONSTRAINT unique_transcript_session UNIQUE (filename, group_name);

-- Prevent duplicate quantifiable goals
ALTER TABLE peer_progress.quantifiable_goals 
ADD CONSTRAINT unique_quantifiable_goal UNIQUE (participant_name, goal_text, call_date);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_transcript_sessions_filename_group 
ON peer_progress.transcript_sessions(filename, group_name);

CREATE INDEX IF NOT EXISTS idx_quantifiable_goals_participant_goal_date 
ON peer_progress.quantifiable_goals(participant_name, goal_text, call_date);
