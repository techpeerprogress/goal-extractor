"""
Streamlit dashboard to display extracted goals from transcripts.
Reads data directly from Supabase.
"""

import streamlit as st
import re
import os
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def get_supabase_client() -> Client:
    """Create and return Supabase client"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        return None
    
    return create_client(supabase_url, supabase_key)


@st.cache_data(show_spinner=False, ttl=120)
def fetch_session_dates(organization_id: str) -> List[str]:
    """Fetch distinct session dates (sorted desc) for quick date filter population."""
    supabase = get_supabase_client()
    if not supabase:
        return []
    try:
        res = (
            supabase
            .schema('peer_progress')
            .table('transcript_sessions')
            .select('session_date')
            .eq('organization_id', organization_id)
            .not_.is_('session_date', 'null')  # exclude nulls
            .order('session_date', desc=True)
            .execute()
        )
        dates = [r['session_date'] for r in (res.data or []) if r.get('session_date')]
        # remove duplicates while preserving order
        seen = set()
        unique_desc = []
        for d in dates:
            if d not in seen:
                seen.add(d)
                unique_desc.append(d)
        return unique_desc
    except Exception:
        return []

@st.cache_data(show_spinner=True, ttl=120)
def load_groups_from_supabase_by_date(organization_id: str, session_date: str) -> List[Dict]:
    """Load groups and goals for a specific session date. Cached for faster reloads."""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        # Get sessions only for the selected date
        sessions_result = (
            supabase
            .schema('peer_progress')
            .table('transcript_sessions')
            .select('id, filename, group_name, session_date')
            .eq('organization_id', organization_id)
            .eq('session_date', session_date)
            .order('session_date', desc=True)
            .execute()
        )
        sessions = sessions_result.data or []
        
        groups = []

        if not sessions:
            return groups

        session_ids = [s['id'] for s in sessions]
        # Fetch all goals for these sessions in a single query
        goals_result = (
            supabase
            .schema('peer_progress')
            .table('quantifiable_goals')
            .select('transcript_session_id, participant_name, goal_text, source_details')
            .in_('transcript_session_id', session_ids)
            .execute()
        )
        goals = goals_result.data or []

        # Group goals by session_id for fast assembly
        goals_by_session = {}
        for g in goals:
            goals_by_session.setdefault(g['transcript_session_id'], []).append(g)
            
        for session in sessions:
            session_id = session['id']
            group_name = session.get('group_name', session.get('filename', 'Unknown Group'))
            s_date = session.get('session_date', 'Unknown')
            content_parts = []

            for goal in goals_by_session.get(session_id, []):
                participant_name = goal.get('participant_name', 'Unknown')
                source_details = goal.get('source_details', {}) or {}
                
                content_parts.append(f"### {participant_name}\n")
                content_parts.append("\n**What They Discussed:**\n\n")
                
                if source_details.get('discussion'):
                    content_parts.append(f"{source_details['discussion']}\n")
                
                content_parts.append("\n**Their Commitment for Next Week:**\n\n")
                goal_text = goal.get('goal_text', 'No specific commitment made')
                content_parts.append(f"{goal_text}\n")
                
                content_parts.append("\n**Classification:**\n\n")
                classification = source_details.get('classification', 'not_quantifiable')
                
                # Map database classification to display format
                if classification == 'quantifiable':
                    content_parts.append("Quantifiable\n")
                elif classification == 'not_quantifiable':
                    content_parts.append("Not Quantifiable\n")
                elif classification == 'no_goal':
                    content_parts.append("No Goal\n")
                elif classification == 'decision_pending':
                    content_parts.append("Decision Pending\n")
                else:
                    content_parts.append("Not Quantifiable\n")
                
                if source_details.get('classification_reason'):
                    content_parts.append("\n**Why This Classification:**\n\n")
                    content_parts.append(f"{source_details['classification_reason']}\n")
                
                if source_details.get('exact_quote'):
                    content_parts.append("\n**Exact Quote:**\n\n")
                    content_parts.append(f"{source_details['exact_quote']}\n")
                
                if source_details.get('timestamp'):
                    content_parts.append("\n**Timestamp:**\n\n")
                    content_parts.append(f"{source_details['timestamp']}\n")
                
                if source_details.get('how_to_quantify'):
                    content_parts.append("\n**How to Make It Quantifiable:**\n\n")
                    content_parts.append(f"{source_details['how_to_quantify']}\n")
                
                if source_details.get('nudge_message'):
                    content_parts.append("\n**Personalized Accountability Nudge Message:**\n\n")
                    nudge = source_details['nudge_message']
                    # Add blockquote markers if not already present
                    nudge_lines = nudge.split('\n')
                    for line in nudge_lines:
                        if not line.strip().startswith('>'):
                            content_parts.append(f"> {line}\n")
                        else:
                            content_parts.append(f"{line}\n")
                
                content_parts.append("\n---\n\n")
            
            groups.append({
                'name': group_name,
                'content': ''.join(content_parts),
                'session_date': s_date or 'Unknown'
            })
        
        return groups
    
    except Exception as e:
        st.error(f"Error loading from Supabase: {e}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
        return []

def format_content_with_indicators(content: str):
    """Format content and add visual indicators for classifications"""
    lines = content.split('\n')
    formatted_sections = []
    
    i = 0
    current_participant = None
    current_section = []
    
    while i < len(lines):
        line = lines[i]
        
        # Participant name
        if line.strip().startswith('### '):
            # Process previous participant if exists
            if current_participant and current_section:
                formatted_sections.append({
                    'participant': current_participant,
                    'content': '\n'.join(current_section)
                })
            
            current_participant = line.replace('###', '').strip()
            current_section = [line]
            i += 1
            continue
        
        # Check for classification line
        if '**Classification:**' in line:
            # Add classification and current content
            current_section.append(line)
            
            # Get classification value
            if ':' in line:
                classification_text = line.split(':', 1)[1].strip()
            else:
                i += 1
                if i < len(lines):
                    classification_text = lines[i].strip()
                    current_section.append(lines[i])
                else:
                    classification_text = ""
            
            # Clean classification
            classification_clean = classification_text.replace('🚫', '').replace('✅', '').replace('📝', '').replace('🤔', '').strip()
            
            i += 1
            continue
        
        # Add line to current section
        current_section.append(line)
        i += 1
    
    # Add last participant
    if current_participant and current_section:
        formatted_sections.append({
            'participant': current_participant,
            'content': '\n'.join(current_section)
        })
    
    return formatted_sections

def extract_classification(content: str) -> str:
    """Extract classification from participant content"""
    match = re.search(r'\*\*Classification:\*\*\s*(.+?)(?:\n|$)', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""

def main():
    st.set_page_config(page_title="Goal Extractor Dashboard", layout="wide")
    
    # Add custom CSS for smaller fonts
    st.markdown("""
    <style>
        .main h1 { font-size: 2rem !important; }
        .main h2 { font-size: 1.5rem !important; }
        .main h3 { font-size: 1.2rem !important; }
        .main p, .main li, .main div[data-testid="stMarkdownContainer"] { 
            font-size: 0.9rem !important; 
            line-height: 1.4 !important;
        }
        .stMarkdown { font-size: 0.9rem !important; }
        .stExpander label { font-size: 1rem !important; }
        div[data-testid="stSuccess"] > div,
        div[data-testid="stError"] > div,
        div[data-testid="stInfo"] > div,
        div[data-testid="stWarning"] > div {
            font-size: 0.85rem !important;
        }
        /* Reduce padding in expanders */
        .streamlit-expanderHeader { padding: 0.5rem 0 !important; }
        .streamlit-expanderContent { padding: 0.5rem 0 !important; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🎯 Goal Extractor Dashboard")
    st.markdown("View quantifiable and non-quantifiable goals extracted from mastermind transcripts")
    
    # Check Supabase connection
    supabase = get_supabase_client()
    if not supabase:
        st.error("❌ Could not connect to Supabase. Please check your SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        return
    
    try:
        organization_id = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e'
        
        # Fast date bootstrap (cached)
        st.sidebar.header("Filters")
        session_dates = fetch_session_dates(organization_id)
        if not session_dates:
            st.warning("No sessions found in Supabase. Run the extractor to populate data.")
            return

        # Default to latest date
        selected_date = st.sidebar.selectbox("📅 Session Date", session_dates, index=0)

        # Load only groups for selected date (cached)
        groups = load_groups_from_supabase_by_date(organization_id, selected_date)
        if not groups:
            st.info("No goals found for the selected date.")
            return
        
        st.sidebar.header("Groups")
        
        # Group selector - show only filtered groups
        group_names = [g['name'] for g in groups]
        selected_group_name = None
        if not group_names:
            st.sidebar.warning("No groups found for selected date filter.")
        else:
            selected_group_name = st.sidebar.selectbox("Select a group", group_names)
        
        selected_group = None
        if selected_group_name:
            selected_group = next((g for g in groups if g['name'] == selected_group_name), None)
        
        if selected_group:
            st.markdown(f"### {selected_group['name']}")
            session_date = selected_group.get('session_date', 'Unknown')
            if session_date and session_date != 'Unknown':
                st.caption(f"📅 Session Date: {session_date}")
            st.divider()
            
            # Display content with formatting
            content = selected_group.get('content', '')
            
            # Debug info
            if not content:
                st.warning(f"No content found for this group. Content key exists: {'content' in selected_group}")
                st.json(selected_group)
                return
            
            if not content.strip():
                st.warning("Content is empty after stripping.")
                st.code(f"Content length: {len(content)}")
                return
            
            # Process content line by line to add indicators
            lines = content.split('\n')
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Participant name
                if line.strip().startswith('### '):
                    participant_name = line.replace('###', '').strip()
                    st.markdown(f"#### 👤 {participant_name}")
                    
                    # Look ahead for classification
                    j = i + 1
                    classification = None
                    while j < len(lines) and j < i + 20:  # Look ahead up to 20 lines
                        if '**Classification:**' in lines[j]:
                            # Get classification value
                            classification_line = lines[j]
                            if ':' in classification_line:
                                classification = classification_line.split(':', 1)[1].strip()
                            else:
                                if j + 1 < len(lines):
                                    classification = lines[j + 1].strip()
                            break
                        j += 1
                    
                    # Add classification badge if found
                    if classification:
                        classification_clean = classification.replace('🚫', '').replace('✅', '').replace('📝', '').replace('🤔', '').strip()
                        if 'Quantifiable' in classification_clean and 'Not' not in classification_clean:
                            st.success("✅ **Quantifiable Goal**")
                        elif 'Not Quantifiable' in classification_clean:
                            st.error("❌ **Not Quantifiable**")
                        elif 'No Goal' in classification_clean:
                            st.info("⚪ **No Goal**")
                        elif 'Decision Pending' in classification_clean:
                            st.warning("🤔 **Decision Pending**")
                    
                    i += 1
                    continue
                
                # Regular line - display as markdown
                st.markdown(line)
                i += 1
        
        # Summary stats
        st.sidebar.divider()
        st.sidebar.header("Summary")
        
        # Get all groups (unfiltered) for total stats (aggregate by calling cached per date and combining counts)
        all_dates = session_dates
        total_groups = 0
        total_participants = 0
        total_goals = 0
        quantifiable_count = 0
        
        # Compute stats for current (filtered) groups fast
        filtered_groups_count = len(groups)
        for group in groups:
            content = group.get('content', '')
            if not content:
                continue
            participants = re.findall(r'^### (.+)$', content, re.MULTILINE)
            total_participants += len(participants)
            quantifiable_matches = re.findall(r'\*\*Classification:\*\*\s*(.+?)(?:\n|$)', content, re.MULTILINE)
            for match in quantifiable_matches:
                classification = match.strip()
                classification_clean = classification.replace('🚫', '').replace('✅', '').replace('📝', '').replace('🤔', '').strip()
                if 'Quantifiable' in classification_clean and 'Not' not in classification_clean:
                    quantifiable_count += 1
                total_goals += 1
        
        # Total groups across all dates (count sessions only)
        total_groups = sum(len(load_groups_from_supabase_by_date(organization_id, d)) > 0 for d in all_dates)
        
        # Display stats for filtered groups
        st.sidebar.metric("Groups (Filtered)", filtered_groups_count)
        st.sidebar.metric("Total Groups (All)", total_groups)
        st.sidebar.metric("Participants", total_participants)
        if total_goals > 0:
            st.sidebar.metric("Total Goals", total_goals)
            st.sidebar.metric("✅ Quantifiable", quantifiable_count)
            st.sidebar.metric("❌ Not Quantifiable", total_goals - quantifiable_count)
        
    except Exception as e:
        st.error(f"Error loading goals: {e}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
