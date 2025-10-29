"""
Script to save exact data from quantifiable_goals.txt to Supabase.
Preserves all information exactly as it appears in the file.
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def parse_goals_file(filepath: str) -> List[Dict]:
    """Parse the quantifiable_goals.txt file maintaining the exact format"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return []
    
    groups = []
    
    # Find all File: sections - they're followed by separator and then content
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
        
        # Parse participants from content - find all lines starting with ###
        participants = []
        lines = group_content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for participant header
            if line.startswith('### '):
                participant_name = line.replace('###', '').strip()
                
                # Collect all lines until next ### or end
                participant_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('### '):
                    participant_lines.append(lines[i])
                    i += 1
                
                participant_content = '\n'.join(participant_lines)
                
                # Parse participant data
                participant_data = _parse_participant_content(participant_content, participant_name)
                if participant_data:
                    participants.append(participant_data)
                
                continue
            
            i += 1
        
        groups.append({
            'name': group_name,
            'session_date': session_date or None,
            'content': group_content,
            'participants': participants
        })
    
    return groups

def _parse_participant_content(content: str, participant_name: str) -> Optional[Dict]:
    """Parse individual participant data from their section"""
    data = {
        'name': participant_name,
        'discussion': None,
        'commitment': None,
        'classification': None,
        'classification_reason': None,
        'exact_quote': None,
        'timestamp': None,
        'how_to_quantify': None,
        'nudge_message': None
    }
    
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # What They Discussed
        if '**What They Discussed:**' in line or 'What They Discussed:' in line:
            i += 1
            discussion_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('**'):
                discussion_lines.append(lines[i].strip())
                i += 1
            data['discussion'] = ' '.join(discussion_lines)
            continue
        
        # Their Commitment for Next Week
        if '**Their Commitment for Next Week:**' in line or 'Their Commitment for Next Week:' in line:
            i += 1
            commitment_lines = []
            # Skip empty lines immediately after header
            while i < len(lines) and not lines[i].strip():
                i += 1
            # Collect commitment text until next section
            while i < len(lines):
                line_check = lines[i].strip()
                if not line_check:
                    # Empty line - might be separator, check next
                    i += 1
                    if i < len(lines) and lines[i].strip().startswith('**'):
                        break
                    continue
                if line_check.startswith('**'):
                    break
                commitment_lines.append(line_check)
                i += 1
            data['commitment'] = ' '.join(commitment_lines) if commitment_lines else None
            continue
        
        # Classification
        if '**Classification:**' in line or 'Classification:' in line:
            classification_text = ""
            # Check if classification is on the same line after colon
            if ':' in line:
                potential = line.split(':', 1)[1].strip()
                # Only use if it's not just markdown formatting
                if potential and potential not in ['**', '*', '']:
                    classification_text = potential
            
            # If empty or just formatting, get from next non-empty line
            if not classification_text or classification_text in ['**', '*']:
                i += 1  # Move to next line after Classification: header
                # Skip any empty lines
                while i < len(lines) and not lines[i].strip():
                    i += 1
                # Now get the classification from this line
                if i < len(lines):
                    classification_text = lines[i].strip()
                # Don't increment i here - we'll increment at end of loop
            
            # Clean classification - remove emojis and markdown
            if classification_text:
                classification_clean = classification_text.replace('🚫', '').replace('✅', '').replace('📝', '').replace('🤔', '').replace('**', '').replace('*', '').strip()
            else:
                classification_clean = ""
            
            # Map to database values
            if classification_clean:
                if 'Quantifiable' in classification_clean and 'Not' not in classification_clean:
                    data['classification'] = 'quantifiable'
                elif 'Not Quantifiable' in classification_clean:
                    data['classification'] = 'not_quantifiable'
                elif 'No Goal' in classification_clean:
                    data['classification'] = 'no_goal'
                elif 'Decision Pending' in classification_clean:
                    data['classification'] = 'decision_pending'
                else:
                    data['classification'] = 'not_quantifiable'  # Default fallback
            else:
                data['classification'] = 'not_quantifiable'  # Default fallback
            
            # Continue to next line (don't double increment)
            i += 1
            continue
        
        # Why This Classification
        if '**Why This Classification:**' in line or 'Why This Classification:' in line:
            i += 1
            reason_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('**'):
                reason_lines.append(lines[i].strip())
                i += 1
            data['classification_reason'] = ' '.join(reason_lines)
            continue
        
        # Exact Quote
        if '**Exact Quote:**' in line or 'Exact Quote:' in line:
            i += 1
            quote_lines = []
            while i < len(lines):
                quote_line = lines[i].strip()
                if not quote_line:
                    i += 1
                    continue
                if quote_line.startswith('**') and 'Quote' not in quote_line:
                    break
                if quote_line.startswith('**Timestamp:') or quote_line.startswith('**Why') or quote_line.startswith('**How to Make'):
                    break
                if quote_line.startswith('---'):
                    break
                quote_line = quote_line.strip('"').strip("'")
                if quote_line and quote_line.upper() != 'N/A':
                    quote_lines.append(quote_line)
                i += 1
            if quote_lines:
                data['exact_quote'] = ' '.join(quote_lines).strip('"').strip("'")
            continue
        
        # Timestamp
        if '**Timestamp:**' in line or 'Timestamp:' in line:
            if ':' in line:
                timestamp_text = line.split(':', 1)[1].strip()
            else:
                i += 1
                if i < len(lines):
                    timestamp_text = lines[i].strip()
                else:
                    timestamp_text = ""
            data['timestamp'] = timestamp_text.strip('()').strip() if timestamp_text else None
            i += 1
            continue
        
        # How to Make It Quantifiable
        if '**How to Make It Quantifiable:**' in line or 'How to Make It Quantifiable:' in line:
            i += 1
            suggestion_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('**'):
                suggestion_lines.append(lines[i].strip())
                i += 1
            data['how_to_quantify'] = ' '.join(suggestion_lines)
            continue
        
        # Personalized Accountability Nudge Message
        if '**Personalized Accountability Nudge Message:**' in line or 'Personalized Accountability Nudge Message:' in line:
            i += 1
            nudge_lines = []
            # Look for blockquote or regular text
            in_blockquote = False
            while i < len(lines):
                nudge_line = lines[i]
                if '>' in nudge_line:
                    in_blockquote = True
                    # Remove blockquote markers
                    nudge_line = re.sub(r'^>\s*', '', nudge_line.strip())
                    if nudge_line:
                        nudge_lines.append(nudge_line)
                elif in_blockquote and nudge_line.strip() and not nudge_line.strip().startswith('**'):
                    nudge_lines.append(nudge_line.strip())
                elif nudge_line.strip().startswith('**') or nudge_line.strip().startswith('---'):
                    break
                elif not in_blockquote and nudge_line.strip() and not nudge_line.strip().startswith('**'):
                    nudge_lines.append(nudge_line.strip())
                
                i += 1
                if i < len(lines) and lines[i].strip().startswith('---'):
                    break
            
            if nudge_lines:
                data['nudge_message'] = '\n'.join(nudge_lines)
            continue
        
        i += 1
    
    # Return data if we have at least a participant name and some content
    # Even if no commitment, we want to save participants with "No Goal"
    if data['name'] and (data['commitment'] or data['discussion'] or data['classification']):
        return data
    
    return None

def save_to_supabase(groups: List[Dict], organization_id: str):
    """Save parsed groups to Supabase"""
    supabase: Client = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_KEY')
    )
    
    total_commitments = 0
    
    for group in groups:
        group_name = group['name']
        session_date_str = group.get('session_date')
        
        # Parse session date
        session_date = None
        if session_date_str:
            try:
                session_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
            except:
                try:
                    # Try other date formats
                    session_date = datetime.strptime(session_date_str, '%m/%d/%Y').date()
                except:
                    pass
        
        # Create or find transcript session
        filename = f"{group_name} - {session_date_str or 'Unknown'}"
        
        # Check if session already exists
        existing_session = supabase.schema('peer_progress').table('transcript_sessions').select('*').eq(
            'filename', filename
        ).eq('group_name', group_name).execute()
        
        if existing_session.data:
            session_id = existing_session.data[0]['id']
            print(f"✓ Using existing session: {group_name}")
        else:
            # Create new session
            session_data = {
                'filename': filename,
                'group_name': group_name,
                'session_date': session_date.isoformat() if session_date else None,
                'organization_id': organization_id,
                'raw_transcript': None  # We don't have raw transcript here
            }
            
            result = supabase.schema('peer_progress').table('transcript_sessions').insert(session_data).execute()
            if result.data:
                session_id = result.data[0]['id']
                print(f"✓ Created session: {group_name} ({session_date_str or 'No date'})")
            else:
                print(f"✗ Failed to create session: {group_name}")
                continue
        
        # Save each participant's goal to quantifiable_goals table
        for participant in group['participants']:
            # Save all participants, even if no commitment (store in goal_text)
            commitment_text = participant.get('commitment')
            classification = participant.get('classification')
            
            # If no commitment, use a placeholder or skip
            if not commitment_text or commitment_text == 'No specific commitment made':
                # Still save for tracking purposes, but with "No Goal" text
                goal_text_to_save = "No specific commitment made"
                target_number = 0.0
            else:
                goal_text_to_save = commitment_text
                # Extract target number - try from commitment text
                target_number = 1.0  # Default
                number_match = re.search(r'(\d+(?:\.\d+)?)', commitment_text)
                if number_match:
                    target_number = float(number_match.group(1))
                else:
                    # If quantifiable but no number, default to 1
                    if classification == 'quantifiable':
                        target_number = 1.0
                    else:
                        target_number = 0.0
            
            # Prepare source_details JSONB with ALL the exact information from the file
            source_details = {
                'discussion': participant.get('discussion'),
                'classification': classification,
                'classification_reason': participant.get('classification_reason'),
                'exact_quote': participant.get('exact_quote'),
                'timestamp': participant.get('timestamp'),
                'how_to_quantify': participant.get('how_to_quantify'),
                'nudge_message': participant.get('nudge_message'),
                'source_file': 'quantifiable_goals.txt',
                'full_participant_data': {
                    'discussion': participant.get('discussion'),
                    'commitment': participant.get('commitment'),
                    'classification': classification,
                    'classification_reason': participant.get('classification_reason'),
                    'exact_quote': participant.get('exact_quote'),
                    'timestamp': participant.get('timestamp'),
                    'how_to_quantify': participant.get('how_to_quantify'),
                    'nudge_message': participant.get('nudge_message')
                }
            }
            
            goal_data = {
                'transcript_session_id': session_id,
                'organization_id': organization_id,
                'participant_name': participant['name'],
                'group_name': group_name,
                'call_date': session_date.isoformat() if session_date else None,
                'goal_text': goal_text_to_save,
                'target_number': target_number,
                'source_type': 'ai_extraction',
                'source_details': source_details,
                'member_id': None,  # Will need to match by name later
            }
            
            # Check if goal already exists (by session, participant, and goal text)
            existing = supabase.schema('peer_progress').table('quantifiable_goals').select('*').eq(
                'transcript_session_id', session_id
            ).eq('participant_name', participant['name']).eq('goal_text', goal_text_to_save).execute()
            
            if existing.data:
                # Update existing
                goal_id = existing.data[0]['id']
                result = supabase.schema('peer_progress').table('quantifiable_goals').update(goal_data).eq(
                    'id', goal_id
                ).execute()
                print(f"  ✓ Updated goal for {participant['name']} ({classification})")
            else:
                # Insert new
                result = supabase.schema('peer_progress').table('quantifiable_goals').insert(goal_data).execute()
                if result.data:
                    total_commitments += 1
                    print(f"  ✓ Saved goal for {participant['name']} ({classification})")
                else:
                    print(f"  ✗ Failed to save goal for {participant['name']}")
                    if result:
                        print(f"     Error: {result}")
    
    print(f"\n✅ Complete! Saved {total_commitments} goals to quantifiable_goals table in Supabase.")

def main():
    organization_id = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e'
    goals_file = "quantifiable_goals.txt"
    
    print("📖 Parsing quantifiable_goals.txt...")
    groups = parse_goals_file(goals_file)
    
    if not groups:
        print("❌ No groups found in file.")
        return
    
    print(f"✓ Found {len(groups)} groups with {sum(len(g['participants']) for g in groups)} participants\n")
    
    print("💾 Saving to Supabase...\n")
    save_to_supabase(groups, organization_id)

if __name__ == "__main__":
    main()

