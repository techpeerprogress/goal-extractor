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
