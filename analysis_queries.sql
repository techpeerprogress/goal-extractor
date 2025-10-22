-- Useful queries for retrieving transcript analysis data
-- Run these in your Supabase SQL Editor after creating the tables

-- 1. Get all transcript sessions with participant counts
SELECT 
    ts.filename,
    ts.group_name,
    ts.session_date,
    ts.analysis_date,
    COUNT(c.id) as participant_count,
    COUNT(CASE WHEN c.classification = 'quantifiable' THEN 1 END) as quantifiable_count,
    COUNT(CASE WHEN c.classification = 'not_quantifiable' THEN 1 END) as not_quantifiable_count,
    COUNT(CASE WHEN c.classification = 'no_goal' THEN 1 END) as no_goal_count
FROM peer_progress.transcript_sessions ts
LEFT JOIN peer_progress.commitments c ON ts.id = c.transcript_session_id
GROUP BY ts.id, ts.filename, ts.group_name, ts.session_date, ts.analysis_date
ORDER BY ts.session_date DESC;

-- 2. Get all quantifiable commitments with progress
SELECT 
    ts.filename,
    ts.group_name,
    c.participant_name,
    c.commitment_text,
    c.target_number,
    c.goal_unit,
    c.deadline_date,
    gp.progress_value,
    gp.target_value,
    gp.progress_percentage,
    gp.progress_notes
FROM peer_progress.transcript_sessions ts
JOIN peer_progress.commitments c ON ts.id = c.transcript_session_id
LEFT JOIN peer_progress.goal_progress gp ON c.id = gp.commitment_id
WHERE c.classification = 'quantifiable'
ORDER BY ts.session_date DESC, c.participant_name;

-- 3. Get all nudge messages for non-quantifiable goals
SELECT 
    ts.filename,
    ts.group_name,
    c.participant_name,
    c.commitment_text,
    c.nudge_message,
    c.classification_reason,
    c.quantification_suggestion
FROM peer_progress.transcript_sessions ts
JOIN peer_progress.commitments c ON ts.id = c.transcript_session_id
WHERE c.classification IN ('not_quantifiable', 'no_goal')
AND c.nudge_message IS NOT NULL
ORDER BY ts.session_date DESC, c.participant_name;

-- 4. Get participant progress summary
SELECT 
    c.participant_name,
    COUNT(*) as total_commitments,
    COUNT(CASE WHEN c.classification = 'quantifiable' THEN 1 END) as quantifiable_goals,
    COUNT(CASE WHEN c.classification = 'not_quantifiable' THEN 1 END) as vague_goals,
    COUNT(CASE WHEN c.classification = 'no_goal' THEN 1 END) as no_goals,
    AVG(gp.progress_percentage) as avg_progress_percentage
FROM peer_progress.commitments c
LEFT JOIN peer_progress.goal_progress gp ON c.id = gp.commitment_id
GROUP BY c.participant_name
ORDER BY total_commitments DESC;

-- 5. Get recent sessions with analysis status
SELECT 
    ts.filename,
    ts.group_name,
    ts.session_date,
    ta.processing_status,
    ta.error_message,
    ta.created_at as analysis_created_at
FROM peer_progress.transcript_sessions ts
LEFT JOIN peer_progress.transcript_analysis ta ON ts.id = ta.transcript_session_id
ORDER BY ts.session_date DESC
LIMIT 10;

-- 6. Get all commitments by group and date
SELECT 
    ts.group_name,
    ts.session_date,
    c.participant_name,
    c.commitment_text,
    c.classification,
    c.exact_quote,
    c.timestamp_in_transcript
FROM peer_progress.transcript_sessions ts
JOIN peer_progress.commitments c ON ts.id = c.transcript_session_id
ORDER BY ts.session_date DESC, ts.group_name, c.participant_name;

-- 7. Get goal completion rates
SELECT 
    DATE_TRUNC('week', ts.session_date) as week_start,
    COUNT(CASE WHEN c.classification = 'quantifiable' THEN 1 END) as quantifiable_goals,
    COUNT(CASE WHEN gp.progress_percentage >= 100 THEN 1 END) as completed_goals,
    ROUND(
        COUNT(CASE WHEN gp.progress_percentage >= 100 THEN 1 END)::DECIMAL / 
        NULLIF(COUNT(CASE WHEN c.classification = 'quantifiable' THEN 1 END), 0) * 100, 
        2
    ) as completion_rate_percentage
FROM peer_progress.transcript_sessions ts
JOIN peer_progress.commitments c ON ts.id = c.transcript_session_id
LEFT JOIN peer_progress.goal_progress gp ON c.id = gp.commitment_id
GROUP BY DATE_TRUNC('week', ts.session_date)
ORDER BY week_start DESC;

-- 8. Get detailed analysis for a specific session
SELECT 
    ts.filename,
    ts.group_name,
    ts.session_date,
    ta.extracted_commitments_json,
    ta.classification_results_json,
    ta.nudge_messages_json
FROM peer_progress.transcript_sessions ts
JOIN peer_progress.transcript_analysis ta ON ts.id = ta.transcript_session_id
WHERE ts.filename = 'Group 1.1 (Bryan Stephens, David Taiwo, Nirav Sheth)';

-- 9. Get members with most commitments
SELECT 
    m.name as member_name,
    COUNT(c.id) as total_commitments,
    COUNT(CASE WHEN c.classification = 'quantifiable' THEN 1 END) as quantifiable_commitments,
    AVG(gp.progress_percentage) as avg_completion_rate
FROM peer_progress.members m
LEFT JOIN peer_progress.commitments c ON m.id = c.member_id
LEFT JOIN peer_progress.goal_progress gp ON c.id = gp.commitment_id
GROUP BY m.id, m.name
HAVING COUNT(c.id) > 0
ORDER BY total_commitments DESC;

-- 10. Get weekly commitment trends
SELECT 
    DATE_TRUNC('week', ts.session_date) as week_start,
    COUNT(c.id) as total_commitments,
    COUNT(CASE WHEN c.classification = 'quantifiable' THEN 1 END) as quantifiable_commitments,
    COUNT(CASE WHEN c.classification = 'not_quantifiable' THEN 1 END) as vague_commitments,
    COUNT(CASE WHEN c.classification = 'no_goal' THEN 1 END) as no_goal_commitments
FROM peer_progress.transcript_sessions ts
JOIN peer_progress.commitments c ON ts.id = c.transcript_session_id
GROUP BY DATE_TRUNC('week', ts.session_date)
ORDER BY week_start DESC;
