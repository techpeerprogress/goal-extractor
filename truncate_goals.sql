-- Truncate quantifiable_goals table
-- WARNING: This will delete ALL data in the table
-- Run this in your Supabase SQL Editor

-- First, check current count
SELECT COUNT(*) as current_goal_count FROM peer_progress.quantifiable_goals;

-- Truncate the table (removes all rows but keeps table structure)
TRUNCATE TABLE peer_progress.quantifiable_goals RESTART IDENTITY CASCADE;

-- Verify the table is empty
SELECT COUNT(*) as goal_count_after_truncate FROM peer_progress.quantifiable_goals;

-- Optional: Also truncate related tables if needed
-- TRUNCATE TABLE peer_progress.goal_progress_tracking RESTART IDENTITY CASCADE;
-- TRUNCATE TABLE peer_progress.transcript_sessions RESTART IDENTITY CASCADE;
