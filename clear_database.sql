-- Clear database tables for fresh run
-- Run this in your Supabase SQL Editor

-- Clear all goal-related data
DELETE FROM peer_progress.goal_progress_tracking;
DELETE FROM peer_progress.quantifiable_goals;
DELETE FROM peer_progress.vague_goals_detected;
DELETE FROM peer_progress.participant_follow_ups;

-- Clear transcript analysis data
DELETE FROM peer_progress.transcript_analysis;
DELETE FROM peer_progress.commitments;
DELETE FROM peer_progress.goal_progress;

-- Clear transcript sessions
DELETE FROM peer_progress.transcript_sessions;

-- Clear other related data
DELETE FROM peer_progress.member_attendance;
DELETE FROM peer_progress.marketing_activities;
DELETE FROM peer_progress.pipeline_outcomes;
DELETE FROM peer_progress.challenges;
DELETE FROM peer_progress.strategies;
DELETE FROM peer_progress.stuck_signals;
DELETE FROM peer_progress.help_offers;
DELETE FROM peer_progress.call_sentiment;
DELETE FROM peer_progress.participant_sentiment;
DELETE FROM peer_progress.group_health_flags;
DELETE FROM peer_progress.support_connections;

-- Reset sequences (if any)
-- Note: PostgreSQL doesn't have sequences for UUID primary keys

-- Verify tables are empty
SELECT 'transcript_sessions' as table_name, COUNT(*) as count FROM peer_progress.transcript_sessions
UNION ALL
SELECT 'quantifiable_goals', COUNT(*) FROM peer_progress.quantifiable_goals
UNION ALL
SELECT 'vague_goals_detected', COUNT(*) FROM peer_progress.vague_goals_detected
UNION ALL
SELECT 'commitments', COUNT(*) FROM peer_progress.commitments
UNION ALL
SELECT 'goal_progress_tracking', COUNT(*) FROM peer_progress.goal_progress_tracking;
