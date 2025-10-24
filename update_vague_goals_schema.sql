-- Add missing columns to vague_goals_detected table for source tracking
-- Run this in your Supabase SQL Editor

-- Add source_type column
ALTER TABLE peer_progress.vague_goals_detected 
ADD COLUMN IF NOT EXISTS source_type TEXT CHECK (source_type IN ('ai_extraction', 'human_input', 'member_update', 'qa_clarification', 'system_generated')) DEFAULT 'ai_extraction';

-- Add source_details column
ALTER TABLE peer_progress.vague_goals_detected 
ADD COLUMN IF NOT EXISTS source_details JSONB;

-- Add updated_by column
ALTER TABLE peer_progress.vague_goals_detected 
ADD COLUMN IF NOT EXISTS updated_by TEXT;

-- Add updated_at column
ALTER TABLE peer_progress.vague_goals_detected 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_schema = 'peer_progress' 
AND table_name = 'vague_goals_detected' 
ORDER BY ordinal_position;
