"""
Simple script to extract quantifiable goals from transcripts.
Reads transcripts (excluding Main Room), extracts quantifiable goals using Gemini, saves directly to Supabase.
"""

import os
import re
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict, Optional
from ai_llm_fallback import ai_generate_content
from main import TranscriptProcessor
from supabase import create_client, Client

load_dotenv()

# Available folder URLs for different transcript collections
FOLDER_URLS = {
    'october_2025': "https://drive.google.com/drive/folders/1AdNcUaav5hSYGC_8Slac8h4WVnCq5GX7",
    'folder_1': "https://drive.google.com/drive/folders/1HA53gTQpCpn3Tf46Q16FlTPPEVWTjTKK",
    'folder_2': "https://drive.google.com/drive/folders/1ku7IhbFWsYWDnYf0FJMcqOn2EIOfPnWu",
    'folder_3': "https://drive.google.com/drive/folders/1Cess2d0pndMdBZ9Us16S8vZUSvnWHiUa",
    'folder_4': "https://drive.google.com/drive/folders/1Vq3Wm7Xgqtzj5EdHA2DLPna_pCiqsJKf",
    'folder_5': "https://drive.google.com/drive/folders/1rLxQt6ehsrEdtH87vwqqO0ivJIRRv8xQ",
}

# Load the prompt from goal_extraction.md
def _load_goal_extraction_prompt():
    """Load the full goal extraction prompt from the markdown file"""
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'goal_extraction.md')
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Replace the placeholder with the transcript placeholder for formatting
            return content.replace('[Transcript goes here]', '{transcript}')
    else:
        raise Exception(f"Prompt file not found at {prompt_path}")

PROMPT = _load_goal_extraction_prompt()

def _parse_gemini_response(response_text: str, filename: str, session_date: str) -> Optional[Dict]:
    """Parse Gemini response to extract group and participant data"""
    group_name = filename
    
    # Find all participant sections (lines starting with ###)
    participants = []
    lines = response_text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
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
    
    if participants:
        return {
            'name': group_name,
            'session_date': session_date,
            'participants': participants
        }
    
    return None

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
            while i < len(lines) and not lines[i].strip():
                i += 1
            while i < len(lines):
                line_check = lines[i].strip()
                if not line_check:
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
            if ':' in line:
                potential = line.split(':', 1)[1].strip()
                if potential and potential not in ['**', '*', '']:
                    classification_text = potential
            
            if not classification_text or classification_text in ['**', '*']:
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i < len(lines):
                    classification_text = lines[i].strip()
            
            if classification_text:
                classification_clean = classification_text.replace('🚫', '').replace('✅', '').replace('📝', '').replace('🤔', '').replace('**', '').replace('*', '').strip()
            else:
                classification_clean = ""
            
            if classification_clean:
                clean_lower = classification_clean.lower()
                if clean_lower == 'quantifiable' or (clean_lower.startswith('quantifiable') and 'not' not in clean_lower):
                    data['classification'] = 'quantifiable'
                elif 'not quantifiable' in clean_lower:
                    data['classification'] = 'not_quantifiable'
                elif 'no goal' in clean_lower:
                    data['classification'] = 'no_goal'
                elif 'decision pending' in clean_lower:
                    data['classification'] = 'decision_pending'
                else:
                    if 'quantifiable' in clean_lower and 'not' not in clean_lower:
                        data['classification'] = 'quantifiable'
                    else:
                        data['classification'] = 'not_quantifiable'
            else:
                data['classification'] = 'not_quantifiable'
            
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
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('**'):
                quote_lines.append(lines[i].strip())
                i += 1
            data['exact_quote'] = ' '.join(quote_lines)
            continue
        
        # Timestamp
        if '**Timestamp:**' in line or 'Timestamp:' in line:
            i += 1
            if i < len(lines):
                data['timestamp'] = lines[i].strip()
            i += 1
            continue
        
        # How to Make It Quantifiable
        if '**How to Make It Quantifiable:**' in line or 'How to Make It Quantifiable:' in line:
            i += 1
            how_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('**'):
                how_lines.append(lines[i].strip())
                i += 1
            data['how_to_quantify'] = ' '.join(how_lines)
            continue
        
        # Personalized Accountability Nudge Message
        if '**Personalized Accountability Nudge Message:**' in line or 'Personalized Accountability Nudge Message:' in line:
            i += 1
            nudge_lines = []
            in_blockquote = False
            while i < len(lines):
                nudge_line = lines[i]
                if '>' in nudge_line:
                    in_blockquote = True
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
    
    if data['name'] and (data['commitment'] or data['discussion'] or data['classification']):
        return data
    
    return None

def _save_group_to_supabase(supabase: Client, group_data: Dict, organization_id: str, filename: str, session_date: str) -> int:
    """Save parsed group data to Supabase and return count of goals saved"""
    group_name = group_data['name']
    session_date_str = group_data.get('session_date', session_date)
    
    # Parse session date
    parsed_date = None
    if session_date_str:
        try:
            parsed_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
        except:
            try:
                parsed_date = datetime.strptime(session_date_str, '%m/%d/%Y').date()
            except:
                pass
    
    # Create or find transcript session
    session_filename = f"{group_name} - {session_date_str or 'Unknown'}"
    
    existing_session = supabase.schema('peer_progress').table('transcript_sessions').select('*').eq(
        'filename', session_filename
    ).eq('organization_id', organization_id).execute()
    
    if existing_session.data:
        session_id = existing_session.data[0]['id']
    else:
        session_data = {
            'filename': session_filename,
            'group_name': group_name,
            'session_date': parsed_date.isoformat() if parsed_date else None,
            'organization_id': organization_id,
            'raw_transcript': None
        }
        
        result = supabase.schema('peer_progress').table('transcript_sessions').insert(session_data).execute()
        if result.data:
            session_id = result.data[0]['id']
            print(f"  ✓ Created session: {group_name} (ID: {session_id})")
        else:
            print(f"  ✗ Failed to create session: {group_name}")
            print(f"     Error response: {result}")
            return 0
    
    # Save each participant's goal
    saved_count = 0
    for participant in group_data['participants']:
        commitment_text = participant.get('commitment')
        classification = participant.get('classification')
        
        if not commitment_text or commitment_text == 'No specific commitment made':
            goal_text_to_save = "No specific commitment made"
            target_number = 0.0
        else:
            goal_text_to_save = commitment_text
            target_number = 1.0
            number_match = re.search(r'(\d+(?:\.\d+)?)', commitment_text)
            if number_match:
                target_number = float(number_match.group(1))
            else:
                if classification == 'quantifiable':
                    target_number = 1.0
                else:
                    target_number = 0.0
        
        source_details = {
            'discussion': participant.get('discussion'),
            'classification': classification,
            'classification_reason': participant.get('classification_reason'),
            'exact_quote': participant.get('exact_quote'),
            'timestamp': participant.get('timestamp'),
            'how_to_quantify': participant.get('how_to_quantify'),
            'nudge_message': participant.get('nudge_message'),
            'source': 'direct_extraction',
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
            'call_date': parsed_date.isoformat() if parsed_date else None,
            'goal_text': goal_text_to_save,
            'target_number': target_number,
            'source_type': 'ai_extraction',
            'source_details': source_details,
            'member_id': None,
        }
        
        # Check if goal already exists
        existing = supabase.schema('peer_progress').table('quantifiable_goals').select('*').eq(
            'transcript_session_id', session_id
        ).eq('participant_name', participant['name']).eq('goal_text', goal_text_to_save).execute()
        
        if existing.data:
            goal_id = existing.data[0]['id']
            update_result = supabase.schema('peer_progress').table('quantifiable_goals').update(goal_data).eq(
                'id', goal_id
            ).execute()
            if update_result.data:
                print(f"    ✓ Updated goal for {participant['name']}")
        else:
            result = supabase.schema('peer_progress').table('quantifiable_goals').insert(goal_data).execute()
            if result.data:
                saved_count += 1
                print(f"    ✓ Inserted goal for {participant['name']}: {goal_text_to_save[:50]}...")
            else:
                print(f"    ✗ Failed to insert goal for {participant['name']}")
                print(f"       Response: {result}")
    
    return saved_count

def _get_files_recursively(processor, folder_url, days_back=None):
    """Get all transcript files recursively from a folder and its subfolders"""
    from datetime import datetime, timedelta
    
    folder_id = processor._extract_folder_id(folder_url)
    if not folder_id:
        return []
    
    all_files = []
    folders_to_search = [folder_id]
    searched_folders = set()
    
    file_types = [
        'application/vnd.google-apps.document',
        'application/pdf', 
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    # Build date filter if specified
    date_filter = ""
    if days_back is not None:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        date_filter = f" and modifiedTime > '{cutoff_date.isoformat()}Z'"
    
    while folders_to_search:
        current_folder = folders_to_search.pop(0)
        if current_folder in searched_folders:
            continue
        searched_folders.add(current_folder)
        
        # Search for files in current folder
        for mime_type in file_types:
            try:
                query = f"'{current_folder}' in parents and mimeType='{mime_type}'{date_filter}"
                results = processor.drive_service.files().list(
                    q=query,
                    fields="files(id, name, mimeType, createdTime, modifiedTime)",
                    orderBy="modifiedTime desc"
                ).execute()
                files = results.get('files', [])
                all_files.extend(files)
            except Exception as e:
                print(f"  ⚠️  Error searching folder {current_folder}: {e}")
        
        # Find all subfolders
        try:
            query = f"'{current_folder}' in parents and mimeType='application/vnd.google-apps.folder'"
            results = processor.drive_service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            subfolders = results.get('files', [])
            for subfolder in subfolders:
                if subfolder['id'] not in searched_folders:
                    folders_to_search.append(subfolder['id'])
                    print(f"  📂 Found subfolder: {subfolder['name']}")
        except Exception as e:
            print(f"  ⚠️  Error finding subfolders: {e}")
    
    return all_files

def extract_goals_for_all_transcripts(folder_url=None, folder_key=None, days_back=None, multiple_folders=None, recursive=True):
    """
    Extract quantifiable goals from all transcripts and save to file.
    
    Args:
        folder_url: Direct folder URL to use
        folder_key: Key from FOLDER_URLS dict (e.g., 'october_2025')
        days_back: Number of days to look back for transcripts (None = no date filter)
        multiple_folders: List of folder URLs or folder_keys to process (combines results)
        recursive: If True, search subfolders recursively (default: True)
    """
    
    # Use existing processor for Google Drive access
    processor = TranscriptProcessor(organization_id='f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e')
    
    # Determine which folders to process
    folders_to_process = []
    
    if multiple_folders:
        # Process multiple folders
        for folder in multiple_folders:
            if folder in FOLDER_URLS:
                folders_to_process.append(FOLDER_URLS[folder])
            elif folder.startswith('http'):
                folders_to_process.append(folder)
            else:
                print(f"⚠️  Unknown folder key: {folder}, skipping")
    elif folder_key and folder_key in FOLDER_URLS:
        folders_to_process = [FOLDER_URLS[folder_key]]
    elif folder_url:
        folders_to_process = [folder_url]
    else:
        # Default to October 2025 folder
        folders_to_process = [FOLDER_URLS['october_2025']]
    
    # Get transcripts from all folders
    print(f"Getting transcripts from {len(folders_to_process)} folder(s)...")
    all_files = []
    
    for folder_url in folders_to_process:
        print(f"\n📁 Processing folder: {folder_url}")
        
        # If recursive, we need to get all files from subfolders
        if recursive:
            files = _get_files_recursively(processor, folder_url, days_back)
        else:
            files = processor.get_recent_transcripts(folder_url=folder_url, days_back=days_back)
        
        files = [f for f in files if 'Main Room' not in f.get('name', '')]
        print(f"  Found {len(files)} transcripts (excluding Main Room)")
        all_files.extend(files)
    
    # Remove duplicates based on file ID
    seen_ids = set()
    unique_files = []
    for file in all_files:
        if file['id'] not in seen_ids:
            seen_ids.add(file['id'])
            unique_files.append(file)
    
    files = unique_files
    print(f"\n📊 Total unique transcripts: {len(files)}\n")
    
    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
        return
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        # Test connection
        test_result = supabase.schema('peer_progress').table('transcript_sessions').select('id').limit(1).execute()
        print("✓ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return
    
    organization_id = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e'
    total_goals_saved = 0
    
    for file in files:
        filename = file['name']
        print(f"Processing: {filename}")
        
        try:
            # Read transcript
            content = processor.download_and_read_file(
                file['id'], 
                filename, 
                file['mimeType']
            )
            
            if not content.strip():
                continue
            
            # Extract group info from filename to get date
            group_info = processor.extract_group_info_from_filename(filename)
            
            # Use Google Drive modification date as session date
            modified_time = file.get('modifiedTime', '')
            if modified_time:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                    session_date = dt.strftime('%Y-%m-%d')
                except:
                    session_date = group_info.get('session_date', 'Unknown')
            else:
                session_date = group_info.get('session_date', 'Unknown')
            
            # Extract goals with LLM (Gemini preferred, fallback to ChatGPT)
            gemini_output = ai_generate_content(PROMPT.format(transcript=content))
            
            # Parse the Gemini output to extract group and participants
            group_data = _parse_gemini_response(gemini_output, filename, session_date)
            
            if group_data and group_data.get('participants'):
                # Save to Supabase
                saved_count = _save_group_to_supabase(supabase, group_data, organization_id, filename, session_date)
                total_goals_saved += saved_count
                print(f"  ✓ Saved {saved_count} goals to Supabase")
                if saved_count == 0:
                    print(f"     ⚠️  Warning: No goals were saved (might be duplicates or errors)")
            else:
                print(f"  ⚠️  No participants found in response")
                if group_data:
                    print(f"     Participants in group_data: {len(group_data.get('participants', []))}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✅ Complete! Saved {total_goals_saved} goals to Supabase")

if __name__ == "__main__":
    # You can use:
    # - folder_url: Direct URL
    # - folder_key: Key from FOLDER_URLS (e.g., 'october_2025')
    # - multiple_folders: List of folder keys or URLs to process together
    
    # Example: Process October 2025 folder (recursively searches all subfolders)
    extract_goals_for_all_transcripts(
        folder_key='october_2025',
        days_back=None,  # None = no date filter, gets all files
        recursive=True   # Search subfolders recursively
    )
    
    # Example: Process multiple folders
    # extract_goals_for_all_transcripts(
    #     multiple_folders=['october_2025', 'folder_1'],
    #     days_back=30
    # )
