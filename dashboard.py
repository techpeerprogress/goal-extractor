import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
from supabase import create_client, Client

# Page configuration
st.set_page_config(
    page_title="Goal Extractor Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_supabase():
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url:
            try:
                supabase_url = st.secrets["SUPABASE_URL"]
            except:
                pass
                
        if not supabase_key:
            try:
                supabase_key = st.secrets["SUPABASE_SERVICE_KEY"]
            except:
                pass
        
        if not supabase_url or not supabase_key:
            st.error("❌ Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
            return None
            
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"❌ Error connecting to Supabase: {e}")
        return None

# Data fetching functions
def fetch_vague_goals(supabase: Client, organization_id: str = None):
    """Fetch vague goals that need clarification"""
    try:
        query = supabase.schema('peer_progress').table('vague_goals_detected').select('*')
        if organization_id:
            query = query.eq('organization_id', organization_id)
        
        result = query.order('created_at', desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error fetching vague goals: {e}")
        return []

def fetch_quantifiable_goals(supabase: Client, organization_id: str = None, start_date: str = None, end_date: str = None):
    """Fetch only quantifiable goals with optional date filtering"""
    try:
        query = supabase.schema('peer_progress').table('quantifiable_goals').select('*')
        
        if organization_id:
            query = query.eq('organization_id', organization_id)
        if start_date:
            query = query.gte('call_date', start_date)
        if end_date:
            query = query.lte('call_date', end_date)
        
        result = query.order('call_date', desc=True).execute()
        all_goals = result.data if result.data else []
        
        # Filter to only show quantifiable goals, excluding Main Room sessions
        quantifiable_goals = []
        for goal in all_goals:
            # Skip Main Room goals
            group_name = goal.get('group_name', '')
            if group_name and ('Main Room' in group_name or group_name.startswith('Main Room')):
                continue
            
            source_details = goal.get('source_details', {})
            goal_type = source_details.get('goal_type', 'quantifiable')
            if goal_type == 'quantifiable':
                quantifiable_goals.append(goal)
        
        return quantifiable_goals
    except Exception as e:
        st.error(f"Error fetching quantifiable goals: {e}")
        return []

def fetch_non_quantifiable_goals(supabase: Client, organization_id: str = None, start_date: str = None, end_date: str = None):
    """Fetch only non-quantifiable goals with optional date filtering"""
    try:
        query = supabase.schema('peer_progress').table('quantifiable_goals').select('*')
        
        if organization_id:
            query = query.eq('organization_id', organization_id)
        if start_date:
            query = query.gte('call_date', start_date)
        if end_date:
            query = query.lte('call_date', end_date)
        
        result = query.order('call_date', desc=True).execute()
        all_goals = result.data if result.data else []
        
        # Filter to only show non-quantifiable goals, excluding Main Room sessions
        non_quantifiable_goals = []
        for goal in all_goals:
            # Skip Main Room goals
            group_name = goal.get('group_name', '')
            if group_name and ('Main Room' in group_name or group_name.startswith('Main Room')):
                continue
            
            source_details = goal.get('source_details', {})
            goal_type = source_details.get('goal_type', 'quantifiable')
            if goal_type == 'non_quantifiable':
                non_quantifiable_goals.append(goal)
        
        return non_quantifiable_goals
    except Exception as e:
        st.error(f"Error fetching non-quantifiable goals: {e}")
        return []

def fetch_community_posts(supabase: Client, organization_id: str = None):
    """Fetch community posts"""
    try:
        result = supabase.schema('peer_progress').table('community_posts').select('*').order('created_at', desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error fetching community posts: {e}")
        return []

def fetch_member_attendance(supabase: Client, organization_id: str = None):
    """Fetch member attendance data"""
    try:
        result = supabase.schema('peer_progress').table('member_attendance').select('*').order('call_date', desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error fetching member attendance: {e}")
        return []

def fetch_member_changes(supabase: Client, organization_id: str = None):
    """Fetch member change log"""
    try:
        result = supabase.schema('peer_progress').table('member_change_log').select('*').order('created_at', desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error fetching member changes: {e}")
        return []

def fetch_marketing_activities(supabase: Client, organization_id: str = None, start_date: str = None, end_date: str = None):
    """Fetch marketing activities with optional date filtering"""
    try:
        query = supabase.schema('peer_progress').table('marketing_activities').select('*')
        
        if organization_id:
            query = query.eq('organization_id', organization_id)
        if start_date:
            query = query.gte('session_date', start_date)
        if end_date:
            query = query.lte('session_date', end_date)
        
        result = query.order('session_date', desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error fetching marketing activities: {e}")
        return []

def fetch_pipeline_outcomes(supabase: Client, organization_id: str = None, start_date: str = None, end_date: str = None):
    """Fetch pipeline outcomes with optional date filtering"""
    try:
        query = supabase.schema('peer_progress').table('pipeline_outcomes').select('*')
        
        if organization_id:
            query = query.eq('organization_id', organization_id)
        if start_date:
            query = query.gte('session_date', start_date)
        if end_date:
            query = query.lte('session_date', end_date)
        
        result = query.order('session_date', desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error fetching pipeline outcomes: {e}")
        return []

def fetch_challenges_strategies(supabase: Client, organization_id: str = None, start_date: str = None, end_date: str = None):
    """Fetch challenges and strategies with optional date filtering"""
    try:
        challenges_query = supabase.schema('peer_progress').table('challenges').select('*')
        strategies_query = supabase.schema('peer_progress').table('strategies').select('*')
        
        if organization_id:
            challenges_query = challenges_query.eq('organization_id', organization_id)
            strategies_query = strategies_query.eq('organization_id', organization_id)
        if start_date:
            challenges_query = challenges_query.gte('session_date', start_date)
            strategies_query = strategies_query.gte('created_at', start_date)
        if end_date:
            challenges_query = challenges_query.lte('session_date', end_date)
            strategies_query = strategies_query.lte('created_at', end_date)
        
        challenges_result = challenges_query.order('session_date', desc=True).execute()
        strategies_result = strategies_query.order('created_at', desc=True).execute()
        
        return {
            'challenges': challenges_result.data if challenges_result.data else [],
            'strategies': strategies_result.data if strategies_result.data else []
        }
    except Exception as e:
        st.error(f"Error fetching challenges/strategies: {e}")
        return {'challenges': [], 'strategies': []}

def fetch_stuck_signals(supabase: Client, organization_id: str = None, start_date: str = None, end_date: str = None):
    """Fetch stuck signals and help offers with optional date filtering"""
    try:
        stuck_query = supabase.schema('peer_progress').table('stuck_signals').select('*')
        help_query = supabase.schema('peer_progress').table('help_offers').select('*')
        sentiment_query = supabase.schema('peer_progress').table('call_sentiment').select('*')
        
        if organization_id:
            stuck_query = stuck_query.eq('organization_id', organization_id)
            help_query = help_query.eq('organization_id', organization_id)
            sentiment_query = sentiment_query.eq('organization_id', organization_id)
        if start_date:
            stuck_query = stuck_query.gte('session_date', start_date)
            help_query = help_query.gte('created_at', start_date)
            sentiment_query = sentiment_query.gte('session_date', start_date)
        if end_date:
            stuck_query = stuck_query.lte('session_date', end_date)
            help_query = help_query.lte('created_at', end_date)
            sentiment_query = sentiment_query.lte('session_date', end_date)
        
        stuck_result = stuck_query.order('created_at', desc=True).execute()
        help_result = help_query.order('created_at', desc=True).execute()
        sentiment_result = sentiment_query.order('session_date', desc=True).execute()
        
        return {
            'stuck_signals': stuck_result.data if stuck_result.data else [],
            'help_offers': help_result.data if help_result.data else [],
            'sentiment': sentiment_result.data if sentiment_result.data else []
        }
    except Exception as e:
        st.error(f"Error fetching stuck signals: {e}")
        return {'stuck_signals': [], 'help_offers': [], 'sentiment': []}

def fetch_goal_source_analytics(supabase: Client, organization_id: str = None):
    """Fetch goal source tracking analytics"""
    try:
        goals_result = supabase.schema('peer_progress').table('quantifiable_goals').select('created_at').execute()
        vague_result = supabase.schema('peer_progress').table('vague_goals_detected').select('status, created_at').execute()
        
        return {
            'goals': goals_result.data if goals_result.data else [],
            'vague_goals': vague_result.data if vague_result.data else []
        }
    except Exception as e:
        st.error(f"Error fetching goal source analytics: {e}")
        return {'goals': [], 'vague_goals': []}

# Tab functions
def show_vague_goals_tab(supabase: Client):
    """Display non-quantifiable goals that need clarification"""
    st.header("🚨 Vague Goals - Non-Quantifiable Goals")
    
    st.subheader("📅 Date Filter")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        start_date = st.date_input("Start Date", value=None, key="vague_start_date")
    with col2:
        end_date = st.date_input("End Date", value=None, key="vague_end_date")
    with col3:
        if st.button("Clear Date Filter", key="vague_clear"):
            st.rerun()
    
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    
    vague_goals = fetch_non_quantifiable_goals(supabase, start_date=start_date_str, end_date=end_date_str)
    
    if not vague_goals:
        st.info("✅ No non-quantifiable goals found. All goals are quantifiable!")
        return
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        participant_filter = st.selectbox("Filter by Participant", ["All"] + list(set([g.get('participant_name', '') for g in vague_goals])), key="vague_participant_filter")
    with col2:
        source_filter = st.selectbox("Filter by Source", ["All"] + list(set([g.get('source_type', '') for g in vague_goals])), key="vague_source_filter")
    with col3:
        group_filter = st.selectbox("Filter by Group", ["All"] + list(set([g.get('group_name', '') for g in vague_goals])), key="vague_group_filter")
    
    # Apply filters
    filtered_goals = vague_goals
    if participant_filter != "All":
        filtered_goals = [g for g in filtered_goals if g.get('participant_name') == participant_filter]
    if source_filter != "All":
        filtered_goals = [g for g in filtered_goals if g.get('source_type') == source_filter]
    if group_filter != "All":
        filtered_goals = [g for g in filtered_goals if g.get('group_name') == group_filter]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Non-Quantifiable Goals", len(filtered_goals))
    with col2:
        ai_goals = len([g for g in filtered_goals if g.get('source_type') == 'ai_extraction'])
        st.metric("🤖 AI Extracted", ai_goals)
    with col3:
        manual_goals = len([g for g in filtered_goals if g.get('source_type') == 'human_input'])
        st.metric("👤 Manual Input", manual_goals)
    
    # Group goals by participant and session (same format as quantifiable goals)
    st.subheader(f"📋 Non-Quantifiable Goals by Member & Session ({len(filtered_goals)} total goals)")
    
    # Group goals by participant_name and call_date
    grouped_goals = {}
    for goal in filtered_goals:
        participant = goal.get('participant_name', 'Unknown')
        call_date = goal.get('call_date', 'N/A')
        group_name = goal.get('group_name', 'N/A')
        
        key = f"{participant}|{call_date}|{group_name}"
        if key not in grouped_goals:
            grouped_goals[key] = {
                'participant': participant,
                'call_date': call_date,
                'group_name': group_name,
                'goals': []
            }
        grouped_goals[key]['goals'].append(goal)
    
    # Display grouped goals
    for key, session_data in grouped_goals.items():
        participant = session_data['participant']
        call_date = session_data['call_date']
        group_name = session_data['group_name']
        goals = session_data['goals']
        
        # Count AI vs Manual goals for this session
        ai_count = len([g for g in goals if g.get('source_type') == 'ai_extraction'])
        manual_count = len([g for g in goals if g.get('source_type') == 'human_input'])
        
        # Create expander title with goal count
        title = f"👤 {participant} - {group_name} ({call_date}) - {len(goals)} non-quantifiable goals"
        if ai_count > 0 and manual_count > 0:
            title += f" [🤖{ai_count} AI, 👤{manual_count} Manual]"
        elif ai_count > 0:
            title += f" [🤖{ai_count} AI]"
        elif manual_count > 0:
            title += f" [👤{manual_count} Manual]"
        
        with st.expander(title):
            st.write(f"**Session:** {group_name} on {call_date}")
            st.write(f"**Total Non-Quantifiable Goals:** {len(goals)}")
            st.write("⚠️ **These goals need clarification to become quantifiable**")
            st.divider()
            
            # Display each goal in this session
            for i, goal in enumerate(goals, 1):
                goal_text = goal.get('goal_text', 'No goal')
                source_type = goal.get('source_type', 'ai_extraction')
                target_number = goal.get('target_number', 'N/A')
                
                # Source badge
                source_badge = "🤖 AI" if source_type == 'ai_extraction' else "👤 Manual" if source_type == 'human_input' else f"📝 {source_type}"
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Goal {i}:** {goal_text}")
                    st.write(f"**Target:** {target_number}")
                    st.write("**Type:** ⚠️ Not Quantifiable")
                    
                with col2:
                    st.write(f"**Source:** {source_badge}")
                    st.info("⚠️ Needs clarification")
                
                # Show source details if available
                source_details = goal.get('source_details', {})
                if source_details:
                    with st.expander(f"Details for Goal {i}", expanded=False):
                        if source_type == 'ai_extraction':
                            confidence = source_details.get('confidence_score', 'N/A')
                            st.write(f"- Confidence: {confidence}")
                            st.write(f"- Method: AI Transcript Analysis")
                        elif source_type == 'human_input':
                            input_method = source_details.get('input_method', 'N/A')
                            st.write(f"- Method: {input_method}")
                            notes = source_details.get('notes', '')
                            if notes:
                                st.write(f"- Notes: {notes}")
                
                if i < len(goals):  # Add separator between goals
                    st.divider()

def show_quantifiable_goals_tab(supabase: Client):
    """Display quantifiable goals and progress tracking"""
    st.header("🎯 Quantifiable Goals Tracking")
    
    st.subheader("📅 Date Filter")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        start_date = st.date_input("Start Date", value=None)
    with col2:
        end_date = st.date_input("End Date", value=None)
    with col3:
        if st.button("Clear Date Filter"):
            st.rerun()
    
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    
    goals = fetch_quantifiable_goals(supabase, start_date=start_date_str, end_date=end_date_str)
    
    if not goals:
        st.info("📝 No quantifiable goals found for the selected date range.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Quantifiable Goals", len(goals))
    with col2:
        ai_goals = len([g for g in goals if g.get('source_type') == 'ai_extraction'])
        st.metric("🤖 AI Goals", ai_goals)
    with col3:
        manual_goals = len([g for g in goals if g.get('source_type') == 'human_input'])
        st.metric("👤 Manual Goals", manual_goals)
    with col4:
        unique_participants = len(set([g.get('participant_name', '') for g in goals]))
        st.metric("Active Participants", unique_participants)
    
    st.subheader("🔍 Additional Filters")
    col1, col2, col3 = st.columns(3)
    with col1:
        participant_filter = st.selectbox("Filter by Participant", ["All"] + list(set([g.get('participant_name', '') for g in goals])), key="quantifiable_participant_filter")
    with col2:
        source_filter = st.selectbox("Filter by Source", ["All"] + list(set([g.get('source_type', '') for g in goals])), key="quantifiable_source_filter")
    with col3:
        if st.button("➕ Add Manual Goal"):
            st.session_state.show_manual_goal_form = True
    
    # Manual goal form
    if st.session_state.get('show_manual_goal_form', False):
        st.subheader("➕ Add Manual Goal")
        with st.form("manual_goal_form"):
            col1, col2 = st.columns(2)
            with col1:
                manual_participant = st.text_input("Participant Name", key="manual_participant")
                manual_group = st.text_input("Group Name", key="manual_group")
            with col2:
                manual_target = st.number_input("Target Number", min_value=0, key="manual_target")
                manual_date = st.date_input("Call Date", value=datetime.now().date(), key="manual_date")
            
            manual_goal_text = st.text_area("Goal Text", key="manual_goal_text")
            manual_notes = st.text_area("Notes (Optional)", key="manual_notes")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.form_submit_button("✅ Add Goal"):
                    if manual_participant and manual_goal_text and manual_target:
                        # This would need to be implemented with actual database connection
                        st.success(f"✅ Goal added for {manual_participant}: {manual_goal_text[:50]}...")
                        st.session_state.show_manual_goal_form = False
                        st.rerun()
                    else:
                        st.error("Please fill in all required fields")
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    st.session_state.show_manual_goal_form = False
                    st.rerun()
    
    filtered_goals = goals
    if participant_filter != "All":
        filtered_goals = [g for g in filtered_goals if g.get('participant_name') == participant_filter]
    if source_filter != "All":
        filtered_goals = [g for g in filtered_goals if g.get('source_type') == source_filter]
    
    # Group goals by participant and session
    st.subheader(f"📋 Goals by Member & Session ({len(filtered_goals)} total goals)")
    
    # Group goals by participant_name and call_date
    grouped_goals = {}
    for goal in filtered_goals:
        participant = goal.get('participant_name', 'Unknown')
        call_date = goal.get('call_date', 'N/A')
        group_name = goal.get('group_name', 'N/A')
        
        key = f"{participant}|{call_date}|{group_name}"
        if key not in grouped_goals:
            grouped_goals[key] = {
                'participant': participant,
                'call_date': call_date,
                'group_name': group_name,
                'goals': []
            }
        grouped_goals[key]['goals'].append(goal)
    
    # Display grouped goals
    for key, session_data in grouped_goals.items():
        participant = session_data['participant']
        call_date = session_data['call_date']
        group_name = session_data['group_name']
        goals = session_data['goals']
        
        # Count goals by source
        ai_count = len([g for g in goals if g.get('source_type') == 'ai_extraction'])
        manual_count = len([g for g in goals if g.get('source_type') == 'human_input'])
        
        # Create expander title with goal count and source breakdown
        title = f"👤 {participant} - {group_name} ({call_date}) - {len(goals)} quantifiable goals"
        
        # Add source breakdown
        if ai_count > 0 and manual_count > 0:
            title += f" [🤖{ai_count} AI, 👤{manual_count} Manual]"
        elif ai_count > 0:
            title += f" [🤖{ai_count} AI]"
        elif manual_count > 0:
            title += f" [👤{manual_count} Manual]"
        
        with st.expander(title):
            st.write(f"**Session:** {group_name} on {call_date}")
            
            # Summary section
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Quantifiable Goals", len(goals))
            with col2:
                st.metric("✅ All Quantifiable", len(goals))
            
            st.divider()
            
            # Display each goal in this session
            for i, goal in enumerate(goals, 1):
                goal_text = goal.get('goal_text', 'No goal')
                source_type = goal.get('source_type', 'ai_extraction')
                target_number = goal.get('target_number', 'N/A')
                
                # Determine source badge and description
                source_details = goal.get('source_details', {})
                is_human = source_details.get('is_human_update', False) or source_type in ['human_input', 'qa_clarification', 'member_update']
                is_ai = source_details.get('is_ai_update', False) or source_type == 'ai_extraction'
                
                if source_type == 'qa_clarification':
                    source_badge = "👤 QA (Human)"
                    updated_by = goal.get('updated_by', 'Unknown')
                    source_desc = f"Clarified by {updated_by}"
                elif source_type == 'human_input':
                    source_badge = "👤 Human"
                    updated_by = goal.get('updated_by', 'Unknown')
                    source_desc = f"Manual entry by {updated_by}"
                elif source_type == 'ai_extraction':
                    source_badge = "🤖 AI"
                    source_desc = "AI transcript analysis"
                else:
                    source_badge = f"📝 {source_type}"
                    source_desc = source_type
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Goal {i}:** {goal_text}")
                    st.write(f"**Target:** {target_number}")
                    st.write("**Type:** ✅ Quantifiable")
                    
                with col2:
                    st.write(f"**Source:** {source_badge}")
                    st.caption(source_desc)
                    
                    # Progress tracking for quantifiable goals
                    progress = st.slider(f"Progress {i} (%)", 0, 100, 0, key=f"progress_{goal['id']}")
                    if st.button(f"Update {i}", key=f"update_{goal['id']}"):
                        st.info(f"Progress update for goal {i} would be implemented here")
                
                # Show source details if available
                if source_details:
                    with st.expander(f"Details for Goal {i}", expanded=False):
                        # Show update source clearly
                        if source_details.get('is_human_update'):
                            st.write("**Update Source:** 👤 Human")
                            if source_type == 'qa_clarification':
                                qa_member = source_details.get('qa_team_member', goal.get('updated_by', 'Unknown'))
                                st.write(f"- Clarified by: {qa_member}")
                                if source_details.get('member_contacted'):
                                    st.write(f"- Member was contacted: Yes")
                        elif source_details.get('is_ai_update'):
                            st.write("**Update Source:** 🤖 AI")
                            confidence = source_details.get('confidence_score', 'N/A')
                            st.write(f"- Confidence: {confidence}")
                            st.write(f"- Method: AI Transcript Analysis")
                        
                        # Show update timestamp if available
                        update_timestamp = source_details.get('update_timestamp')
                        if update_timestamp:
                            st.write(f"- Updated: {update_timestamp}")
                        
                        # Show additional context based on source type
                        if source_type == 'qa_clarification':
                            clarification_method = source_details.get('clarification_method', 'N/A')
                            st.write(f"- Method: {clarification_method}")
                            if source_details.get('original_vague_goal_id'):
                                st.write(f"- Original vague goal was clarified")
                        elif source_type == 'human_input':
                            input_method = source_details.get('input_method', 'manual_entry')
                            st.write(f"- Method: {input_method}")
                            notes = source_details.get('notes', '')
                            if notes:
                                st.write(f"- Notes: {notes}")
                
                if i < len(goals):  # Add separator between goals
                    st.divider()

def show_community_posting_tab(supabase: Client):
    """Display community posting activity"""
    st.header("📢 Community Goals Posting")
    
    posts = fetch_community_posts(supabase)
    
    if not posts:
        st.info("📝 No community posts found.")
        return
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Posts", len(posts))
    with col2:
        successful_posts = len([p for p in posts if p.get('status') == 'success'])
        st.metric("Successful Posts", successful_posts)
    with col3:
        platforms = list(set([p.get('platform', '') for p in posts]))
        st.metric("Platforms Used", len(platforms))
    
    # Recent posts
    st.subheader("Recent Posts")
    for post in posts[:10]:  # Show last 10 posts
        with st.expander(f"📢 {post.get('platform', 'Unknown Platform')} - {post.get('created_at', 'N/A')}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Platform:** {post.get('platform', 'N/A')}")
                st.write(f"**Content:** {post.get('content', 'N/A')}")
                st.write(f"**Status:** {post.get('status', 'N/A')}")
                
            with col2:
                st.write(f"**Channel:** {post.get('channel', 'N/A')}")
                st.write(f"**Posted At:** {post.get('posted_at', 'N/A')}")
                
                if post.get('status') == 'failed':
                    st.error("❌ Post failed")

def show_attendance_achievement_tab(supabase: Client):
    """Display attendance and goal achievement tracking"""
    st.header("📊 Attendance & Goal Achievement")
    
    attendance_data = fetch_member_attendance(supabase)
    
    if not attendance_data:
        st.info("📝 No attendance data found.")
        return
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(attendance_data)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sessions", len(df))
    with col2:
        avg_attendance = df['attended'].mean() * 100 if 'attended' in df.columns else 0
        st.metric("Avg Attendance %", f"{avg_attendance:.1f}%")
    with col3:
        unique_members = df['member_id'].nunique() if 'member_id' in df.columns else 0
        st.metric("Unique Members", unique_members)
    with col4:
        recent_sessions = len(df[df['call_date'] >= (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')])
        st.metric("Sessions This Week", recent_sessions)
    
    # Attendance chart
    if 'call_date' in df.columns and 'attendance_status' in df.columns:
        st.subheader("Attendance Over Time")
        # Convert attendance_status to numeric for chart
        df['attended_numeric'] = df['attendance_status'].map({'present': 1, 'absent': 0, 'excused': 0.5})
        attendance_by_date = df.groupby('call_date')['attended_numeric'].mean().reset_index()
        fig = px.line(attendance_by_date, x='call_date', y='attended_numeric', 
                     title="Attendance Rate Over Time")
        st.plotly_chart(fig, use_container_width=True)
    
    # Member attendance table
    if 'member_name' in df.columns:
        st.subheader("Member Attendance Summary")
        # Convert attendance_status to numeric for aggregation
        df['attended_numeric'] = df['attendance_status'].map({'present': 1, 'absent': 0, 'excused': 0.5})
        member_summary = df.groupby('member_name').agg({
            'attended_numeric': ['count', 'sum', 'mean']
        }).round(2)
        member_summary.columns = ['Total Sessions', 'Present Sessions', 'Attendance Rate']
        st.dataframe(member_summary)

def show_member_changes_tab(supabase: Client):
    """Display member change log"""
    st.header("📝 Member Change Log")
    
    changes = fetch_member_changes(supabase)
    
    if not changes:
        st.info("📝 No member changes found.")
        return
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Changes", len(changes))
    with col2:
        recent_changes = len([c for c in changes if c.get('created_at', '') >= (datetime.now() - timedelta(days=7)).isoformat()])
        st.metric("Changes This Week", recent_changes)
    with col3:
        change_types = list(set([c.get('change_type', '') for c in changes]))
        st.metric("Change Types", len(change_types))
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        change_type_filter = st.selectbox("Filter by Change Type", ["All"] + change_types, key="member_change_type_filter")
    with col2:
        member_filter = st.selectbox("Filter by Member", ["All"] + list(set([c.get('member_name', '') for c in changes])), key="member_change_member_filter")
    
    # Apply filters
    filtered_changes = changes
    if change_type_filter != "All":
        filtered_changes = [c for c in filtered_changes if c.get('change_type') == change_type_filter]
    if member_filter != "All":
        filtered_changes = [c for c in filtered_changes if c.get('member_name') == member_filter]
    
    # Display changes
    for change in filtered_changes:
        with st.expander(f"📝 {change.get('member_name', 'Unknown')} - {change.get('change_type', 'N/A')} ({change.get('created_at', 'N/A')})"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Change Type:** {change.get('change_type', 'N/A')}")
                st.write(f"**Description:** {change.get('description', 'N/A')}")
                st.write(f"**Previous Value:** {change.get('previous_value', 'N/A')}")
                st.write(f"**New Value:** {change.get('new_value', 'N/A')}")
                
            with col2:
                st.write(f"**Category:** {change.get('change_category', 'N/A')}")
                st.write(f"**Created:** {change.get('created_at', 'N/A')}")
                st.write(f"**Source:** {change.get('source_type', 'N/A')}")

def show_marketing_activities_tab(supabase: Client):
    """Display marketing activities and pipeline outcomes"""
    st.header("📈 Marketing Activities & Pipeline")
    
    st.subheader("📅 Date Filter")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        start_date = st.date_input("Start Date", value=None, key="marketing_start_date")
    with col2:
        end_date = st.date_input("End Date", value=None, key="marketing_end_date")
    with col3:
        if st.button("Clear Date Filter", key="marketing_clear"):
            st.rerun()
    
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    
    activities = fetch_marketing_activities(supabase, start_date=start_date_str, end_date=end_date_str)
    pipeline_outcomes = fetch_pipeline_outcomes(supabase, start_date=start_date_str, end_date=end_date_str)
    
    if not activities and not pipeline_outcomes:
        st.info("📝 No marketing activities or pipeline outcomes found.")
        return
    
    # Show pipeline outcomes section
    if pipeline_outcomes:
        st.subheader("🎯 Pipeline Outcomes")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_meetings = sum([p.get('meetings', 0) for p in pipeline_outcomes])
            st.metric("Total Meetings", total_meetings)
        with col2:
            total_proposals = sum([p.get('proposals', 0) for p in pipeline_outcomes])
            st.metric("Total Proposals", total_proposals)
        with col3:
            total_clients = sum([p.get('clients', 0) for p in pipeline_outcomes])
            st.metric("Total Clients", total_clients)
        with col4:
            unique_participants_pipeline = len(set([p.get('participant_name', '') for p in pipeline_outcomes]))
            st.metric("Participants", unique_participants_pipeline)
        
        # Recent pipeline outcomes table
        st.subheader("Recent Pipeline Outcomes")
        pipeline_df = pd.DataFrame(pipeline_outcomes)
        if not pipeline_df.empty:
            display_cols = ['participant_name', 'meetings', 'proposals', 'clients', 'session_date', 'notes']
            available_cols = [col for col in display_cols if col in pipeline_df.columns]
            st.dataframe(pipeline_df[available_cols].head(10))
        
        st.divider()
    
    if not activities:
        st.info("📝 No marketing activities found.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Activities", len(activities))
    with col2:
        unique_participants = len(set([a.get('participant_name', '') for a in activities]))
        st.metric("Active Participants", unique_participants)
    with col3:
        activities_by_type = {}
        for activity in activities:
            activity_type = activity.get('activity_category', 'Unknown')
            activities_by_type[activity_type] = activities_by_type.get(activity_type, 0) + 1
        st.metric("Activity Types", len(activities_by_type))
    with col4:
        recent_activities = len([a for a in activities if a.get('session_date', '') >= (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')])
        st.metric("Activities This Week", recent_activities)
    
    # Activity type breakdown
    if activities_by_type:
        st.subheader("Activity Type Breakdown")
        fig = px.pie(values=list(activities_by_type.values()), 
                     names=list(activities_by_type.keys()),
                     title="Marketing Activities by Type")
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent activities table
    st.subheader("Recent Activities")
    df = pd.DataFrame(activities)
    if not df.empty:
        st.dataframe(df[['participant_name', 'activity_category', 'activity_description', 'session_date']].head(10))

def show_challenges_strategies_tab(supabase: Client):
    """Display challenges and strategies"""
    st.header("🧠 Challenges & Strategies")
    
    st.subheader("📅 Date Filter")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        start_date = st.date_input("Start Date", value=None, key="challenges_start_date")
    with col2:
        end_date = st.date_input("End Date", value=None, key="challenges_end_date")
    with col3:
        if st.button("Clear Date Filter", key="challenges_clear"):
            st.rerun()
    
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    
    data = fetch_challenges_strategies(supabase, start_date=start_date_str, end_date=end_date_str)
    challenges = data['challenges']
    strategies = data['strategies']
    
    if not challenges and not strategies:
        st.info("📝 No challenges or strategies found.")
        return
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Challenges", len(challenges))
    with col2:
        st.metric("Total Strategies", len(strategies))
    with col3:
        unique_categories = len(set([c.get('category', '') for c in challenges]))
        st.metric("Challenge Categories", unique_categories)
    
    # Challenge categories breakdown
    if challenges:
        challenge_categories = {}
        for challenge in challenges:
            category = challenge.get('category', 'Unknown')
            challenge_categories[category] = challenge_categories.get(category, 0) + 1
        
        st.subheader("Challenge Categories")
        fig = px.bar(x=list(challenge_categories.keys()), 
                     y=list(challenge_categories.values()),
                     title="Challenges by Category")
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent challenges
    if challenges:
        st.subheader("Recent Challenges")
        for challenge in challenges[:5]:  # Show last 5 challenges
            with st.expander(f"🧠 {challenge.get('participant_name', 'Unknown')} - {challenge.get('challenge_description', 'No description')[:50]}..."):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Challenge:** {challenge.get('challenge_description', 'N/A')}")
                    st.write(f"**Category:** {challenge.get('category', 'N/A')}")
                    st.write(f"**Date:** {challenge.get('session_date', 'N/A')}")
                    
                with col2:
                    st.write(f"**Severity:** {challenge.get('severity_level', 'N/A')}")
                    st.write(f"**Status:** {challenge.get('status', 'N/A')}")

def show_stuck_frustrated_supported_tab(supabase: Client):
    """Display stuck signals, help offers, and sentiment analysis"""
    st.header("🚨 Group Health: Stuck/Frustrated/Supported")
    
    st.subheader("📅 Date Filter")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        start_date = st.date_input("Start Date", value=None, key="stuck_start_date")
    with col2:
        end_date = st.date_input("End Date", value=None, key="stuck_end_date")
    with col3:
        if st.button("Clear Date Filter", key="stuck_clear"):
            st.rerun()
    
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    
    data = fetch_stuck_signals(supabase, start_date=start_date_str, end_date=end_date_str)
    stuck_signals = data['stuck_signals']
    help_offers = data['help_offers']
    sentiment_data = data['sentiment']
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Stuck Signals", len(stuck_signals))
    with col2:
        st.metric("Help Offers", len(help_offers))
    with col3:
        avg_sentiment = sum([s.get('sentiment_score', 3) for s in sentiment_data]) / len(sentiment_data) if sentiment_data else 3
        st.metric("Avg Sentiment", f"{avg_sentiment:.1f}/5")
    with col4:
        critical_flags = len([s for s in sentiment_data if s.get('sentiment_score', 3) <= 2])
        st.metric("Critical Flags", critical_flags)
    
    # Sentiment over time
    if sentiment_data:
        st.subheader("Sentiment Over Time")
        sentiment_df = pd.DataFrame(sentiment_data)
        fig = px.line(sentiment_df, x='session_date', y='sentiment_score',
                     title="Call Sentiment Score Over Time")
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent stuck signals
    if stuck_signals:
        st.subheader("Recent Stuck Signals")
        for signal in stuck_signals[:5]:  # Show last 5
            with st.expander(f"🚨 {signal.get('participant_name', 'Unknown')} - {signal.get('stuck_classification', 'Unknown Type')}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Summary:** {signal.get('stuck_summary', 'N/A')}")
                    st.write(f"**Classification:** {signal.get('stuck_classification', 'N/A')}")
                    st.write(f"**Suggested Nudge:** {signal.get('suggested_nudge', 'N/A')}")
                    
                with col2:
                    st.write(f"**Severity:** {signal.get('severity_score', 'N/A')}")
                    st.write(f"**Date:** {signal.get('session_date', 'N/A')}")
    
    # Recent help offers
    if help_offers:
        st.subheader("Recent Help Offers")
        for offer in help_offers[:5]:  # Show last 5
            with st.expander(f"🤝 {offer.get('offerer_name', 'Unknown')} offered help"):
                st.write(f"**What They Offered:** {offer.get('help_description', 'N/A')}")
                st.write(f"**Classification:** {offer.get('classification', 'N/A')}")
                st.write(f"**Target:** {offer.get('target_participant', 'N/A')}")

def show_goal_source_tracking_tab(supabase: Client):
    """Display goal source tracking analytics"""
    st.header("📊 Goal Source Tracking")
    
    data = fetch_goal_source_analytics(supabase)
    goals = data['goals']
    vague_goals = data['vague_goals']
    
    if not goals and not vague_goals:
        st.info("📝 No goal source data found.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Goals", len(goals))
    with col2:
        st.metric("Vague Goals", len(vague_goals))
    with col3:
        recent_goals = len([g for g in goals if g.get('created_at', '') >= (datetime.now() - timedelta(days=7)).isoformat()])
        st.metric("Goals This Week", recent_goals)
    with col4:
        resolved_vague = len([g for g in vague_goals if g.get('status') == 'resolved'])
        st.metric("Resolved Vague Goals", resolved_vague)
    
    # Goal activity over time
    if goals:
        st.subheader("Goal Creation Over Time")
        goals_df = pd.DataFrame(goals)
        goals_df['created_at'] = pd.to_datetime(goals_df['created_at'])
        goals_by_date = goals_df.groupby(goals_df['created_at'].dt.date).size().reset_index()
        goals_by_date.columns = ['Date', 'Goals Created']
        
        fig = px.line(goals_by_date, x='Date', y='Goals Created', 
                     title="Goals Created Over Time")
        st.plotly_chart(fig, use_container_width=True)

# Main dashboard
def main():
    st.title("🎯 Goal Extractor Dashboard")
    st.markdown("Comprehensive analytics for mastermind group goal tracking and analysis")
    
    # Initialize Supabase
    supabase = init_supabase()
    if not supabase:
        return
    
    # Sidebar
    st.sidebar.title("📊 Dashboard")
    st.sidebar.markdown("Select a tab to view different analytics:")
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Quantifiable Goals", 
        "🚨 Vague Goals", 
        "📢 Community Posting",
        "📊 Attendance & Achievement",
        "📝 Member Changes"
    ])
    
    tab6, tab7, tab8, tab9 = st.tabs([
        "📈 Marketing Activities",
        "🧠 Challenges & Strategies", 
        "🚨 Group Health",
        "📊 Source Tracking"
    ])
    
    with tab1:
        show_quantifiable_goals_tab(supabase)
    
    with tab2:
        show_vague_goals_tab(supabase)
    
    with tab3:
        show_community_posting_tab(supabase)
    
    with tab4:
        show_attendance_achievement_tab(supabase)
    
    with tab5:
        show_member_changes_tab(supabase)
    
    with tab6:
        show_marketing_activities_tab(supabase)
    
    with tab7:
        show_challenges_strategies_tab(supabase)
    
    with tab8:
        show_stuck_frustrated_supported_tab(supabase)
    
    with tab9:
        show_goal_source_tracking_tab(supabase)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data Sources:** Supabase PostgreSQL")
    st.sidebar.markdown("**Last Updated:** " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()
