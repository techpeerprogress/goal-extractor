"""
Streamlit dashboard to display extracted goals from transcripts.
Displays the exact output format from quantifiable_goals.txt
"""

import streamlit as st
import re
from typing import List, Dict

def parse_goals_file(filepath: str) -> List[Dict]:
    """Parse the quantifiable_goals.txt file maintaining the exact format"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        import streamlit as st
        st.error(f"Error reading file {filepath}: {e}")
        return []
    
    groups = []
    
    # Find all File: sections - they're followed by separator and then content
    # Handle both old format (without Session Date) and new format (with Session Date)
    # Pattern: File: ... (may have Session Date line, then separator)
    file_pattern = r'File: (.+?)(?=\n)'
    file_matches = list(re.finditer(file_pattern, content, re.MULTILINE))
    
    for i, match in enumerate(file_matches):
        group_name = match.group(1).strip()
        
        # Find the start position after the File: line
        content_start = match.end()
        
        # Move to the end of the File: line
        while content_start < len(content) and content[content_start] != '\n':
            content_start += 1
        content_start += 1  # Skip newline after File: line
        
        # Look for Session Date line after File: line (optional)
        session_date = None
        if content_start < len(content):
            # Check if next line is "Session Date:"
            date_line_start = content_start
            date_line_end = date_line_start
            while date_line_end < len(content) and content[date_line_end] != '\n':
                date_line_end += 1
            
            date_line = content[date_line_start:date_line_end].strip()
            if date_line.startswith('Session Date:'):
                session_date = date_line.replace('Session Date:', '').strip()
                content_start = date_line_end + 1  # Move past Session Date line
        
        # Now find the separator line (========)
        while content_start < len(content) and content[content_start] != '=':
            content_start += 1
        
        # Skip the entire separator line
        while content_start < len(content) and content[content_start] != '\n':
            content_start += 1
        content_start += 1  # Skip the newline after separator
        
        # Skip any empty lines after the separator
        while content_start < len(content) and content[content_start] == '\n':
            content_start += 1
        
        # Find the end of this section (next File: or end of file)
        if i + 1 < len(file_matches):
            # Find the start of the next File: section
            content_end = file_matches[i + 1].start()
            # Move backward to find the start of the separator before the next File:
            # We want to stop before the separator line
            temp_end = content_end
            while temp_end > 0 and content[temp_end - 1] != '\n':
                temp_end -= 1
            if temp_end > content_start:
                content_end = temp_end
        else:
            content_end = len(content)
        
        # Extract the content (don't strip initially to preserve structure)
        group_content = content[content_start:content_end]
        # Remove trailing separator if present
        group_content = re.sub(r'\n={80,}\s*$', '', group_content)
        group_content = group_content.strip()
        
        groups.append({
            'name': group_name,
            'content': group_content,
            'session_date': session_date or 'Unknown'
        })
    
    return groups

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
    
    # File path
    import os
    # Try multiple possible paths
    possible_paths = [
        "quantifiable_goals.txt",  # Current directory
        os.path.join(os.path.dirname(__file__), "quantifiable_goals.txt") if __file__ else None,  # Script directory
    ]
    
    goals_file = None
    for path in possible_paths:
        if path and os.path.exists(path):
            goals_file = path
            break
    
    if not goals_file:
        st.error(f"File 'quantifiable_goals.txt' not found. Please run `python goal_extractor.py` first to generate the goals file.")
        st.info("Looking in: " + ", ".join([p for p in possible_paths if p]))
        return
    
    try:
        
        # Parse goals
        groups = parse_goals_file(goals_file)
        
        if not groups:
            st.warning("No goals found in the file. Make sure to run goal_extractor.py first.")
            return
        
        st.sidebar.header("Groups")
        
        # Group selector
        group_names = [g['name'] for g in groups]
        selected_group_name = st.sidebar.selectbox("Select a group", group_names)
        
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
        total_groups = len(groups)
        
        # Count participants and goals
        total_participants = 0
        total_goals = 0
        quantifiable_count = 0
        
        for group in groups:
            content = group['content']
            # Count participants (lines starting with ###)
            participants = re.findall(r'^### (.+)$', content, re.MULTILINE)
            total_participants += len(participants)
            
            # Count quantifiable goals
            quantifiable_matches = re.findall(r'\*\*Classification:\*\*\s*(.+?)(?:\n|$)', content, re.MULTILINE)
            for match in quantifiable_matches:
                classification = match.strip()
                classification_clean = classification.replace('🚫', '').replace('✅', '').replace('📝', '').replace('🤔', '').strip()
                if 'Quantifiable' in classification_clean and 'Not' not in classification_clean:
                    quantifiable_count += 1
                total_goals += 1
        
        st.sidebar.metric("Groups", total_groups)
        st.sidebar.metric("Participants", total_participants)
        if total_goals > 0:
            st.sidebar.metric("Total Goals", total_goals)
            st.sidebar.metric("✅ Quantifiable", quantifiable_count)
            st.sidebar.metric("❌ Not Quantifiable", total_goals - quantifiable_count)
        
    except FileNotFoundError:
        st.error(f"File '{goals_file}' not found. Please run `python goal_extractor.py` first to generate the goals file.")
    except Exception as e:
        st.error(f"Error loading goals: {e}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
