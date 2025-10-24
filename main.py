import os
import re
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import PyPDF2
from docx import Document
import prompts

load_dotenv()

class TranscriptProcessor:
    def __init__(self, organization_id: str):
        self.supabase: Client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        self.organization_id = organization_id
        
        # Initialize Google AI
        genai.configure(api_key=os.getenv('GOOGLE_AI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Initialize Google Drive service
        self.drive_service = self._initialize_google_drive()
        
        # Your existing prompts
        self.EXTRACT_COMMITMENTS = prompts.EXTRACT_COMMITMENTS
        self.CLASSIFY_COMMITMENTS = prompts.CLASSIFY_COMMITMENTS
        self.EXTRACT_QUANTIFIABLE_GOALS = prompts.EXTRACT_QUANTIFIABLE_GOALS
        self.MARKETING_ACTIVITY_EXTRACTION = prompts.MARKETING_ACTIVITY_EXTRACTION
        self.PIPELINE_OUTCOME_EXTRACTION = prompts.PIPELINE_OUTCOME_EXTRACTION
        self.CHALLENGE_STRATEGY_EXTRACTION = prompts.CHALLENGE_STRATEGY_EXTRACTION
        self.STUCK_SIGNAL_EXTRACTION = prompts.STUCK_SIGNAL_EXTRACTION
        self.HELP_OFFER_EXTRACTION = prompts.HELP_OFFER_EXTRACTION
        self.SENTIMENT_ANALYSIS = prompts.SENTIMENT_ANALYSIS
        self.GENERATE_NUDGES = prompts.GENERATE_NUDGES
        
        # Community posting configuration
        self.community_config = self._load_community_config()
    
    def _initialize_google_drive(self):
        try:
            service_account_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
            
            if not service_account_info:
                service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
                if service_account_file and os.path.exists(service_account_file):
                    with open(service_account_file, 'r') as f:
                        service_account_info = json.load(f)
            
            if not service_account_info:
                raise Exception("Google Service Account credentials not found")
            
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            return build('drive', 'v3', credentials=credentials)
            
        except Exception as e:
            print(f"Error initializing Google Drive: {e}")
            return None
    
    def get_all_transcript_files(self, folder_url: str = None, days_back: int = 30) -> List[Dict]:
        """Get all transcript files from any folder, regardless of structure"""
        try:
            folder_id = self._extract_folder_id(folder_url or os.getenv('GOOGLE_DRIVE_FOLDER_URL'))
            if not folder_id:
                raise Exception("Could not extract folder ID from URL")
            
            # Search for all transcript files directly
            file_types = [
                'application/vnd.google-apps.document',
                'application/pdf', 
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]
            
            all_files = []
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for mime_type in file_types:
                try:
                    # Search for files modified in the last N days
                    query = f"'{folder_id}' in parents and mimeType='{mime_type}' and modifiedTime > '{cutoff_date.isoformat()}Z'"
                    results = self.drive_service.files().list(
                        q=query,
                        fields="files(id, name, mimeType, createdTime, modifiedTime)",
                        orderBy="modifiedTime desc"
                    ).execute()
                    
                    files = results.get('files', [])
                    if files:
                        print(f"Found {len(files)} recent {mime_type.split('/')[-1]} files")
                        all_files.extend(files)
                        
                        # Show file names for debugging
                        for file in files[:5]:  # Show first 5 files
                            print(f"  - {file['name']} (modified: {file.get('modifiedTime', 'unknown')})")
                        if len(files) > 5:
                            print(f"  ... and {len(files) - 5} more files")
                            
                except Exception as e:
                    print(f"Error searching for {mime_type}: {e}")
                    continue
            
            print(f"Total found {len(all_files)} recent transcript files")
            return all_files
            
        except Exception as e:
            print(f"Error getting all transcript files: {e}")
            return []
    
    def get_recent_transcripts(self, folder_url: str = None, days_back: int = 7) -> List[Dict]:
        """Get recent transcripts from the last N days"""
        return self.get_all_transcript_files(folder_url, days_back)
    
    def get_october_transcripts(self, folder_url: str = None) -> List[Dict]:
        """Legacy method - use get_recent_transcripts instead"""
        return self.get_recent_transcripts(folder_url, days_back=30)
    
    def _extract_folder_id(self, folder_url: str) -> str:
        if not folder_url:
            return None
        
        patterns = [
            r'https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)',
            r'https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)',
            r'([a-zA-Z0-9_-]{25,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, folder_url)
            if match:
                return match.group(1)
        
        return folder_url
    
    def download_and_read_file(self, file_id: str, file_name: str, mime_type: str) -> str:
        try:
            if mime_type == 'application/vnd.google-apps.document':
                return self._export_google_doc(file_id)
            elif mime_type == 'application/pdf':
                return self._download_and_read_pdf(file_id, file_name)
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                return self._download_and_read_docx(file_id, file_name)
            else:
                print(f"Unsupported file type: {mime_type}")
                return ""
                
        except Exception as e:
            print(f"Error reading file {file_name}: {e}")
            return ""
    
    def _export_google_doc(self, file_id: str) -> str:
        try:
            request = self.drive_service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            content = request.execute()
            return content.decode('utf-8') if isinstance(content, bytes) else content
        except Exception as e:
            print(f"Error exporting Google Doc: {e}")
            return ""
    
    def _download_and_read_pdf(self, file_id: str, file_name: str) -> str:
        """Download and read PDF file"""
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            
            # Read PDF content
            pdf_reader = PyPDF2.PdfReader(file_content)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text
            
        except Exception as e:
            print(f"Error reading PDF {file_name}: {e}")
            return ""
    
    def _download_and_read_docx(self, file_id: str, file_name: str) -> str:
        """Download and read DOCX file"""
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            
            # Read DOCX content
            doc = Document(file_content)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text
            
        except Exception as e:
            print(f"Error reading DOCX {file_name}: {e}")
            return ""
    
    def extract_group_info_from_filename(self, filename: str) -> Dict:
        """Extract group name and date from filename"""
        try:
            # Enhanced patterns for transcript filenames
            patterns = [
                r'Group\s*(\d+\.\d+)[^.]*\.',  # Group 1.1, Group 1.2, etc.
                r'(\d+\.\d+)[^.]*\.',          # 1.1, 1.2, etc.
                r'Group\s*([^.]*)\.',          # Group name before extension
                r'Main\s*Room\s*(\d+)',        # Main Room 1, Main Room 2
                r'Room\s*(\d+)',               # Room 1, Room 2
                r'(\w+)\s*(\d+\.\d+)',        # Any word followed by number.number
            ]
            
            group_name = "Main Session"  # Better default than "Unknown Group"
            
            for pattern in patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    if 'Main Room' in filename or 'Main Room' in pattern:
                        group_name = f"Main Room {match.group(1)}"
                    elif 'Room' in filename and 'Main' not in filename:
                        group_name = f"Room {match.group(1)}"
                    elif len(match.groups()) >= 2:
                        # Handle patterns with multiple groups
                        group_name = f"Group {match.group(2)}"
                    else:
                        group_name = f"Group {match.group(1)}"
                    break
            
            # If still no match, try to extract any meaningful identifier
            if group_name == "Main Session":
                # Look for any number pattern
                number_match = re.search(r'(\d+)', filename)
                if number_match:
                    group_name = f"Session {number_match.group(1)}"
                else:
                    # Extract first meaningful word
                    word_match = re.search(r'([A-Za-z]+)', filename)
                    if word_match:
                        group_name = f"{word_match.group(1).title()} Session"
            
            print(f"📝 Extracted group name: '{group_name}' from filename: '{filename}'")
            
            # Extract date from filename (including folder context)
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY
                r'(\d{8})',              # YYYYMMDD
                r'(\d{1,2})[_-](\d{1,2})[_-](\d{4})',  # M_D_YYYY or M-D-YYYY
                r'(October|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep)\s+(\d{1,2}),?\s+(\d{4})',  # "October 22, 2025"
            ]
            
            session_date = None
            for pattern in date_patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 1:
                        date_str = match.group(1)
                        if len(date_str) == 8:  # YYYYMMDD
                            session_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        else:
                            session_date = date_str
                    elif len(match.groups()) == 3:
                        if pattern == r'(October|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep)\s+(\d{1,2}),?\s+(\d{4})':
                            # Handle month name format: "October 22, 2025"
                            month_name, day, year = match.groups()
                            month_map = {
                                'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
                                'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
                                'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
                                'august': '08', 'aug': '08', 'september': '09', 'sep': '09',
                                'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
                                'december': '12', 'dec': '12'
                            }
                            month_num = month_map.get(month_name.lower(), '10')
                            session_date = f"{year}-{month_num}-{day.zfill(2)}"
                        else:
                            # Handle numeric format: M_D_YYYY
                            month, day, year = match.groups()
                            session_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    break
            
            # If no date found, use current date
            if not session_date:
                session_date = datetime.now().strftime('%Y-%m-%d')
            
            return {
                'group_name': group_name,
                'session_date': session_date
            }
            
        except Exception as e:
            print(f"Error extracting group info from {filename}: {e}")
            return {'group_name': 'Unknown Group', 'session_date': '2024-10-15'}
    
    def process_recent_transcripts(self, folder_url: str = None, days_back: int = 7) -> Dict:
        """Process recent transcripts from the last N days"""
        try:
            transcripts = self.get_recent_transcripts(folder_url, days_back)
            results = {
                'processed': 0,
                'failed': 0,
                'details': []
            }
            
            for transcript_file in transcripts:
                print(f"Processing: {transcript_file['name']}")
                
                try:
                    # Read file content
                    content = self.download_and_read_file(
                        transcript_file['id'],
                        transcript_file['name'],
                        transcript_file['mimeType']
                    )
                    
                    if not content.strip():
                        print(f"Skipping empty file: {transcript_file['name']}")
                        continue
                    
                    # Extract group info from filename
                    group_info = self.extract_group_info_from_filename(transcript_file['name'])
                    
                    # Use Google Drive modification date as session date
                    modified_time = transcript_file.get('modifiedTime', '')
                    if modified_time:
                        try:
                            # Parse ISO format: 2025-10-22T23:16:31.303Z
                            from datetime import datetime
                            dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                            session_date = dt.strftime('%Y-%m-%d')
                            print(f"📅 Using Google Drive modification date: {session_date}")
                        except Exception as e:
                            print(f"⚠️ Could not parse modification date {modified_time}: {e}")
                            session_date = group_info['session_date']
                    else:
                        session_date = group_info['session_date']
                    
                    # Process transcript
                    success = self.process_transcript(
                        transcript_text=content,
                        filename=transcript_file['name'],
                        group_name=group_info['group_name'],
                        session_date=session_date
                    )
                    
                    if success:
                        results['processed'] += 1
                        results['details'].append({
                            'filename': transcript_file['name'],
                            'status': 'success',
                            'group': group_info['group_name'],
                            'date': group_info['session_date']
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'filename': transcript_file['name'],
                            'status': 'failed',
                            'group': group_info['group_name'],
                            'date': group_info['session_date']
                        })
                    
                    print(f"Completed: {transcript_file['name']} - {'Success' if success else 'Failed'}")
                    
                except Exception as e:
                    print(f"Error processing {transcript_file['name']}: {e}")
                    results['failed'] += 1
                    results['details'].append({
                        'filename': transcript_file['name'],
                        'status': 'error',
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            print(f"Error processing October transcripts: {e}")
            return {'processed': 0, 'failed': 0, 'details': [], 'error': str(e)}

    # The following methods are the same as in the previous implementation
    # but included for completeness
    
    def create_transcript_session(self, filename: str, group_name: str, session_date: str = None, raw_transcript: str = None) -> Dict:
        """Create a new transcript session record"""
        existing_session = self.supabase.schema('peer_progress').table('transcript_sessions').select('*').eq(
            'filename', filename
        ).eq('group_name', group_name).execute()
        
        if existing_session.data:
            return existing_session.data[0]
        
        session_data = {
            'filename': filename,
            'group_name': group_name,
            'session_date': session_date or datetime.now().date().isoformat(),
            'raw_transcript': raw_transcript,
            'analysis_date': datetime.now().isoformat(),
            'organization_id': self.organization_id
        }
        
        result = self.supabase.schema('peer_progress').table('transcript_sessions').insert(session_data).execute()
        return result.data[0] if result.data else None
    
    def get_member_by_name(self, name: str) -> Dict:
        """Find member by name"""
        result = self.supabase.schema('peer_progress').table('members').select('*').eq('full_name', name).execute()
        return result.data[0] if result.data else None
    
    def process_transcript(self, transcript_text: str, filename: str, group_name: str, session_date: str = None) -> bool:
        """Main method to process a transcript and store results"""
        try:
            # 1. Create transcript session
            session = self.create_transcript_session(filename, group_name, session_date, transcript_text)
            if not session:
                raise Exception("Failed to create transcript session")
            
            # 2. Extract commitments using AI
            commitments = self.extract_commitments_from_transcript(transcript_text, group_name, session_date)
            
            # 3. Extract quantifiable goals using AI
            quantifiable_goals = self.extract_quantifiable_goals_from_transcript(transcript_text, group_name, session_date)
            
            # 4. Classify commitments
            classified_commitments = self.classify_commitments(commitments)
            
            # 5. Generate nudge messages
            final_commitments = self.generate_nudge_messages(classified_commitments)
            
            # 6. Store analysis results (simplified for existing schema)
            analysis_data = {
                'transcript_session_id': session['id'],
                'organization_id': self.organization_id,
                'processing_status': 'completed'
            }
            
            try:
                analysis_result = self.supabase.schema('peer_progress').table('transcript_analysis').insert(analysis_data).execute()
            except Exception as e:
                print(f"Warning: Could not insert analysis data: {e}")
                # Continue processing even if analysis table insert fails
            
            # 7. Store individual commitments
            for commitment in final_commitments:
                try:
                    self.store_individual_commitment(commitment, session['id'])
                except Exception as e:
                    print(f"Warning: Could not store commitment: {e}")
                    # Continue processing other commitments
            
            # 8. Store individual quantifiable goals
            for goal_data in quantifiable_goals:
                try:
                    self.store_quantifiable_goals(goal_data, session['id'])
                except Exception as e:
                    print(f"Warning: Could not store quantifiable goal: {e}")
                    # Continue processing other goals
            
            # 9. Vague goals are now automatically detected by database trigger when commitments are stored
            total_quantifiable = sum(len(g.get('quantifiable_goals', [])) for g in quantifiable_goals)
            print(f"✅ Successfully processed {filename} with {len(final_commitments)} participants and {total_quantifiable} quantifiable goals")
            print(f"📝 Vague goals will be automatically detected and scheduled for follow-up by database trigger")
            
            # 10. Track attendance from transcript participants
            participants = [c['participant_name'] for c in final_commitments]
            self.track_attendance_from_transcript(session['id'], group_name, session_date, participants)
            
            # 11. Post goals to community platform
            self.post_goals_to_community(session['id'], group_name, session_date)
            
            # 12. Assess risk for all participants
            for participant in participants:
                member = self.get_member_by_name(participant)
                if member:
                    self.assess_member_risk(member['id'])
                else:
                    print(f"Warning: Could not find member {participant} for risk assessment")
            
            # 13. Extract marketing activities and pipeline outcomes
            marketing_activities = self.extract_marketing_activities(transcript_text, session['id'], group_name, session_date)
            pipeline_outcomes = self.extract_pipeline_outcomes(transcript_text, session['id'], group_name, session_date)
            
            # 14. Extract challenges and strategies
            challenges_strategies = self.extract_challenges_and_strategies(transcript_text, session['id'], group_name, session_date)
            
            # 15. Extract stuck signals and help offers
            stuck_signals = self.extract_stuck_signals(transcript_text, session['id'], group_name, session_date)
            help_offers = self.extract_help_offers(transcript_text, session['id'], group_name, session_date)
            
            # 16. Analyze sentiment and group health
            try:
                sentiment_analysis = self.analyze_sentiment(transcript_text, session['id'], group_name, session_date)
            except Exception as e:
                print(f"Error analyzing sentiment: {e}")
                sentiment_analysis = None
            
            # 17. Log attendance changes for participants
            for participant in participants:
                self.log_member_change(
                    member_id=participant,
                    change_type='attendance_update',
                    change_category='attendance',
                    new_value={'group': group_name, 'session_date': session_date, 'status': 'present'},
                    change_description=f"Attended {group_name} call on {session_date}",
                    change_source='automatic'
                )
            return True
            
        except Exception as e:
            if 'session' in locals():
                error_data = {
                    'transcript_session_id': session['id'],
                    'organization_id': self.organization_id,
                    'processing_status': 'failed',
                    'error_message': str(e)
                }
                self.supabase.schema('peer_progress').table('transcript_analysis').insert(error_data).execute()
            
            print(f"Error processing transcript: {e}")
            return False
    
    def extract_commitments_from_transcript(self, transcript_text: str, group_name: str, call_date: str = None) -> List[Dict]:
        """Extract commitments using AI"""
        try:
            prompt = self.EXTRACT_COMMITMENTS.format(transcript=transcript_text)
            response = self.model.generate_content(prompt)
            return self._parse_extracted_commitments(response.text, group_name, call_date)
        except Exception as e:
            print(f"Error extracting commitments: {e}")
            return []
    
    def extract_quantifiable_goals_from_transcript(self, transcript_text: str, group_name: str, call_date: str = None) -> List[Dict]:
        """Extract quantifiable goals using AI"""
        try:
            prompt = self.EXTRACT_QUANTIFIABLE_GOALS.format(transcript=transcript_text)
            response = self.model.generate_content(prompt)
            return self._parse_quantifiable_goals(response.text, group_name, call_date)
        except Exception as e:
            print(f"Error extracting quantifiable goals: {e}")
            return []
    
    def _parse_extracted_commitments(self, ai_response: str, group_name: str, call_date: str) -> List[Dict]:
        """Parse AI response into structured data"""
        commitments = []
        current_commitment = {}
        
        lines = ai_response.split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith('### '):
                if current_commitment:
                    commitments.append(current_commitment)
                current_commitment = {
                    'participant_name': line.replace('### ', '').strip(),
                    'group_name': group_name,
                    'call_date': call_date or datetime.now().strftime('%Y-%m-%d'),
                    'organization_id': self.organization_id
                }
            
            elif line.startswith('**What They Discussed:**'):
                current_commitment['discussion_summary'] = self._get_next_content(lines, lines.index(line))
            
            elif line.startswith('**Their Commitment for Next Week:**'):
                current_commitment['commitment_text'] = self._get_next_content(lines, lines.index(line))
            
            elif line.startswith('**Exact Quote:**'):
                current_commitment['exact_quote'] = self._get_next_content(lines, lines.index(line))
            
            elif line.startswith('**Timestamp:**'):
                current_commitment['timestamp_in_transcript'] = self._get_next_content(lines, lines.index(line))
        
        if current_commitment:
            commitments.append(current_commitment)
        
        return commitments
    
    def _get_next_content(self, lines: List[str], current_index: int) -> str:
        """Extract content following a header"""
        content = []
        i = current_index + 1
        while i < len(lines) and lines[i] and not lines[i].startswith('**') and not lines[i].startswith('###') and lines[i] != '---':
            if lines[i].strip():
                content.append(lines[i].strip())
            i += 1
        return ' '.join(content)
    
    def _parse_quantifiable_goals(self, ai_response: str, group_name: str, call_date: str) -> List[Dict]:
        """Parse AI response for both quantifiable and non-quantifiable goals"""
        goals = []
        current_participant = None
        current_quantifiable_goals = []
        current_non_quantifiable_goals = []
        in_quantifiable_section = False
        in_non_quantifiable_section = False
        
        lines = ai_response.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # New participant section
            if line.startswith('### '):
                if current_participant and (current_quantifiable_goals or current_non_quantifiable_goals):
                    goals.append({
                        'participant_name': current_participant,
                        'group_name': group_name,
                        'call_date': call_date or datetime.now().strftime('%Y-%m-%d'),
                        'organization_id': self.organization_id,
                        'quantifiable_goals': current_quantifiable_goals,
                        'non_quantifiable_goals': current_non_quantifiable_goals
                    })
                
                current_participant = line.replace('### ', '').strip()
                current_quantifiable_goals = []
                current_non_quantifiable_goals = []
                in_quantifiable_section = False
                in_non_quantifiable_section = False
            
            # Check for section headers
            elif line.startswith('**Quantifiable Goals:**'):
                in_quantifiable_section = True
                in_non_quantifiable_section = False
            elif line.startswith('**Non-Quantifiable Goals:**'):
                in_quantifiable_section = False
                in_non_quantifiable_section = True
            
            # Extract goal text
            elif line.startswith('[Goal') and ']' in line:
                # Find the last closing bracket
                bracket_idx = line.rfind(']')
                
                if bracket_idx != -1:
                    # Extract everything between the first : and the last ]
                    colon_idx = line.find(':', line.find('[Goal'))
                    if colon_idx != -1:
                        goal_text = line[colon_idx + 1:bracket_idx].strip()
                        
                        # Clean up any leading colons or quotes
                        if goal_text.startswith(':'):
                            goal_text = goal_text[1:].strip()
                        if goal_text.startswith('"') and goal_text.endswith('"'):
                            goal_text = goal_text[1:-1].strip()
                        
                        # Skip placeholder text
                        if goal_text and goal_text not in ["No specific numbers mentioned", "No specific commitments mentioned", "No quantifiable goals mentioned", "No non-quantifiable goals mentioned"] and not goal_text.startswith("[If none:"):
                            
                            # Extract number from goal text if available
                            number_match = re.search(r'(\d+(?:\.\d+)?)', goal_text)
                            if number_match:
                                target_number = float(number_match.group(1))
                            else:
                                target_number = 1.0
                            
                            goal_data = {
                                'goal_text': goal_text,
                                'target_number': target_number,
                                'goal_unit': 'units'  # Default unit
                            }
                            
                            # Add to appropriate section
                            if in_quantifiable_section:
                                current_quantifiable_goals.append(goal_data)
                            elif in_non_quantifiable_section:
                                current_non_quantifiable_goals.append(goal_data)
        
        # Handle the last participant
        if current_participant and (current_quantifiable_goals or current_non_quantifiable_goals):
            goals.append({
                'participant_name': current_participant,
                'group_name': group_name,
                'call_date': call_date or datetime.now().strftime('%Y-%m-%d'),
                'organization_id': self.organization_id,
                'quantifiable_goals': current_quantifiable_goals,
                'non_quantifiable_goals': current_non_quantifiable_goals
            })
        
        return goals
    
    def classify_commitments(self, commitments: List[Dict]) -> List[Dict]:
        """Classify commitments by quantifiability"""
        try:
            commitments_text = "\n".join([
                f"### {c['participant_name']}\n"
                f"**Commitment:** {c.get('commitment_text', 'N/A')}\n"
                for c in commitments
            ])
            
            prompt = self.CLASSIFY_COMMITMENTS.format(commitments=commitments_text)
            response = self.model.generate_content(prompt)
            
            return self._parse_classified_commitments(commitments, response.text)
        except Exception as e:
            print(f"Error classifying commitments: {e}")
            return commitments
    
    def _parse_classified_commitments(self, original_commitments: List[Dict], ai_response: str) -> List[Dict]:
        """Parse classification results"""
        for commitment in original_commitments:
            commitment_text = commitment.get('commitment_text', '')
            numbers = re.findall(r'\b\d+\b', commitment_text)
            
            if numbers:
                commitment['classification'] = 'quantifiable'
                commitment['classification_reason'] = f'Contains specific numbers: {", ".join(numbers)}'
                commitment['target_number'] = int(numbers[0])
                
                if 'post' in commitment_text.lower():
                    commitment['goal_unit'] = 'posts'
                elif 'call' in commitment_text.lower():
                    commitment['goal_unit'] = 'calls'
                elif 'message' in commitment_text.lower():
                    commitment['goal_unit'] = 'messages'
                elif 'draft' in commitment_text.lower():
                    commitment['goal_unit'] = 'drafts'
                else:
                    commitment['goal_unit'] = 'tasks'
            else:
                commitment['classification'] = 'not_quantifiable'
                commitment['classification_reason'] = 'No specific numbers found in commitment'
                commitment['quantification_suggestion'] = 'Add specific numbers and deadlines to make goal measurable'
        
        return original_commitments
    
    def generate_nudge_messages(self, commitments: List[Dict]) -> List[Dict]:
        """Generate nudge messages for non-quantifiable goals"""
        try:
            classified_text = "\n".join([
                f"### {c['participant_name']}\n"
                f"Classification: {c.get('classification', 'not_quantifiable')}\n"
                f"Commitment: {c.get('commitment_text', 'N/A')}\n"
                for c in commitments if c.get('classification') in ['not_quantifiable', 'no_goal']
            ])
            
            if not classified_text.strip():
                return commitments
            
            prompt = self.GENERATE_NUDGES.format(classified_commitments=classified_text)
            response = self.model.generate_content(prompt)
            
            return self._parse_nudge_messages(commitments, response.text)
        except Exception as e:
            print(f"Error generating nudge messages: {e}")
            return commitments
    
    def _parse_nudge_messages(self, commitments: List[Dict], ai_response: str) -> List[Dict]:
        """Parse nudge messages from AI response"""
        nudge_sections = ai_response.split('### ')
        
        for section in nudge_sections[1:]:
            lines = section.split('\n')
            participant_name = lines[0].strip()
            
            for commitment in commitments:
                if commitment['participant_name'] == participant_name:
                    nudge_content = []
                    in_nudge_section = False
                    
                    for line in lines:
                        if 'Personalized Accountability Nudge Message:' in line:
                            in_nudge_section = True
                            continue
                        if in_nudge_section and line.strip() and not line.startswith('---'):
                            nudge_content.append(line.strip())
                    
                    commitment['nudge_message'] = '\n'.join(nudge_content) if nudge_content else "Let's make your goal more specific with numbers and deadlines!"
                    break
        
        return commitments
    
    def store_individual_commitment(self, commitment: Dict, transcript_session_id: str):
        """Store an individual commitment in the database"""
        try:
            member = self.get_member_by_name(commitment['participant_name'])
            member_id = member['id'] if member else None
            
            target_number = commitment.get('target_number')
            if target_number is not None:
                try:
                    target_number = float(target_number)
                except (ValueError, TypeError):
                    target_number = None
            
            commitment_data = {
                'transcript_session_id': transcript_session_id,
                'member_id': member_id,
                'organization_id': self.organization_id,
                'participant_name': commitment['participant_name'],
                'discussion_summary': commitment.get('discussion_summary'),
                'commitment_text': commitment.get('commitment_text'),
                'exact_quote': commitment.get('exact_quote'),
                'timestamp_in_transcript': commitment.get('timestamp_in_transcript'),
                'classification': commitment.get('classification'),
                'classification_reason': commitment.get('classification_reason'),
                'quantification_suggestion': commitment.get('quantification_suggestion'),
                'nudge_message': commitment.get('nudge_message'),
                'target_number': target_number,
                'goal_unit': commitment.get('goal_unit'),
                'week_start_date': commitment.get('call_date'),
                'deadline_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            }
            
            result = self.supabase.schema('peer_progress').table('commitments').insert(commitment_data).execute()
            
            if commitment.get('classification') == 'quantifiable' and result.data:
                progress_data = {
                    'commitment_id': result.data[0]['id'],
                    'organization_id': self.organization_id,
                    'member_id': member_id,
                    'progress_value': 0,
                    'target_value': commitment.get('target_number', 1),
                    'progress_notes': 'Initial commitment recorded'
                }
                self.supabase.schema('peer_progress').table('goal_progress').insert(progress_data).execute()
            
            return True
            
        except Exception as e:
            print(f"Error storing individual commitment: {e}")
            return False
    
    def store_quantifiable_goals(self, goal_data: Dict, transcript_session_id: str):
        """Store both quantifiable and non-quantifiable goals for a participant"""
        try:
            member = self.get_member_by_name(goal_data['participant_name'])
            member_id = member['id'] if member else None
            
            # Store quantifiable goals
            for goal in goal_data.get('quantifiable_goals', []):
                # Enhanced deduplication check
                existing_goal = self.supabase.schema('peer_progress').table('quantifiable_goals').select('id').eq(
                    'participant_name', goal_data['participant_name']
                ).eq('goal_text', goal.get('goal_text')).eq('call_date', goal_data['call_date']).eq(
                    'group_name', goal_data['group_name']
                ).execute()
                
                if existing_goal.data:
                    print(f"⚠️ Skipping duplicate quantifiable goal for {goal_data['participant_name']}: {goal.get('goal_text', '')[:50]}...")
                    continue
                
                # Convert target_number to float if it exists
                target_number = goal.get('target_number')
                if target_number is not None:
                    try:
                        target_number = float(target_number)
                    except (ValueError, TypeError):
                        target_number = 1.0  # Default fallback
                
                goal_record = {
                       'transcript_session_id': transcript_session_id,
                       'member_id': member_id,
                       'organization_id': self.organization_id,
                       'participant_name': goal_data['participant_name'],
                       'group_name': goal_data['group_name'],
                       'call_date': goal_data['call_date'],
                       'goal_text': goal.get('goal_text'),
                       'target_number': target_number
                }
                   
                # Add source tracking columns if they exist
                try:
                    goal_record.update({
                        'source_type': 'ai_extraction',
                        'source_details': {
                            'extraction_method': 'ai_transcript_analysis',
                            'transcript_session_id': transcript_session_id,
                            'confidence_score': goal.get('confidence_score', 0.8)
                        },
                        'updated_by': 'ai_system'
                    })
                except:
                    pass  # Columns don't exist yet, skip source tracking
                
                result = self.supabase.schema('peer_progress').table('quantifiable_goals').insert(goal_record).execute()
                
                if result.data:
                    progress_data = {
                        'quantifiable_goal_id': result.data[0]['id'],
                        'organization_id': self.organization_id,
                        'member_id': member_id,
                        'current_value': 0,
                        'target_value': goal.get('target_number'),
                        'status': 'not_started',
                        'source_type': 'ai_extraction',
                        'source_details': {
                            'initial_setup': True,
                            'transcript_session_id': transcript_session_id
                        }
                    }
                    self.supabase.schema('peer_progress').table('goal_progress_tracking').insert(progress_data).execute()
            
            # Store non-quantifiable goals
            for goal in goal_data.get('non_quantifiable_goals', []):
                # Enhanced deduplication check
                existing_goal = self.supabase.schema('peer_progress').table('quantifiable_goals').select('id').eq(
                    'participant_name', goal_data['participant_name']
                ).eq('goal_text', goal.get('goal_text')).eq('call_date', goal_data['call_date']).eq(
                    'group_name', goal_data['group_name']
                ).execute()
                
                if existing_goal.data:
                    print(f"⚠️ Skipping duplicate non-quantifiable goal for {goal_data['participant_name']}: {goal.get('goal_text', '')[:50]}...")
                    continue
                
                # Convert target_number to float if it exists
                target_number = goal.get('target_number')
                if target_number is not None:
                    try:
                        target_number = float(target_number)
                    except (ValueError, TypeError):
                        target_number = 1.0  # Default fallback
                
                goal_record = {
                       'transcript_session_id': transcript_session_id,
                       'member_id': member_id,
                       'organization_id': self.organization_id,
                       'participant_name': goal_data['participant_name'],
                       'group_name': goal_data['group_name'],
                       'call_date': goal_data['call_date'],
                       'goal_text': goal.get('goal_text'),
                       'target_number': target_number
                }
                   
                # Add source tracking columns if they exist
                try:
                    goal_record.update({
                        'source_type': 'ai_extraction',
                        'source_details': {
                            'extraction_method': 'ai_transcript_analysis',
                            'transcript_session_id': transcript_session_id,
                            'confidence_score': goal.get('confidence_score', 0.8),
                            'goal_type': 'non_quantifiable'
                        },
                        'updated_by': 'ai_system'
                    })
                except:
                    pass  # Columns don't exist yet, skip source tracking
                
                result = self.supabase.schema('peer_progress').table('quantifiable_goals').insert(goal_record).execute()
                
                if result.data:
                    progress_data = {
                        'goal_id': result.data[0]['id'],
                        'member_id': member_id,
                        'organization_id': self.organization_id,
                        'progress_percentage': 0,
                        'notes': 'Non-quantifiable goal - needs clarification',
                        'updated_by': 'ai_system'
                    }
                    self.supabase.schema('peer_progress').table('goal_progress_tracking').insert(progress_data).execute()
            
            return True
            
        except Exception as e:
            print(f"Error storing quantifiable goals: {e}")
            return False
    
    
    def add_manual_goal(self, goal_data: Dict, updated_by: str) -> bool:
        """Add a manually input goal with human_input source tracking"""
        try:
            member = self.get_member_by_name(goal_data['participant_name'])
            member_id = member['id'] if member else None
            
            goal_record = {
                'member_id': member_id,
                'organization_id': self.organization_id,
                'participant_name': goal_data['participant_name'],
                'group_name': goal_data.get('group_name', 'Manual Input'),
                'call_date': goal_data.get('call_date', datetime.now().strftime('%Y-%m-%d')),
                'goal_text': goal_data['goal_text'],
                'target_number': goal_data['target_number'],
                'source_type': 'human_input',
                'source_details': {
                    'input_method': 'manual_entry',
                    'input_source': 'dashboard',
                    'input_timestamp': datetime.now().isoformat(),
                    'notes': goal_data.get('notes', '')
                },
                'updated_by': updated_by
            }
            
            result = self.supabase.schema('peer_progress').table('quantifiable_goals').insert(goal_record).execute()
            
            if result.data:
                progress_data = {
                    'quantifiable_goal_id': result.data[0]['id'],
                    'organization_id': self.organization_id,
                    'member_id': member_id,
                    'current_value': 0,
                    'target_value': goal_data['target_number'],
                    'status': 'not_started',
                    'source_type': 'human_input',
                    'source_details': {
                        'initial_setup': True,
                        'manual_entry': True,
                        'created_by': updated_by
                    }
                }
                self.supabase.schema('peer_progress').table('goal_progress_tracking').insert(progress_data).execute()
                
                print(f"✅ Added manual goal: {goal_data['participant_name']} - {goal_data['goal_text'][:50]}...")
                return True
            else:
                print(f"❌ Failed to add manual goal")
                return False
                
        except Exception as e:
            print(f"Error adding manual goal: {e}")
            return False

    def send_pending_follow_ups(self):
        """Send scheduled follow-up messages (simple version - just logs for now)"""
        try:
            # Get follow-ups that are due to be sent
            now = datetime.now()
            result = self.supabase.schema('peer_progress').table('participant_follow_ups').select('*').eq('follow_up_status', 'scheduled').lte('scheduled_date', now.isoformat()).execute()
            
            if not result.data:
                print("No pending follow-ups to send")
                return
            
            for follow_up in result.data:
                # For now, just log the message (ready for email/SMS integration)
                print(f"\n📧 FOLLOW-UP MESSAGE FOR {follow_up['participant_name']}:")
                print(f"📅 Scheduled: {follow_up['scheduled_date']}")
                print(f"💬 Message: {follow_up['nudge_message']}")
                print("-" * 50)
                
                # Update status to 'sent' (simulate sending)
                self.supabase.schema('peer_progress').table('participant_follow_ups').update({
                    'follow_up_status': 'sent',
                    'sent_date': now.isoformat()
                }).eq('id', follow_up['id']).execute()
            
            print(f"✅ Processed {len(result.data)} follow-up messages")
            
        except Exception as e:
            print(f"Error sending follow-ups: {e}")
    
    def get_vague_goals_summary(self, organization_id: str = None) -> Dict:
        """Get summary of vague goals and follow-ups"""
        try:
            org_filter = organization_id or self.organization_id
            
            # Get vague goals count
            vague_result = self.supabase.schema('peer_progress').table('vague_goals_detected').select('*', count='exact').eq('organization_id', org_filter).execute()
            
            # Get follow-ups count
            follow_up_result = self.supabase.schema('peer_progress').table('participant_follow_ups').select('*', count='exact').eq('organization_id', org_filter).execute()
            
            # Get pending follow-ups
            pending_result = self.supabase.schema('peer_progress').table('participant_follow_ups').select('*', count='exact').eq('organization_id', org_filter).eq('follow_up_status', 'scheduled').execute()
            
            return {
                'total_vague_goals': vague_result.count,
                'total_follow_ups': follow_up_result.count,
                'pending_follow_ups': pending_result.count,
                'sent_follow_ups': follow_up_result.count - pending_result.count if follow_up_result.count else 0
            }
            
        except Exception as e:
            print(f"Error getting vague goals summary: {e}")
            return {'total_vague_goals': 0, 'total_follow_ups': 0, 'pending_follow_ups': 0, 'sent_follow_ups': 0}
    
    def _load_community_config(self) -> Dict:
        """Load community posting configuration from environment"""
        return {
            'enabled': os.getenv('COMMUNITY_POSTING_ENABLED', 'false').lower() == 'true',
            'platform': os.getenv('COMMUNITY_PLATFORM', 'slack'),  # slack, discord, webhook
            'webhook_url': os.getenv('COMMUNITY_WEBHOOK_URL'),
            'channel': os.getenv('COMMUNITY_CHANNEL', '#goals'),
            'post_quantifiable': os.getenv('COMMUNITY_POST_QUANTIFIABLE', 'true').lower() == 'true',
            'post_vague': os.getenv('COMMUNITY_POST_VAGUE', 'false').lower() == 'true',
            'post_summary': os.getenv('COMMUNITY_POST_SUMMARY', 'true').lower() == 'true'
        }
    
    def post_goals_to_community(self, transcript_session_id: str, group_name: str, session_date: str):
        """Post extracted goals to community platform"""
        if not self.community_config['enabled']:
            print("Community posting is disabled")
            return
        
        try:
            # Get goals from this session
            quantifiable_goals = self._get_quantifiable_goals_for_session(transcript_session_id)
            vague_goals = self._get_vague_goals_for_session(transcript_session_id)
            
            # Create community posts
            posts_created = []
            
            if self.community_config['post_summary']:
                summary_post = self._create_summary_post(group_name, session_date, quantifiable_goals, vague_goals)
                if summary_post:
                    posts_created.append(summary_post)
            
            if self.community_config['post_quantifiable'] and quantifiable_goals:
                quantifiable_post = self._create_quantifiable_goals_post(group_name, quantifiable_goals)
                if quantifiable_post:
                    posts_created.append(quantifiable_post)
            
            if self.community_config['post_vague'] and vague_goals:
                vague_post = self._create_vague_goals_post(group_name, vague_goals)
                if vague_post:
                    posts_created.append(vague_post)
            
            # Send posts to community
            for post in posts_created:
                success = self._send_to_community(post)
                if success:
                    self._log_community_post(transcript_session_id, post, 'success')
                else:
                    self._log_community_post(transcript_session_id, post, 'failed')
            
            print(f"📢 Posted {len(posts_created)} messages to {self.community_config['platform']} community")
            
        except Exception as e:
            print(f"Error posting to community: {e}")
    
    def _get_quantifiable_goals_for_session(self, transcript_session_id: str) -> List[Dict]:
        """Get quantifiable goals for a specific session"""
        try:
            result = self.supabase.schema('peer_progress').table('quantifiable_goals').select('*').eq('transcript_session_id', transcript_session_id).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting quantifiable goals: {e}")
            return []
    
    def _get_vague_goals_for_session(self, transcript_session_id: str) -> List[Dict]:
        """Get vague goals for a specific session"""
        try:
            result = self.supabase.schema('peer_progress').table('vague_goals_detected').select('*').eq('transcript_session_id', transcript_session_id).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting vague goals: {e}")
            return []
    
    def _create_summary_post(self, group_name: str, session_date: str, quantifiable_goals: List[Dict], vague_goals: List[Dict]) -> Dict:
        """Create a summary post for the community"""
        total_participants = len(set([g['participant_name'] for g in quantifiable_goals + vague_goals]))
        
        post_content = f"""
        🎯 **{group_name} - Goals Summary ({session_date})**

        👥 **{total_participants} participants** shared their goals

        ✅ **{len(quantifiable_goals)} quantifiable goals** set
        📝 **{len(vague_goals)} goals** need more specificity

        Let's hold each other accountable! 💪
        """
        
        return {
            'type': 'summary',
            'content': post_content,
            'group_name': group_name,
            'session_date': session_date,
            'participant_count': total_participants,
            'quantifiable_count': len(quantifiable_goals),
            'vague_count': len(vague_goals)
        }
    
    def _create_quantifiable_goals_post(self, group_name: str, quantifiable_goals: List[Dict]) -> Dict:
        """Create a post showing quantifiable goals"""
        post_content = f"🎯 **{group_name} - Quantifiable Goals**\n\n"
        
        for goal in quantifiable_goals:
            post_content += f"**{goal['participant_name']}:** {goal['goal_text']}\n"
            post_content += f"   Target: {goal['target_number']} {goal.get('goal_unit', 'units')}\n\n"
        
        post_content += "Let's crush these goals! 💪"
        
        return {
            'type': 'quantifiable_goals',
            'content': post_content,
            'group_name': group_name,
            'goal_count': len(quantifiable_goals)
        }
    
    def _create_vague_goals_post(self, group_name: str, vague_goals: List[Dict]) -> Dict:
        """Create a post showing vague goals that need refinement"""
        post_content = f"📝 **{group_name} - Goals Needing Specificity**\n\n"
        
        for goal in vague_goals:
            post_content += f"**{goal['participant_name']}:** {goal['original_goal_text']}\n"
            suggestions = goal.get('suggested_quantifications', [])
            if suggestions:
                post_content += f"   💡 Suggestion: {suggestions[0]}\n\n"
        
        post_content += "Let's help each other make these goals more specific! 🤝"
        
        return {
            'type': 'vague_goals',
            'content': post_content,
            'group_name': group_name,
            'goal_count': len(vague_goals)
        }
    
    def _send_to_community(self, post: Dict) -> bool:
        """Send post to community platform"""
        try:
            if self.community_config['platform'] == 'slack':
                return self._send_to_slack(post)
            elif self.community_config['platform'] == 'discord':
                return self._send_to_discord(post)
            elif self.community_config['platform'] == 'webhook':
                return self._send_to_webhook(post)
            else:
                print(f"Unsupported platform: {self.community_config['platform']}")
                return False
        except Exception as e:
            print(f"Error sending to community: {e}")
            return False
    
    def _send_to_slack(self, post: Dict) -> bool:
        """Send message to Slack"""
        try:
            payload = {
                "text": post['content'],
                "channel": self.community_config['channel'],
                "username": "Goal Tracker",
                "icon_emoji": ":goal:"
            }
            
            response = requests.post(self.community_config['webhook_url'], json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending to Slack: {e}")
            return False
    
    def _send_to_discord(self, post: Dict) -> bool:
        """Send message to Discord"""
        try:
            payload = {
                "content": post['content']
            }
            
            response = requests.post(self.community_config['webhook_url'], json=payload)
            return response.status_code == 204
        except Exception as e:
            print(f"Error sending to Discord: {e}")
            return False
    
    def _send_to_webhook(self, post: Dict) -> bool:
        """Send message to generic webhook"""
        try:
            payload = {
                "message": post['content'],
                "type": post['type'],
                "group_name": post['group_name'],
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(self.community_config['webhook_url'], json=payload)
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"Error sending to webhook: {e}")
            return False
    
    def _log_community_post(self, transcript_session_id: str, post: Dict, status: str):
        """Log community post to database"""
        try:
            log_data = {
                'transcript_session_id': transcript_session_id,
                'organization_id': self.organization_id,
                'post_type': post['type'],
                'post_content': post['content'],
                'platform': self.community_config['platform'],
                'channel': self.community_config['channel'],
                'status': status,
                'group_name': post['group_name']
            }
            
            self.supabase.schema('peer_progress').table('community_posts').insert(log_data).execute()
        except Exception as e:
            print(f"Error logging community post: {e}")
    
    def track_attendance_from_transcript(self, transcript_session_id: str, group_name: str, session_date: str, participants: List[str]):
        """Track attendance from transcript participants"""
        try:
            attendance_records = []
            
            for participant in participants:
                # Check if member exists in database
                member = self.get_member_by_name(participant)
                member_id = member['id'] if member else None
                
                attendance_record = {
                    'transcript_session_id': transcript_session_id,
                    'member_id': member_id,
                    'organization_id': self.organization_id,
                    'member_name': participant,
                    'group_name': group_name,
                    'call_date': session_date,
                    'attendance_status': 'present',
                    'communication_status': 'no_communication'
                }
                attendance_records.append(attendance_record)
            
            # Insert attendance records
            if attendance_records:
                self.supabase.schema('peer_progress').table('member_attendance').insert(attendance_records).execute()
                print(f"📋 Tracked attendance for {len(attendance_records)} participants")
            
            return attendance_records
            
        except Exception as e:
            print(f"Error tracking attendance: {e}")
            return []
    
    def assess_member_risk(self, member_id: str, organization_id: str = None) -> Dict:
        """Assess member risk level based on attendance and goals"""
        try:
            org_filter = organization_id or self.organization_id
            member = self.get_member_by_name(member_id) if not member_id.startswith('uuid:') else None
            actual_member_id = member['id'] if member else member_id
            
            # Get recent attendance data (last 2 weeks)
            two_weeks_ago = (datetime.now() - timedelta(days=14)).date()
            attendance_result = self.supabase.schema('peer_progress').table('member_attendance').select('*').eq('member_id', actual_member_id).gte('call_date', two_weeks_ago.isoformat()).execute()
            
            # Get recent goals data
            goals_result = self.supabase.schema('peer_progress').table('member_goals_summary').select('*').eq('member_id', actual_member_id).gte('week_start_date', two_weeks_ago.isoformat()).execute()
            
            # Get recent commitments
            commitments_result = self.supabase.schema('peer_progress').table('commitments').select('*').eq('member_id', actual_member_id).gte('created_at', two_weeks_ago.isoformat()).execute()
            
            # Calculate risk factors
            risk_assessment = self._calculate_risk_factors(attendance_result.data, goals_result.data, commitments_result.data)
            
            # Store risk assessment
            assessment_data = {
                'member_id': actual_member_id,
                'organization_id': org_filter,
                'risk_level': risk_assessment['risk_level'],
                'risk_triggers': risk_assessment['triggers'],
                'consecutive_missed_calls': risk_assessment['consecutive_missed_calls'],
                'weeks_without_goals': risk_assessment['weeks_without_goals'],
                'weeks_without_goal_completion': risk_assessment['weeks_without_goal_completion'],
                'weeks_without_meetings': risk_assessment['weeks_without_meetings'],
                'meetings_scheduled': risk_assessment['meetings_scheduled'],
                'proposals_out': risk_assessment['proposals_out'],
                'clients_closed': risk_assessment['clients_closed'],
                'last_communication_date': risk_assessment['last_communication_date'],
                'last_goal_update_date': risk_assessment['last_goal_update_date'],
                'last_meeting_date': risk_assessment['last_meeting_date']
            }
            
            # Update or insert risk assessment
            existing_result = self.supabase.schema('peer_progress').table('member_risk_assessment').select('id').eq('member_id', actual_member_id).eq('assessment_date', datetime.now().date()).execute()
            
            if existing_result.data:
                self.supabase.schema('peer_progress').table('member_risk_assessment').update(assessment_data).eq('id', existing_result.data[0]['id']).execute()
            else:
                self.supabase.schema('peer_progress').table('member_risk_assessment').insert(assessment_data).execute()
            
            # Create follow-up actions if needed
            self._create_follow_up_actions(actual_member_id, risk_assessment)
            
            return risk_assessment
            
        except Exception as e:
            print(f"Error assessing member risk: {e}")
            return {'risk_level': 'on_track', 'triggers': []}
    
    def _calculate_risk_factors(self, attendance_data: List[Dict], goals_data: List[Dict], commitments_data: List[Dict]) -> Dict:
        """Calculate risk factors based on attendance and goals data"""
        triggers = []
        risk_level = 'on_track'
        
        # Analyze attendance
        consecutive_missed = 0
        total_calls = len(attendance_data)
        missed_calls = len([a for a in attendance_data if a.get('attendance_status') == 'absent'])
        communicated = len([a for a in attendance_data if a.get('communication_status') == 'communicated'])
        
        # Check for high-risk attendance patterns
        if missed_calls >= 2 and communicated == 0:
            triggers.append('missed_2_consecutive_calls_no_communication')
            risk_level = 'high_risk'
        elif missed_calls >= 1 and communicated == 0:
            triggers.append('missed_1_call_no_communication')
            risk_level = 'medium_risk'
        
        # Analyze goals
        weeks_with_goals = len([g for g in goals_data if g.get('goals_set')])
        weeks_with_goal_updates = len([g for g in goals_data if g.get('goals_updated')])
        weeks_with_goal_completion = len([g for g in goals_data if g.get('goals_completed')])
        
        if weeks_with_goals == 0:
            triggers.append('no_goals_for_2_weeks')
            if risk_level == 'on_track':
                risk_level = 'high_risk'
        elif weeks_with_goal_updates == 0:
            triggers.append('no_goal_updates_for_1_week')
            if risk_level == 'on_track':
                risk_level = 'medium_risk'
        
        # Analyze meetings and business metrics
        total_meetings = sum([g.get('meetings_scheduled', 0) for g in goals_data])
        total_proposals = sum([g.get('proposals_out', 0) for g in goals_data])
        total_clients = sum([g.get('clients_closed', 0) for g in goals_data])
        
        if total_meetings >= 4 and total_proposals == 0:
            triggers.append('4_plus_meetings_no_proposals')
            # This is a special case - still on track but needs coaching
        
        # Determine final risk level based on business success
        if total_clients > 0 or total_proposals > 0:
            risk_level = 'crushing_it'
            triggers.append('has_proposals_or_clients')
        elif total_meetings > 0 and weeks_with_goal_updates > 0:
            risk_level = 'on_track'
        
        return {
            'risk_level': risk_level,
            'triggers': triggers,
            'consecutive_missed_calls': consecutive_missed,
            'weeks_without_goals': 2 - weeks_with_goals,
            'weeks_without_goal_completion': 2 - weeks_with_goal_completion,
            'weeks_without_meetings': 2 - len([g for g in goals_data if g.get('meetings_scheduled', 0) > 0]),
            'meetings_scheduled': total_meetings,
            'proposals_out': total_proposals,
            'clients_closed': total_clients,
            'last_communication_date': attendance_data[-1]['call_date'] if attendance_data else None,
            'last_goal_update_date': goals_data[-1]['week_start_date'] if goals_data else None,
            'last_meeting_date': None  # Would need additional data source
        }
    
    def _create_follow_up_actions(self, member_id: str, risk_assessment: Dict):
        """Create follow-up actions for success champion based on risk assessment"""
        try:
            actions = []
            risk_level = risk_assessment['risk_level']
            triggers = risk_assessment['triggers']
            
            # Create actions based on risk level and triggers
            if risk_level == 'high_risk':
                for trigger in triggers:
                    if 'missed_2_consecutive_calls' in trigger:
                        actions.append({
                            'member_id': member_id,
                            'organization_id': self.organization_id,
                            'action_type': 'attendance_followup',
                            'trigger_reason': trigger,
                            'priority': 'urgent',
                            'due_date': (datetime.now() + timedelta(days=1)).date().isoformat()
                        })
                    elif 'no_goals_for_2_weeks' in trigger:
                        actions.append({
                            'member_id': member_id,
                            'organization_id': self.organization_id,
                            'action_type': 'goal_followup',
                            'trigger_reason': trigger,
                            'priority': 'high',
                            'due_date': (datetime.now() + timedelta(days=2)).date().isoformat()
                        })
            
            elif risk_level == 'medium_risk':
                for trigger in triggers:
                    if 'missed_1_call' in trigger:
                        actions.append({
                            'member_id': member_id,
                            'organization_id': self.organization_id,
                            'action_type': 'attendance_followup',
                            'trigger_reason': trigger,
                            'priority': 'medium',
                            'due_date': (datetime.now() + timedelta(days=3)).date().isoformat()
                        })
                    elif 'no_goal_updates' in trigger:
                        actions.append({
                            'member_id': member_id,
                            'organization_id': self.organization_id,
                            'action_type': 'goal_followup',
                            'trigger_reason': trigger,
                            'priority': 'medium',
                            'due_date': (datetime.now() + timedelta(days=3)).date().isoformat()
                        })
            
            # Special case for coaching intervention
            if '4_plus_meetings_no_proposals' in triggers:
                actions.append({
                    'member_id': member_id,
                    'organization_id': self.organization_id,
                    'action_type': 'coaching',
                    'trigger_reason': '4_plus_meetings_no_proposals',
                    'priority': 'medium',
                    'due_date': (datetime.now() + timedelta(days=5)).date().isoformat()
                })
            
            # Insert actions if any
            if actions:
                self.supabase.schema('peer_progress').table('success_champion_actions').insert(actions).execute()
                print(f"📋 Created {len(actions)} follow-up actions for member {member_id}")
            
        except Exception as e:
            print(f"Error creating follow-up actions: {e}")
    
    def get_risk_dashboard_summary(self, organization_id: str = None) -> Dict:
        """Get summary of member risk levels for dashboard"""
        try:
            org_filter = organization_id or self.organization_id
            
            # Get latest risk assessments for all members
            result = self.supabase.schema('peer_progress').table('member_risk_assessment').select('*').eq('organization_id', org_filter).execute()
            
            # Group by risk level
            risk_summary = {
                'high_risk': [],
                'medium_risk': [],
                'on_track': [],
                'crushing_it': []
            }
            
            for assessment in result.data:
                risk_level = assessment['risk_level']
                member_name = assessment.get('member_name', 'Unknown')
                
                risk_summary[risk_level].append({
                    'member_id': assessment['member_id'],
                    'member_name': member_name,
                    'triggers': assessment.get('risk_triggers', []),
                    'assessment_date': assessment['assessment_date']
                })
            
            # Create dashboard summary
            dashboard_summary = {
                'high_risk': {
                    'count': len(risk_summary['high_risk']),
                    'members': risk_summary['high_risk'][:5],  # Show first 5
                    'definition': 'Member is disengaged and unresponsive',
                    'triggers': ['Missed 2+ consecutive calls', 'No goals for 2 weeks', 'No communication for 2+ weeks']
                },
                'medium_risk': {
                    'count': len(risk_summary['medium_risk']),
                    'members': risk_summary['medium_risk'][:5],
                    'definition': 'Member shows inconsistent engagement',
                    'triggers': ['Missed 1 call without communication', 'No goals for 1 week', 'No goal completion']
                },
                'on_track': {
                    'count': len(risk_summary['on_track']),
                    'members': risk_summary['on_track'][:5],
                    'definition': 'Member is engaged and participating',
                    'triggers': ['Goals set and updated', 'Meetings scheduled', 'Accountability updates consistent']
                },
                'crushing_it': {
                    'count': len(risk_summary['crushing_it']),
                    'members': risk_summary['crushing_it'][:5],
                    'definition': 'Member is excelling and driving outcomes',
                    'triggers': ['Has proposals out', 'Has clients closed']
                }
            }
            
            return dashboard_summary
            
        except Exception as e:
            print(f"Error getting risk dashboard summary: {e}")
            return {'high_risk': {'count': 0}, 'medium_risk': {'count': 0}, 'on_track': {'count': 0}, 'crushing_it': {'count': 0}}
    
    def get_success_champion_actions(self, organization_id: str = None, status: str = 'pending') -> List[Dict]:
        """Get pending actions for success champion"""
        try:
            org_filter = organization_id or self.organization_id
            
            result = self.supabase.schema('peer_progress').table('success_champion_actions').select('*').eq('organization_id', org_filter).eq('action_status', status).order('priority', desc=True).order('due_date').execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting success champion actions: {e}")
            return []
    
    def log_member_change(self, member_id: str, change_type: str, change_category: str, old_value: Dict = None, new_value: Dict = None, change_description: str = None, change_reason: str = None, changed_by: str = "System", change_source: str = "automatic", effective_date: str = None, notes: str = None):
        """Log a member change event"""
        try:
            member = self.get_member_by_name(member_id) if not member_id.startswith('uuid:') else None
            actual_member_id = member['id'] if member else member_id
            
            change_data = {
                'member_id': actual_member_id,
                'organization_id': self.organization_id,
                'change_type': change_type,
                'change_category': change_category,
                'old_value': old_value,
                'new_value': new_value,
                'change_description': change_description or f"{change_type} change",
                'change_reason': change_reason,
                'changed_by': changed_by,
                'change_source': change_source,
                'effective_date': effective_date or datetime.now().date().isoformat(),
                'notes': notes
            }
            
            self.supabase.schema('peer_progress').table('member_change_log').insert(change_data).execute()
            print(f"📝 Logged {change_type} change for member {member_id}")
            
        except Exception as e:
            print(f"Error logging member change: {e}")
    
    def change_member_group(self, member_id: str, new_group: str, old_group: str = None, reason: str = None, changed_by: str = "Success Champion"):
        """Change member's group assignment and log the change"""
        try:
            member = self.get_member_by_name(member_id) if not member_id.startswith('uuid:') else None
            actual_member_id = member['id'] if member else member_id
            
            # Log the group change
            self.log_member_change(
                member_id=actual_member_id,
                change_type='group_change',
                change_category='membership',
                old_value={'group': old_group} if old_group else None,
                new_value={'group': new_group},
                change_description=f"Group changed from '{old_group}' to '{new_group}'" if old_group else f"Assigned to group '{new_group}'",
                change_reason=reason,
                changed_by=changed_by,
                change_source='manual'
            )
            
            # Update status history
            status_data = {
                'member_id': actual_member_id,
                'organization_id': self.organization_id,
                'status_type': 'group_assignment',
                'old_status': old_group,
                'new_status': new_group,
                'effective_date': datetime.now().date().isoformat(),
                'changed_by': changed_by,
                'change_reason': reason
            }
            
            self.supabase.schema('peer_progress').table('member_status_history').insert(status_data).execute()
            
            print(f"✅ Changed member {member_id} from group '{old_group}' to '{new_group}'")
            return True
            
        except Exception as e:
            print(f"Error changing member group: {e}")
            return False
    
    def process_member_renewal(self, member_id: str, renewal_type: str, renewal_date: str = None, amount: float = None, payment_method: str = None, invoice_number: str = None, notes: str = None, processed_by: str = "Success Champion"):
        """Process a member renewal and log the change"""
        try:
            member = self.get_member_by_name(member_id) if not member_id.startswith('uuid:') else None
            actual_member_id = member['id'] if member else member_id
            
            renewal_date_obj = datetime.strptime(renewal_date, '%Y-%m-%d') if renewal_date else datetime.now()
            
            # Calculate expiration date based on renewal type
            if renewal_type == 'monthly':
                expiration_date = renewal_date_obj + timedelta(days=30)
            elif renewal_type == 'quarterly':
                expiration_date = renewal_date_obj + timedelta(days=90)
            elif renewal_type == 'annual':
                expiration_date = renewal_date_obj + timedelta(days=365)
            elif renewal_type == 'lifetime':
                expiration_date = datetime(2099, 12, 31).date()
            else:
                expiration_date = renewal_date_obj + timedelta(days=30)  # Default to monthly
            
            # Create renewal record
            renewal_data = {
                'member_id': actual_member_id,
                'organization_id': self.organization_id,
                'renewal_type': renewal_type,
                'renewal_date': renewal_date_obj.date().isoformat(),
                'expiration_date': expiration_date.date().isoformat(),
                'amount': amount,
                'payment_method': payment_method,
                'invoice_number': invoice_number,
                'notes': notes,
                'processed_by': processed_by
            }
            
            self.supabase.schema('peer_progress').table('member_renewals').insert(renewal_data).execute()
            
            # Log the renewal change
            self.log_member_change(
                member_id=actual_member_id,
                change_type='renewal',
                change_category='billing',
                new_value={
                    'renewal_type': renewal_type,
                    'renewal_date': renewal_date_obj.date().isoformat(),
                    'expiration_date': expiration_date.date().isoformat(),
                    'amount': amount
                },
                change_description=f"{renewal_type.title()} renewal processed",
                change_reason=f"Subscription renewal - {renewal_type}",
                changed_by=processed_by,
                change_source='manual',
                notes=notes
            )
            
            # Update status history
            status_data = {
                'member_id': actual_member_id,
                'organization_id': self.organization_id,
                'status_type': 'subscription_status',
                'old_status': 'expired',
                'new_status': 'active',
                'effective_date': renewal_date_obj.date().isoformat(),
                'expiration_date': expiration_date.date().isoformat(),
                'changed_by': processed_by,
                'change_reason': f"{renewal_type} renewal"
            }
            
            self.supabase.schema('peer_progress').table('member_status_history').insert(status_data).execute()
            
            print(f"✅ Processed {renewal_type} renewal for member {member_id}")
            return True
            
        except Exception as e:
            print(f"Error processing member renewal: {e}")
            return False
    
    def pause_member(self, member_id: str, pause_type: str, pause_reason: str, pause_start_date: str = None, pause_end_date: str = None, notes: str = None, requested_by: str = "Member", approved_by: str = "Success Champion"):
        """Pause a member and log the change"""
        try:
            member = self.get_member_by_name(member_id) if not member_id.startswith('uuid:') else None
            actual_member_id = member['id'] if member else member_id
            
            pause_start = datetime.strptime(pause_start_date, '%Y-%m-%d') if pause_start_date else datetime.now()
            pause_end = datetime.strptime(pause_end_date, '%Y-%m-%d') if pause_end_date else None
            
            # Create pause record
            pause_data = {
                'member_id': actual_member_id,
                'organization_id': self.organization_id,
                'pause_type': pause_type,
                'pause_start_date': pause_start.date().isoformat(),
                'pause_end_date': pause_end.date().isoformat() if pause_end else None,
                'pause_reason': pause_reason,
                'notes': notes,
                'requested_by': requested_by,
                'approved_by': approved_by
            }
            
            self.supabase.schema('peer_progress').table('member_pauses').insert(pause_data).execute()
            
            # Log the pause change
            self.log_member_change(
                member_id=actual_member_id,
                change_type='pause',
                change_category='membership',
                new_value={
                    'pause_type': pause_type,
                    'pause_start_date': pause_start.date().isoformat(),
                    'pause_end_date': pause_end.date().isoformat() if pause_end else None,
                    'pause_reason': pause_reason
                },
                change_description=f"Member paused - {pause_type}",
                change_reason=pause_reason,
                changed_by=approved_by,
                change_source='manual',
                notes=notes
            )
            
            # Update status history
            status_data = {
                'member_id': actual_member_id,
                'organization_id': self.organization_id,
                'status_type': 'membership_status',
                'old_status': 'active',
                'new_status': 'paused',
                'effective_date': pause_start.date().isoformat(),
                'changed_by': approved_by,
                'change_reason': pause_reason,
                'notes': notes
            }
            
            self.supabase.schema('peer_progress').table('member_status_history').insert(status_data).execute()
            
            print(f"✅ Paused member {member_id} - {pause_type}")
            return True
            
        except Exception as e:
            print(f"Error pausing member: {e}")
            return False
    
    def resume_member(self, member_id: str, pause_id: str = None, resumed_date: str = None, notes: str = None, resumed_by: str = "Success Champion"):
        """Resume a paused member and log the change"""
        try:
            member = self.get_member_by_name(member_id) if not member_id.startswith('uuid:') else None
            actual_member_id = member['id'] if member else member_id
            
            resumed_date_obj = datetime.strptime(resumed_date, '%Y-%m-%d') if resumed_date else datetime.now()
            
            # Update pause record
            if pause_id:
                self.supabase.schema('peer_progress').table('member_pauses').update({
                    'pause_status': 'completed',
                    'resumed_date': resumed_date_obj.date().isoformat(),
                    'notes': notes
                }).eq('id', pause_id).execute()
            else:
                # Find active pause
                active_pause = self.supabase.schema('peer_progress').table('member_pauses').select('id').eq('member_id', actual_member_id).eq('pause_status', 'active').execute()
                if active_pause.data:
                    self.supabase.schema('peer_progress').table('member_pauses').update({
                        'pause_status': 'completed',
                        'resumed_date': resumed_date_obj.date().isoformat(),
                        'notes': notes
                    }).eq('id', active_pause.data[0]['id']).execute()
            
            # Log the resume change
            self.log_member_change(
                member_id=actual_member_id,
                change_type='resume',
                change_category='membership',
                new_value={'resumed_date': resumed_date_obj.date().isoformat()},
                change_description="Member resumed from pause",
                change_reason="Pause period ended",
                changed_by=resumed_by,
                change_source='manual',
                notes=notes
            )
            
            # Update status history
            status_data = {
                'member_id': actual_member_id,
                'organization_id': self.organization_id,
                'status_type': 'membership_status',
                'old_status': 'paused',
                'new_status': 'active',
                'effective_date': resumed_date_obj.date().isoformat(),
                'changed_by': resumed_by,
                'change_reason': 'Resumed from pause',
                'notes': notes
            }
            
            self.supabase.schema('peer_progress').table('member_status_history').insert(status_data).execute()
            
            print(f"✅ Resumed member {member_id}")
            return True
            
        except Exception as e:
            print(f"Error resuming member: {e}")
            return False
    
    def get_member_change_log(self, member_id: str, change_type: str = None, limit: int = 50) -> List[Dict]:
        """Get change log for a specific member"""
        try:
            member = self.get_member_by_name(member_id) if not member_id.startswith('uuid:') else None
            actual_member_id = member['id'] if member else member_id
            
            query = self.supabase.schema('peer_progress').table('member_change_log').select('*').eq('member_id', actual_member_id)
            
            if change_type:
                query = query.eq('change_type', change_type)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting member change log: {e}")
            return []
    
    def get_member_status_history(self, member_id: str, status_type: str = None) -> List[Dict]:
        """Get status history for a specific member"""
        try:
            member = self.get_member_by_name(member_id) if not member_id.startswith('uuid:') else None
            actual_member_id = member['id'] if member else member_id
            
            query = self.supabase.schema('peer_progress').table('member_status_history').select('*').eq('member_id', actual_member_id)
            
            if status_type:
                query = query.eq('status_type', status_type)
            
            result = query.order('effective_date', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting member status history: {e}")
            return []
    
    def get_renewals_due_soon(self, days_ahead: int = 30, organization_id: str = None) -> List[Dict]:
        """Get members with renewals due soon"""
        try:
            org_filter = organization_id or self.organization_id
            future_date = (datetime.now() + timedelta(days=days_ahead)).date()
            
            result = self.supabase.schema('peer_progress').table('member_renewals').select('*').eq('organization_id', org_filter).lte('expiration_date', future_date.isoformat()).order('expiration_date').execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting renewals due soon: {e}")
            return []
    
    def get_active_pauses(self, organization_id: str = None) -> List[Dict]:
        """Get all currently active member pauses"""
        try:
            org_filter = organization_id or self.organization_id
            
            result = self.supabase.schema('peer_progress').table('member_pauses').select('*').eq('organization_id', org_filter).eq('pause_status', 'active').execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting active pauses: {e}")
            return []
    
    def extract_marketing_activities(self, transcript: str, transcript_session_id: str, group_name: str, session_date: str) -> List[Dict]:
        """Extract marketing activities from transcript using AI"""
        try:
            # Load the marketing activity extraction prompt
            prompt = self.MARKETING_ACTIVITY_EXTRACTION.format(transcript=transcript)
            
            # Generate response using AI
            response = self.model.generate_content(prompt)
            activities_text = response.text
            
            # Parse the response to extract activities
            activities = self._parse_marketing_activities(activities_text, transcript_session_id, group_name, session_date)
            
            # Store activities in database
            if activities:
                self.supabase.schema('peer_progress').table('marketing_activities').insert(activities).execute()
                print(f"📊 Extracted {len(activities)} marketing activities")
            
            return activities
            
        except Exception as e:
            print(f"Error extracting marketing activities: {e}")
            return []
    
    def extract_pipeline_outcomes(self, transcript: str, transcript_session_id: str, group_name: str, session_date: str) -> List[Dict]:
        """Extract pipeline outcomes from transcript using AI"""
        try:
            # Load the pipeline outcome extraction prompt
            prompt = self.PIPELINE_OUTCOME_EXTRACTION.format(transcript=transcript)
            
            # Generate response using AI
            response = self.model.generate_content(prompt)
            outcomes_text = response.text
            
            # Parse the response to extract outcomes
            outcomes = self._parse_pipeline_outcomes(outcomes_text, transcript_session_id, group_name, session_date)
            
            # Store outcomes in database
            if outcomes:
                self.supabase.schema('peer_progress').table('pipeline_outcomes').insert(outcomes).execute()
                print(f"🎯 Extracted {len(outcomes)} pipeline outcomes")
            
            return outcomes
            
        except Exception as e:
            print(f"Error extracting pipeline outcomes: {e}")
            return []
    
    def _parse_marketing_activities(self, activities_text: str, transcript_session_id: str, group_name: str, session_date: str) -> List[Dict]:
        """Parse marketing activities from AI response"""
        activities = []
        lines = activities_text.strip().split('\n')
        
        current_participant = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and section headers
            if not line or line.startswith('---'):
                continue
            
            # Check if this is a participant name line
            if line.startswith('Name: '):
                current_participant = line.replace('Name: ', '').strip()
                continue
            
            # Check if no marketing activity mentioned
            if line == "No marketing activity mentioned.":
                if current_participant:
                    # Create a record indicating no activity
                    member = self.get_member_by_name(current_participant)
                    member_id = member['id'] if member else None
                    
                    activities.append({
                        'transcript_session_id': transcript_session_id,
                        'member_id': member_id,
                        'organization_id': self.organization_id,
                        'participant_name': current_participant,
                        'group_name': group_name,
                        'session_date': session_date,
                        'activity_category': 'network_activation',  # Default category
                        'activity_description': 'No marketing activity mentioned',
                        'quantity': 0,
                        'quantity_unit': 'activities'
                    })
                continue
            
            # Parse activity lines (Network Activation, LinkedIn, Cold Outreach)
            if line.startswith('- Network Activation:') or line.startswith('- LinkedIn:') or line.startswith('- Cold Outreach:'):
                if not current_participant:
                    continue
                
                # Extract category and description
                if line.startswith('- Network Activation:'):
                    category = 'network_activation'
                    description = line.replace('- Network Activation:', '').strip()
                elif line.startswith('- LinkedIn:'):
                    category = 'linkedin'
                    description = line.replace('- LinkedIn:', '').strip()
                elif line.startswith('- Cold Outreach:'):
                    category = 'cold_outreach'
                    description = line.replace('- Cold Outreach:', '').strip()
                
                # Extract quantity if mentioned
                quantity = None
                quantity_unit = None
                if description:
                    # Look for numbers in the description
                    import re
                    numbers = re.findall(r'\b(\d+)\b', description)
                    if numbers:
                        quantity = int(numbers[0])
                        # Determine unit based on context
                        if 'connection' in description.lower():
                            quantity_unit = 'connections'
                        elif 'post' in description.lower():
                            quantity_unit = 'posts'
                        elif 'message' in description.lower() or 'dm' in description.lower():
                            quantity_unit = 'messages'
                        elif 'email' in description.lower():
                            quantity_unit = 'emails'
                        elif 'call' in description.lower():
                            quantity_unit = 'calls'
                        else:
                            quantity_unit = 'activities'
                
                # Get member ID
                member = self.get_member_by_name(current_participant)
                member_id = member['id'] if member else None
                
                activities.append({
                    'transcript_session_id': transcript_session_id,
                    'member_id': member_id,
                    'organization_id': self.organization_id,
                    'participant_name': current_participant,
                    'group_name': group_name,
                    'session_date': session_date,
                    'activity_category': category,
                    'activity_description': description,
                    'quantity': quantity,
                    'quantity_unit': quantity_unit
                })
        
        return activities
    
    def _parse_pipeline_outcomes(self, outcomes_text: str, transcript_session_id: str, group_name: str, session_date: str) -> List[Dict]:
        """Parse pipeline outcomes from AI response"""
        outcomes = []
        lines = outcomes_text.strip().split('\n')
        
        current_participant = None
        current_outcome = {}
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and section headers
            if not line or line.startswith('---'):
                continue
            
            # Check if this is a participant name line
            if line.startswith('Name: '):
                # Save previous outcome if exists
                if current_participant and current_outcome:
                    outcomes.append(current_outcome)
                
                # Start new participant
                current_participant = line.replace('Name: ', '').strip()
                current_outcome = {
                    'transcript_session_id': transcript_session_id,
                    'organization_id': self.organization_id,
                    'participant_name': current_participant,
                    'group_name': group_name,
                    'session_date': session_date,
                    'meetings_count': 0,
                    'proposals_count': 0,
                    'clients_count': 0,
                    'outcome_notes': ''
                }
                
                # Get member ID
                member = self.get_member_by_name(current_participant)
                current_outcome['member_id'] = member['id'] if member else None
                
                continue
            
            # Parse outcome metrics
            if line.startswith('Meetings: '):
                count_str = line.replace('Meetings: ', '').strip()
                # Extract number, handling cases like "3" or "2 (planned)"
                import re
                numbers = re.findall(r'\b(\d+)\b', count_str)
                current_outcome['meetings_count'] = int(numbers[0]) if numbers else 0
                
            elif line.startswith('Proposals: '):
                count_str = line.replace('Proposals: ', '').strip()
                import re
                numbers = re.findall(r'\b(\d+)\b', count_str)
                current_outcome['proposals_count'] = int(numbers[0]) if numbers else 0
                
            elif line.startswith('Clients: '):
                count_str = line.replace('Clients: ', '').strip()
                import re
                numbers = re.findall(r'\b(\d+)\b', count_str)
                current_outcome['clients_count'] = int(numbers[0]) if numbers else 0
                
            elif line.startswith('Notes: '):
                current_outcome['outcome_notes'] = line.replace('Notes: ', '').strip()
        
        # Don't forget the last outcome
        if current_participant and current_outcome:
            outcomes.append(current_outcome)
        
        return outcomes
    
    def create_marketing_activity_summary(self, member_id: str, week_start_date: str, organization_id: str = None) -> Dict:
        """Create weekly marketing activity summary for a member"""
        try:
            org_filter = organization_id or self.organization_id
            
            # Calculate week end date
            from datetime import datetime, timedelta
            start_date = datetime.strptime(week_start_date, '%Y-%m-%d').date()
            end_date = start_date + timedelta(days=6)
            
            # Get marketing activities for the week
            activities_result = self.supabase.schema('peer_progress').table('marketing_activities').select('*').eq('member_id', member_id).eq('organization_id', org_filter).gte('session_date', week_start_date).lte('session_date', end_date.isoformat()).execute()
            
            # Get pipeline outcomes for the week
            outcomes_result = self.supabase.schema('peer_progress').table('pipeline_outcomes').select('*').eq('member_id', member_id).eq('organization_id', org_filter).gte('session_date', week_start_date).lte('session_date', end_date.isoformat()).execute()
            
            # Aggregate activities by category
            network_activation = 0
            linkedin = 0
            cold_outreach = 0
            
            for activity in activities_result.data:
                if activity['activity_category'] == 'network_activation':
                    network_activation += 1
                elif activity['activity_category'] == 'linkedin':
                    linkedin += 1
                elif activity['activity_category'] == 'cold_outreach':
                    cold_outreach += 1
            
            # Aggregate outcomes
            total_meetings = sum(outcome.get('meetings_count', 0) for outcome in outcomes_result.data)
            total_proposals = sum(outcome.get('proposals_count', 0) for outcome in outcomes_result.data)
            total_clients = sum(outcome.get('clients_count', 0) for outcome in outcomes_result.data)
            
            # Calculate effectiveness score (meetings per activity)
            total_activities = network_activation + linkedin + cold_outreach
            effectiveness_score = total_meetings / total_activities if total_activities > 0 else 0
            
            # Create summary record
            summary_data = {
                'member_id': member_id,
                'organization_id': org_filter,
                'week_start_date': week_start_date,
                'week_end_date': end_date.isoformat(),
                'network_activation_activities': network_activation,
                'linkedin_activities': linkedin,
                'cold_outreach_activities': cold_outreach,
                'total_meetings': total_meetings,
                'total_proposals': total_proposals,
                'total_clients': total_clients,
                'activity_effectiveness_score': round(effectiveness_score, 2),
                'summary_notes': f"Weekly summary: {total_activities} activities, {total_meetings} meetings, {total_proposals} proposals, {total_clients} clients"
            }
            
            # Update or insert summary
            existing_result = self.supabase.schema('peer_progress').table('marketing_activity_summary').select('id').eq('member_id', member_id).eq('week_start_date', week_start_date).execute()
            
            if existing_result.data:
                self.supabase.schema('peer_progress').table('marketing_activity_summary').update(summary_data).eq('id', existing_result.data[0]['id']).execute()
            else:
                self.supabase.schema('peer_progress').table('marketing_activity_summary').insert(summary_data).execute()
            
            return summary_data
            
        except Exception as e:
            print(f"Error creating marketing activity summary: {e}")
            return {}
    
    def get_marketing_activity_dashboard(self, organization_id: str = None, weeks_back: int = 4) -> Dict:
        """Get marketing activity dashboard data"""
        try:
            org_filter = organization_id or self.organization_id
            
            # Get recent summaries
            from datetime import datetime, timedelta
            weeks_ago = datetime.now().date() - timedelta(weeks=weeks_back)
            
            summaries_result = self.supabase.schema('peer_progress').table('marketing_activity_summary').select('*').eq('organization_id', org_filter).gte('week_start_date', weeks_ago.isoformat()).execute()
            
            # Calculate aggregate statistics
            total_network_activation = sum(s.get('network_activation_activities', 0) for s in summaries_result.data)
            total_linkedin = sum(s.get('linkedin_activities', 0) for s in summaries_result.data)
            total_cold_outreach = sum(s.get('cold_outreach_activities', 0) for s in summaries_result.data)
            total_meetings = sum(s.get('total_meetings', 0) for s in summaries_result.data)
            total_proposals = sum(s.get('total_proposals', 0) for s in summaries_result.data)
            total_clients = sum(s.get('total_clients', 0) for s in summaries_result.data)
            
            # Calculate averages
            total_activities = total_network_activation + total_linkedin + total_cold_outreach
            avg_effectiveness = sum(s.get('activity_effectiveness_score', 0) for s in summaries_result.data) / len(summaries_result.data) if summaries_result.data else 0
            
            # Identify top performers
            top_performers = sorted(summaries_result.data, key=lambda x: x.get('total_clients', 0), reverse=True)[:5]
            
            # Identify coaching opportunities (no activity, no outcomes)
            coaching_opportunities = [s for s in summaries_result.data if s.get('network_activation_activities', 0) == 0 and s.get('linkedin_activities', 0) == 0 and s.get('cold_outreach_activities', 0) == 0]
            
            dashboard_data = {
                'summary': {
                    'total_network_activation': total_network_activation,
                    'total_linkedin': total_linkedin,
                    'total_cold_outreach': total_cold_outreach,
                    'total_activities': total_activities,
                    'total_meetings': total_meetings,
                    'total_proposals': total_proposals,
                    'total_clients': total_clients,
                    'avg_effectiveness_score': round(avg_effectiveness, 2)
                },
                'top_performers': top_performers,
                'coaching_opportunities': coaching_opportunities,
                'activity_distribution': {
                    'network_activation_pct': round(total_network_activation / total_activities * 100, 1) if total_activities > 0 else 0,
                    'linkedin_pct': round(total_linkedin / total_activities * 100, 1) if total_activities > 0 else 0,
                    'cold_outreach_pct': round(total_cold_outreach / total_activities * 100, 1) if total_activities > 0 else 0
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            print(f"Error getting marketing activity dashboard: {e}")
            return {}
    
    def extract_challenges_and_strategies(self, transcript: str, transcript_session_id: str, group_name: str, session_date: str) -> Dict:
        """Extract challenges and strategies from transcript using AI"""
        try:
            # Load the challenge & strategy extraction prompt
            prompt = self.CHALLENGE_STRATEGY_EXTRACTION.format(transcript=transcript)
            
            # Generate response using AI
            response = self.model.generate_content(prompt)
            challenges_strategies_text = response.text
            
            # Parse the response to extract challenges and strategies
            challenges, strategies = self._parse_challenges_and_strategies(challenges_strategies_text, transcript_session_id, group_name, session_date)
            
            # Store challenges and strategies in database
            if challenges:
                challenge_records = self.supabase.schema('peer_progress').table('challenges').insert(challenges).execute()
                print(f"🧠 Extracted {len(challenges)} challenges")
                
                # Update challenge category usage counts
                for challenge in challenges:
                    self._update_challenge_category_usage(challenge['challenge_category'])
            
            if strategies:
                self.supabase.schema('peer_progress').table('strategies').insert(strategies).execute()
                print(f"💡 Extracted {len(strategies)} strategies")
                
                # Update strategy type usage counts
                for strategy in strategies:
                    self._update_strategy_type_usage(strategy['strategy_type'])
            
            return {
                'challenges': challenges,
                'strategies': strategies
            }
            
        except Exception as e:
            print(f"Error extracting challenges and strategies: {e}")
            return {'challenges': [], 'strategies': []}
    
    def _parse_challenges_and_strategies(self, challenges_strategies_text: str, transcript_session_id: str, group_name: str, session_date: str) -> tuple:
        """Parse challenges and strategies from AI response"""
        challenges = []
        strategies = []
        lines = challenges_strategies_text.strip().split('\n')
        
        current_participant = None
        current_challenge = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and section headers
            if not line or line.startswith('---'):
                continue
            
            # Check if this is a participant name line
            if line.startswith('Name: '):
                # Save previous challenge if exists
                if current_participant and current_challenge:
                    challenges.append(current_challenge)
                
                # Start new participant
                current_participant = line.replace('Name: ', '').strip()
                current_challenge = {
                    'transcript_session_id': transcript_session_id,
                    'organization_id': self.organization_id,
                    'participant_name': current_participant,
                    'group_name': group_name,
                    'session_date': session_date,
                    'challenge_description': '',
                    'challenge_category': 'Other',
                    'is_explicit_challenge': True,
                    'challenge_context': ''
                }
                
                # Get member ID
                member = self.get_member_by_name(current_participant)
                current_challenge['member_id'] = member['id'] if member else None
                
                continue
            
            # Parse challenge description
            if line.startswith('Challenge: '):
                challenge_desc = line.replace('Challenge: ', '').strip()
                current_challenge['challenge_description'] = challenge_desc
                # Check if it's implicit
                if 'implicit' in challenge_desc.lower():
                    current_challenge['is_explicit_challenge'] = False
                
            # Parse challenge category
            elif line.startswith('Category: '):
                category = line.replace('Category: ', '').strip()
                # Remove emoji and clean category name
                import re
                category_clean = re.sub(r'[^\w\s&/]', '', category).strip()
                current_challenge['challenge_category'] = category_clean
                
            # Parse strategies/tips
            elif line.startswith('Strategies/Tips:'):
                # This is the header, continue to next line
                continue
                
            elif line.startswith('- '):
                if not current_participant or not current_challenge:
                    continue
                
                strategy_text = line.replace('- ', '').strip()
                
                # Parse strategy details
                strategy_data = self._parse_strategy_line(strategy_text, transcript_session_id, None)  # Will link later
                if strategy_data:
                    strategies.append(strategy_data)
        
        # Don't forget the last challenge
        if current_participant and current_challenge:
            challenges.append(current_challenge)
        
        return challenges, strategies
    
    def _parse_strategy_line(self, strategy_text: str, transcript_session_id: str, challenge_id: str) -> Dict:
        """Parse individual strategy line"""
        try:
            # Extract strategy type from parentheses at the end
            import re
            type_match = re.search(r'\(([^)]+)\)$', strategy_text)
            strategy_type_raw = type_match.group(1) if type_match else '📝 Tactical Process'
            
            # Clean strategy description
            strategy_desc = re.sub(r'\([^)]+\)$', '', strategy_text).strip()
            
            # Map emoji types to database values
            strategy_type_map = {
                '🧠 Mindset Reframe': 'mindset_reframe',
                '📝 Tactical Process': 'tactical_process',
                '🧰 Tool / Resource Suggestion': 'tool_resource',
                '🔗 Connection / Referral': 'connection_referral',
                '🧭 Framework / Model Shared': 'framework_model'
            }
            
            strategy_type = strategy_type_map.get(strategy_type_raw, 'tactical_process')
            
            # Extract who shared it (usually at the beginning)
            shared_by = 'Unknown'
            if ' suggested' in strategy_desc.lower():
                shared_by = strategy_desc.split(' suggested')[0].strip()
            elif ' shared' in strategy_desc.lower():
                shared_by = strategy_desc.split(' shared')[0].strip()
            elif ' recommended' in strategy_desc.lower():
                shared_by = strategy_desc.split(' recommended')[0].strip()
            elif ' advised' in strategy_desc.lower():
                shared_by = strategy_desc.split(' advised')[0].strip()
            
            strategy_data = {
                'transcript_session_id': transcript_session_id,
                'organization_id': self.organization_id,
                'strategy_description': strategy_desc,
                'strategy_type': strategy_type,
                'shared_by': shared_by,
                'challenge_id': challenge_id,
                'is_general_advice': False,
                'strategy_notes': ''
            }
            
            return strategy_data
            
        except Exception as e:
            print(f"Error parsing strategy line: {e}")
            return None
    
    def _update_challenge_category_usage(self, category_name: str):
        """Update usage count for challenge category"""
        try:
            # Simple increment - could be enhanced with RPC function
            result = self.supabase.schema('peer_progress').table('challenge_categories').select('usage_count').eq('category_name', category_name).execute()
            if result.data:
                current_count = result.data[0].get('usage_count', 0)
                self.supabase.schema('peer_progress').table('challenge_categories').update({
                    'usage_count': current_count + 1
                }).eq('category_name', category_name).execute()
        except Exception as e:
            print(f"Error updating challenge category usage: {e}")
    
    def _update_strategy_type_usage(self, strategy_type: str):
        """Update usage count for strategy type"""
        try:
            # Simple increment - could be enhanced with RPC function
            result = self.supabase.schema('peer_progress').table('strategy_types').select('usage_count').eq('type_name', strategy_type).execute()
            if result.data:
                current_count = result.data[0].get('usage_count', 0)
                self.supabase.schema('peer_progress').table('strategy_types').update({
                    'usage_count': current_count + 1
                }).eq('type_name', strategy_type).execute()
        except Exception as e:
            print(f"Error updating strategy type usage: {e}")
    
    def get_challenge_analysis_dashboard(self, organization_id: str = None, weeks_back: int = 8) -> Dict:
        """Get challenge analysis dashboard data"""
        try:
            org_filter = organization_id or self.organization_id
            
            # Get recent challenges
            from datetime import datetime, timedelta
            weeks_ago = datetime.now().date() - timedelta(weeks=weeks_back)
            
            challenges_result = self.supabase.schema('peer_progress').table('challenges').select('*').eq('organization_id', org_filter).gte('session_date', weeks_ago.isoformat()).execute()
            
            strategies_result = self.supabase.schema('peer_progress').table('strategies').select('*').eq('organization_id', org_filter).gte('created_at', weeks_ago.isoformat()).execute()
            
            # Analyze challenge categories
            category_counts = {}
            for challenge in challenges_result.data:
                category = challenge.get('challenge_category', 'Other')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Analyze strategy types
            strategy_type_counts = {}
            for strategy in strategies_result.data:
                strategy_type = strategy.get('strategy_type', 'tactical_process')
                strategy_type_counts[strategy_type] = strategy_type_counts.get(strategy_type, 0) + 1
            
            # Find most common challenges
            most_common_challenges = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Find most shared strategy types
            most_common_strategies = sorted(strategy_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Find top strategy contributors
            contributor_counts = {}
            for strategy in strategies_result.data:
                contributor = strategy.get('shared_by', 'Unknown')
                contributor_counts[contributor] = contributor_counts.get(contributor, 0) + 1
            
            top_contributors = sorted(contributor_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Find participants with most challenges
            participant_challenge_counts = {}
            for challenge in challenges_result.data:
                participant = challenge.get('participant_name', 'Unknown')
                participant_challenge_counts[participant] = participant_challenge_counts.get(participant, 0) + 1
            
            participants_with_most_challenges = sorted(participant_challenge_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            dashboard_data = {
                'summary': {
                    'total_challenges': len(challenges_result.data),
                    'total_strategies': len(strategies_result.data),
                    'unique_participants': len(set(c.get('participant_name') for c in challenges_result.data)),
                    'unique_contributors': len(set(s.get('shared_by') for s in strategies_result.data))
                },
                'challenge_analysis': {
                    'most_common_challenges': most_common_challenges,
                    'category_distribution': category_counts,
                    'participants_with_most_challenges': participants_with_most_challenges
                },
                'strategy_analysis': {
                    'most_common_strategy_types': most_common_strategies,
                    'strategy_type_distribution': strategy_type_counts,
                    'top_contributors': top_contributors
                },
                'insights': {
                    'avg_strategies_per_challenge': round(len(strategies_result.data) / len(challenges_result.data), 2) if challenges_result.data else 0,
                    'most_active_category': most_common_challenges[0][0] if most_common_challenges else 'None',
                    'most_helpful_strategy_type': most_common_strategies[0][0] if most_common_strategies else 'None'
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            print(f"Error getting challenge analysis dashboard: {e}")
            return {}
    
    def get_challenges_by_category(self, category: str, organization_id: str = None, limit: int = 20) -> List[Dict]:
        """Get challenges by category"""
        try:
            org_filter = organization_id or self.organization_id
            
            result = self.supabase.schema('peer_progress').table('challenges').select('*').eq('organization_id', org_filter).eq('challenge_category', category).order('created_at', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting challenges by category: {e}")
            return []
    
    def get_strategies_by_type(self, strategy_type: str, organization_id: str = None, limit: int = 20) -> List[Dict]:
        """Get strategies by type"""
        try:
            org_filter = organization_id or self.organization_id
            
            result = self.supabase.schema('peer_progress').table('strategies').select('*').eq('organization_id', org_filter).eq('strategy_type', strategy_type).order('created_at', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting strategies by type: {e}")
            return []
    
    def get_participant_challenges_and_solutions(self, participant_name: str, organization_id: str = None, limit: int = 10) -> Dict:
        """Get challenges and solutions for a specific participant"""
        try:
            org_filter = organization_id or self.organization_id
            
            # Get challenges
            challenges_result = self.supabase.schema('peer_progress').table('challenges').select('*').eq('organization_id', org_filter).eq('participant_name', participant_name).order('created_at', desc=True).limit(limit).execute()
            
            # Get strategies shared by this participant
            strategies_shared_result = self.supabase.schema('peer_progress').table('strategies').select('*').eq('organization_id', org_filter).eq('shared_by', participant_name).order('created_at', desc=True).limit(limit).execute()
            
            return {
                'challenges': challenges_result.data if challenges_result.data else [],
                'strategies_shared': strategies_shared_result.data if strategies_shared_result.data else [],
                'strategies_received': []  # Would need to link via challenge_id
            }
            
        except Exception as e:
            print(f"Error getting participant challenges and solutions: {e}")
            return {'challenges': [], 'strategies_shared': [], 'strategies_received': []}
    
    def extract_stuck_signals(self, transcript: str, transcript_session_id: str, group_name: str, session_date: str) -> Dict:
        """Extract stuck signals from transcript using AI"""
        try:
            # Load the stuck signal extraction prompt
            prompt = self.STUCK_SIGNAL_EXTRACTION.format(transcript=transcript)
            
            # Generate response using AI
            response = self.model.generate_content(prompt)
            stuck_signals_text = response.text
            
            # Parse the response to extract stuck signals
            stuck_signals = self._parse_stuck_signals(stuck_signals_text, transcript_session_id, group_name, session_date)
            
            # Store stuck signals in database
            if stuck_signals:
                self.supabase.schema('peer_progress').table('stuck_signals').insert(stuck_signals).execute()
                print(f"🚨 Extracted {len(stuck_signals)} stuck signals")
                
                # Create flags for stuck signals
                for signal in stuck_signals:
                    self._create_stuck_signal_flag(signal)
            
            return {'stuck_signals': stuck_signals}
            
        except Exception as e:
            print(f"Error extracting stuck signals: {e}")
            return {'stuck_signals': []}
    
    def _parse_stuck_signals(self, stuck_signals_text: str, transcript_session_id: str, group_name: str, session_date: str) -> List[Dict]:
        """Parse stuck signals from AI response"""
        stuck_signals = []
        lines = stuck_signals_text.strip().split('\n')
        
        current_participant = None
        current_signal = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and section headers
            if not line or line.startswith('---'):
                continue
            
            # Check if this is a participant name line
            if line.startswith('### '):
                # Save previous signal if exists
                if current_participant and current_signal:
                    stuck_signals.append(current_signal)
                
                # Start new participant
                current_participant = line.replace('### ', '').strip()
                current_signal = {
                    'transcript_session_id': transcript_session_id,
                    'organization_id': self.organization_id,
                    'participant_name': current_participant,
                    'group_name': group_name,
                    'session_date': session_date,
                    'stuck_summary': '',
                    'stuck_classification': 'other',
                    'exact_quotes': [],
                    'timestamp_start': '',
                    'timestamp_end': '',
                    'suggested_nudge': '',
                    'severity_score': 3
                }
                
                # Get member ID
                member = self.get_member_by_name(current_participant)
                current_signal['member_id'] = member['id'] if member else None
                
                continue
            
            # Parse stuck summary
            if line.startswith('**Stuck Summary:**'):
                # Get the next line for the summary
                continue
            elif current_signal and not current_signal['stuck_summary'] and not line.startswith('**'):
                current_signal['stuck_summary'] = line
                
            # Parse exact quotes
            elif line.startswith('**Exact Quotes:**'):
                continue
            elif current_signal and line.startswith('- '):
                quote = line.replace('- ', '').strip()
                if quote and quote not in current_signal['exact_quotes']:
                    current_signal['exact_quotes'].append(quote)
                
            # Parse timestamp
            elif line.startswith('**Timestamp:**'):
                # Get the next line for timestamp
                continue
            elif current_signal and line.startswith('(') and line.endswith(')'):
                timestamp = line.replace('(', '').replace(')', '').strip()
                if '–' in timestamp:
                    start, end = timestamp.split('–', 1)
                    current_signal['timestamp_start'] = start.strip()
                    current_signal['timestamp_end'] = end.strip()
                else:
                    current_signal['timestamp_start'] = timestamp
                
            # Parse stuck classification
            elif line.startswith('**Stuck Classification:**'):
                # Get the next line for classification
                continue
            elif current_signal and not current_signal['stuck_classification'] == 'other' and not line.startswith('**'):
                classification = line.strip()
                # Map to database values
                classification_map = {
                    'Momentum Drop': 'momentum_drop',
                    'Emotional Block': 'emotional_block',
                    'Overwhelm': 'overwhelm',
                    'Decision Paralysis': 'decision_paralysis',
                    'Repeating Goal': 'repeating_goal',
                    'Other': 'other'
                }
                current_signal['stuck_classification'] = classification_map.get(classification, 'other')
                
            # Parse suggested nudge
            elif line.startswith('**Potential Next Step or Nudge (Optional):**'):
                # Get the next line for nudge
                continue
            elif current_signal and not current_signal['suggested_nudge'] and not line.startswith('**'):
                current_signal['suggested_nudge'] = line
        
        # Don't forget the last signal
        if current_participant and current_signal:
            stuck_signals.append(current_signal)
        
        return stuck_signals
    
    def extract_help_offers(self, transcript: str, transcript_session_id: str, group_name: str, session_date: str) -> Dict:
        """Extract help offers from transcript using AI"""
        try:
            # Load the help offer extraction prompt
            prompt = self.HELP_OFFER_EXTRACTION.format(transcript=transcript)
            
            # Generate response using AI
            response = self.model.generate_content(prompt)
            help_offers_text = response.text
            
            # Parse the response to extract help offers
            help_offers = self._parse_help_offers(help_offers_text, transcript_session_id, group_name, session_date)
            
            # Store help offers in database
            if help_offers:
                self.supabase.schema('peer_progress').table('help_offers').insert(help_offers).execute()
                print(f"🤝 Extracted {len(help_offers)} help offers")
                
                # Create support connections
                for offer in help_offers:
                    self._create_support_connection(offer)
            
            return {'help_offers': help_offers}
            
        except Exception as e:
            print(f"Error extracting help offers: {e}")
            return {'help_offers': []}
    
    def _parse_help_offers(self, help_offers_text: str, transcript_session_id: str, group_name: str, session_date: str) -> List[Dict]:
        """Parse help offers from AI response"""
        help_offers = []
        lines = help_offers_text.strip().split('\n')
        
        current_participant = None
        current_offer = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and section headers
            if not line or line.startswith('---'):
                continue
            
            # Check if this is a participant name line
            if line.startswith('### '):
                # Save previous offer if exists
                if current_participant and current_offer:
                    help_offers.append(current_offer)
                
                # Start new participant
                current_participant = line.replace('### ', '').strip()
                current_offer = {
                    'transcript_session_id': transcript_session_id,
                    'organization_id': self.organization_id,
                    'offerer_name': current_participant,
                    'group_name': group_name,
                    'session_date': session_date,
                    'help_description': '',
                    'help_context': '',
                    'exact_quote': '',
                    'timestamp': '',
                    'classification': 'general_support',
                    'target_participant': None,
                    'domain_expertise': ''
                }
                
                continue
            
            # Parse help description
            if line.startswith('**What They Offered to Help With:**'):
                # Get the next line for description
                continue
            elif current_offer and not current_offer['help_description'] and not line.startswith('**'):
                current_offer['help_description'] = line
                
            # Parse context
            elif line.startswith('**Context:**'):
                # Get the next line for context
                continue
            elif current_offer and not current_offer['help_context'] and not line.startswith('**'):
                current_offer['help_context'] = line
                
            # Parse exact quote
            elif line.startswith('**Exact Quote:**'):
                # Get the next line for quote
                continue
            elif current_offer and line.startswith('"') and line.endswith('"'):
                current_offer['exact_quote'] = line.replace('"', '').strip()
                
            # Parse timestamp
            elif line.startswith('**Timestamp:**'):
                # Get the next line for timestamp
                continue
            elif current_offer and line.startswith('(') and line.endswith(')'):
                timestamp = line.replace('(', '').replace(')', '').strip()
                current_offer['timestamp'] = timestamp
                
            # Parse classification
            elif line.startswith('**Classification:**'):
                # Get the next line for classification
                continue
            elif current_offer and not current_offer['classification'] == 'general_support' and not line.startswith('**'):
                classification = line.strip()
                # Map to database values
                classification_map = {
                    'Expertise': 'expertise',
                    'Resource': 'resource',
                    'General Support': 'general_support',
                    'Introductions': 'introductions',
                    'Review & Feedback': 'review_feedback'
                }
                current_offer['classification'] = classification_map.get(classification, 'general_support')
        
        # Don't forget the last offer
        if current_participant and current_offer:
            help_offers.append(current_offer)
        
        return help_offers
    
    def analyze_sentiment(self, transcript: str, transcript_session_id: str, group_name: str, session_date: str) -> Dict:
        """Analyze sentiment and group health from transcript using AI"""
        try:
            print(f"🔍 Analyzing sentiment for group: '{group_name}', session_id: '{transcript_session_id}'")
            
            # Load the sentiment analysis prompt
            prompt = self.SENTIMENT_ANALYSIS.format(transcript=transcript)
            
            # Generate response using AI
            response = self.model.generate_content(prompt)
            sentiment_text = response.text
            
            # Parse the response to extract sentiment data
            sentiment_data = self._parse_sentiment_analysis(sentiment_text, transcript_session_id, group_name, session_date)
            
            # Store sentiment data in database
            if sentiment_data:
                # Store call sentiment
                self.supabase.schema('peer_progress').table('call_sentiment').insert(sentiment_data['call_sentiment']).execute()
                print(f"📊 Analyzed sentiment: {sentiment_data['call_sentiment']['sentiment_score']}/5")
                
                # Store participant sentiments
                if sentiment_data['participant_sentiments']:
                    self.supabase.schema('peer_progress').table('participant_sentiment').insert(sentiment_data['participant_sentiments']).execute()
                    print(f"👥 Analyzed {len(sentiment_data['participant_sentiments'])} participant sentiments")
            
            return sentiment_data
            
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {}
    
    def _parse_sentiment_analysis(self, sentiment_text: str, transcript_session_id: str, group_name: str, session_date: str) -> Dict:
        """Parse sentiment analysis from AI response"""
        lines = sentiment_text.strip().split('\n')
        
        sentiment_data = {
            'call_sentiment': None,
            'participant_sentiments': []
        }
        
        current_participant = None
        current_participant_data = None
        
        # Parse call sentiment
        call_sentiment = {
            'transcript_session_id': transcript_session_id,
            'organization_id': self.organization_id,
            'group_name': group_name,
            'session_date': session_date,
            'sentiment_score': 3.0,
            'confidence_score': 0.5,
            'rationale': '',
            'dominant_emotions': [],
            'representative_quotes': [],
            'negative_participant_count': 0,
            'tense_exchange_count': 0,
            'laughter_count': 0
        }
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Parse sentiment score
            if line.startswith('**Sentiment Score:**'):
                score_text = line.replace('**Sentiment Score:**', '').strip()
                try:
                    score = float(score_text.split()[0])
                    call_sentiment['sentiment_score'] = score
                except:
                    pass
                    
            # Parse rationale
            elif line.startswith('**Rationale:**'):
                continue
            elif not call_sentiment['rationale'] and not line.startswith('**'):
                call_sentiment['rationale'] = line
                
            # Parse dominant emotions
            elif line.startswith('**Dominant Emotions:**'):
                continue
            elif line.startswith('*Example:') or line.startswith('*'):
                continue
            elif 'stuck' in line.lower() or 'optimistic' in line.lower() or 'supportive' in line.lower():
                emotions = [emotion.strip() for emotion in line.replace('*', '').replace('Example:', '').strip().split(',')]
                call_sentiment['dominant_emotions'] = emotions
                
            # Parse representative quotes
            elif line.startswith('**Representative Quotes:**'):
                continue
            elif line.startswith('- ') and ':' in line:
                quote = line.replace('- ', '').strip()
                call_sentiment['representative_quotes'].append(quote)
                
            # Parse confidence score
            elif line.startswith('**Confidence Score:**'):
                score_text = line.replace('**Confidence Score:**', '').strip()
                try:
                    score = float(score_text)
                    call_sentiment['confidence_score'] = score
                except:
                    pass
                    
            # Parse participants with negative emotions
            elif line.startswith('**Participants Expressing Negative Emotions:**'):
                continue
            elif line.startswith('- **') and line.endswith('**'):
                # New participant
                if current_participant and current_participant_data:
                    sentiment_data['participant_sentiments'].append(current_participant_data)
                
                participant_name = line.replace('- **', '').replace('**', '').strip()
                current_participant = participant_name
                
                # Get member ID
                member = self.get_member_by_name(participant_name)
                
                current_participant_data = {
                    'transcript_session_id': transcript_session_id,
                    'member_id': member['id'] if member else None,
                    'organization_id': self.organization_id,
                    'participant_name': participant_name,
                    'group_name': group_name,
                    'session_date': session_date,
                    'negativity_score': 0.6,  # Default for negative participants
                    'positivity_score': 0.3,
                    'emotion_tags': [],
                    'evidence_quotes': [],
                    'notes': ''
                }
                
            elif current_participant and line.startswith('    - *Emotions:*'):
                emotions_text = line.replace('    - *Emotions:*', '').strip()
                emotions = [emotion.strip() for emotion in emotions_text.split(',')]
                current_participant_data['emotion_tags'] = emotions
                
            elif current_participant and line.startswith('    - *Evidence:*'):
                continue
            elif current_participant and line.startswith('    '):
                evidence = line.strip()
                if evidence and evidence not in current_participant_data['evidence_quotes']:
                    current_participant_data['evidence_quotes'].append(evidence)
        
        # Don't forget the last participant
        if current_participant and current_participant_data:
            sentiment_data['participant_sentiments'].append(current_participant_data)
        
        # Update negative participant count
        call_sentiment['negative_participant_count'] = len(sentiment_data['participant_sentiments'])
        
        sentiment_data['call_sentiment'] = call_sentiment
        
        return sentiment_data
    
    def _create_stuck_signal_flag(self, stuck_signal: Dict):
        """Create a flag for stuck signal"""
        try:
            flag_data = {
                'transcript_session_id': stuck_signal['transcript_session_id'],
                'organization_id': stuck_signal['organization_id'],
                'group_name': stuck_signal['group_name'],
                'session_date': stuck_signal['session_date'],
                'flag_level': 'warning' if stuck_signal['severity_score'] >= 3 else 'info',
                'flag_reason': f"Participant {stuck_signal['participant_name']} showing stuck signals: {stuck_signal['stuck_classification']}",
                'flag_category': 'stuck_signals',
                'triggered_by': 'stuck_signal_extraction'
            }
            
            self.supabase.schema('peer_progress').table('group_health_flags').insert(flag_data).execute()
            
        except Exception as e:
            print(f"Error creating stuck signal flag: {e}")
    
    def _create_support_connection(self, help_offer: Dict):
        """Create a support connection from help offer"""
        try:
            connection_data = {
                'transcript_session_id': help_offer['transcript_session_id'],
                'organization_id': help_offer['organization_id'],
                'group_name': help_offer['group_name'],
                'session_date': help_offer['session_date'],
                'supporter_name': help_offer['offerer_name'],
                'supported_participant': help_offer.get('target_participant'),
                'support_type': 'help_offer',
                'support_description': help_offer['help_description'],
                'follow_up_needed': False,
                'follow_up_notes': ''
            }
            
            self.supabase.schema('peer_progress').table('support_connections').insert(connection_data).execute()
            
        except Exception as e:
            print(f"Error creating support connection: {e}")
    
    def get_group_health_dashboard(self, organization_id: str = None, weeks_back: int = 8) -> Dict:
        """Get group health dashboard data"""
        try:
            org_filter = organization_id or self.organization_id
            
            # Get recent sentiment data
            from datetime import datetime, timedelta
            weeks_ago = datetime.now().date() - timedelta(weeks=weeks_back)
            
            sentiment_result = self.supabase.schema('peer_progress').table('call_sentiment').select('*').eq('organization_id', org_filter).gte('session_date', weeks_ago.isoformat()).execute()
            
            flags_result = self.supabase.schema('peer_progress').table('group_health_flags').select('*').eq('organization_id', org_filter).gte('session_date', weeks_ago.isoformat()).execute()
            
            stuck_signals_result = self.supabase.schema('peer_progress').table('stuck_signals').select('*').eq('organization_id', org_filter).gte('session_date', weeks_ago.isoformat()).execute()
            
            help_offers_result = self.supabase.schema('peer_progress').table('help_offers').select('*').eq('organization_id', org_filter).gte('session_date', weeks_ago.isoformat()).execute()
            
            # Analyze sentiment trends
            sentiment_scores = [s['sentiment_score'] for s in sentiment_result.data]
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 3.0
            
            # Count flags by level
            critical_flags = len([f for f in flags_result.data if f['flag_level'] == 'critical'])
            warning_flags = len([f for f in flags_result.data if f['flag_level'] == 'warning'])
            
            # Count stuck signals by type
            stuck_by_type = {}
            for signal in stuck_signals_result.data:
                classification = signal['stuck_classification']
                stuck_by_type[classification] = stuck_by_type.get(classification, 0) + 1
            
            # Count help offers by type
            help_by_type = {}
            for offer in help_offers_result.data:
                classification = offer['classification']
                help_by_type[classification] = help_by_type.get(classification, 0) + 1
            
            # Find most supportive members
            supporter_counts = {}
            for offer in help_offers_result.data:
                supporter = offer['offerer_name']
                supporter_counts[supporter] = supporter_counts.get(supporter, 0) + 1
            
            top_supporters = sorted(supporter_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Find members with most stuck signals
            stuck_counts = {}
            for signal in stuck_signals_result.data:
                participant = signal['participant_name']
                stuck_counts[participant] = stuck_counts.get(participant, 0) + 1
            
            participants_with_most_stuck = sorted(stuck_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            dashboard_data = {
                'summary': {
                    'total_calls_analyzed': len(sentiment_result.data),
                    'average_sentiment': round(avg_sentiment, 2),
                    'total_flags': len(flags_result.data),
                    'critical_flags': critical_flags,
                    'warning_flags': warning_flags,
                    'total_stuck_signals': len(stuck_signals_result.data),
                    'total_help_offers': len(help_offers_result.data)
                },
                'sentiment_analysis': {
                    'recent_scores': sentiment_scores[-5:] if sentiment_scores else [],
                    'trend': 'improving' if len(sentiment_scores) > 1 and sentiment_scores[-1] > sentiment_scores[0] else 'declining',
                    'average_confidence': round(sum(s['confidence_score'] for s in sentiment_result.data) / len(sentiment_result.data), 2) if sentiment_result.data else 0.0
                },
                'stuck_analysis': {
                    'stuck_by_type': stuck_by_type,
                    'participants_with_most_stuck': participants_with_most_stuck
                },
                'support_analysis': {
                    'help_by_type': help_by_type,
                    'top_supporters': top_supporters
                },
                'health_insights': {
                    'most_common_stuck_type': max(stuck_by_type.items(), key=lambda x: x[1])[0] if stuck_by_type else 'None',
                    'most_active_supporter': top_supporters[0][0] if top_supporters else 'None',
                    'group_health_score': min(5.0, max(1.0, avg_sentiment - (critical_flags * 0.5) - (warning_flags * 0.2)))
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            print(f"Error getting group health dashboard: {e}")
            return {}
    
    def get_open_flags(self, organization_id: str = None, limit: int = 20) -> List[Dict]:
        """Get open group health flags"""
        try:
            org_filter = organization_id or self.organization_id
            
            result = self.supabase.schema('peer_progress').table('group_health_flags').select('*').eq('organization_id', org_filter).eq('status', 'open').order('created_at', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting open flags: {e}")
            return []
    
    def get_participant_support_history(self, participant_name: str, organization_id: str = None, limit: int = 10) -> Dict:
        """Get support history for a participant (given and received)"""
        try:
            org_filter = organization_id or self.organization_id
            
            # Get help offers given by this participant
            offers_given_result = self.supabase.schema('peer_progress').table('help_offers').select('*').eq('organization_id', org_filter).eq('offerer_name', participant_name).order('created_at', desc=True).limit(limit).execute()
            
            # Get stuck signals for this participant
            stuck_signals_result = self.supabase.schema('peer_progress').table('stuck_signals').select('*').eq('organization_id', org_filter).eq('participant_name', participant_name).order('created_at', desc=True).limit(limit).execute()
            
            return {
                'help_offers_given': offers_given_result.data if offers_given_result.data else [],
                'stuck_signals': stuck_signals_result.data if stuck_signals_result.data else [],
                'support_balance': len(offers_given_result.data) - len(stuck_signals_result.data) if offers_given_result.data and stuck_signals_result.data else 0
            }
            
        except Exception as e:
            print(f"Error getting participant support history: {e}")
            return {'help_offers_given': [], 'stuck_signals': [], 'support_balance': 0}
    
    def update_goal_with_source(self, goal_id: str, updated_goal_data: Dict, source_type: str, updated_by: str, source_details: Dict = None) -> bool:
        """Update a goal with source tracking information"""
        try:
            # Validate source_type
            valid_sources = ['ai_extraction', 'human_input', 'member_update', 'qa_clarification', 'system_generated']
            if source_type not in valid_sources:
                raise ValueError(f"Invalid source_type. Must be one of: {valid_sources}")
            
            # Prepare update data with source information
            update_data = {
                **updated_goal_data,
                'source_type': source_type,
                'updated_by': updated_by,
                'updated_at': 'now()',
                'source_details': source_details or {}
            }
            
            # Update the goal
            result = self.supabase.schema('peer_progress').table('quantifiable_goals').update(update_data).eq('id', goal_id).execute()
            
            if result.data:
                print(f"✅ Updated goal {goal_id} from {source_type} by {updated_by}")
                return True
            else:
                print(f"❌ Failed to update goal {goal_id}")
                return False
                
        except Exception as e:
            print(f"Error updating goal with source tracking: {e}")
            return False
    
    def update_vague_goal_with_clarification(self, vague_goal_id: str, clarification_data: Dict, updated_by: str, source_details: Dict = None) -> bool:
        """Update a vague goal with clarification from human input (e.g., QA team)"""
        try:
            # Prepare update data for vague goal
            update_data = {
                'status': 'clarified',
                'source_type': 'qa_clarification',
                'updated_by': updated_by,
                'updated_at': 'now()',
                'source_details': source_details or {
                    'clarification_method': 'human_review',
                    'qa_team_member': updated_by
                }
            }
            
            # Update the vague goal
            result = self.supabase.schema('peer_progress').table('vague_goals_detected').update(update_data).eq('id', vague_goal_id).execute()
            
            # If clarification includes a quantifiable version, create a new goal
            if 'quantifiable_goal_text' in clarification_data and 'target_number' in clarification_data:
                self._create_quantifiable_goal_from_clarification(clarification_data, vague_goal_id, updated_by)
            
            if result.data:
                print(f"✅ Updated vague goal {vague_goal_id} with clarification from {updated_by}")
                return True
            else:
                print(f"❌ Failed to update vague goal {vague_goal_id}")
                return False
                
        except Exception as e:
            print(f"Error updating vague goal with clarification: {e}")
            return False
    
    def _create_quantifiable_goal_from_clarification(self, clarification_data: Dict, vague_goal_id: str, updated_by: str):
        """Create a new quantifiable goal from clarification data"""
        try:
            # Get the original vague goal details
            vague_goal = self.supabase.schema('peer_progress').table('vague_goals_detected').select('*').eq('id', vague_goal_id).execute()
            
            if not vague_goal.data:
                return False
            
            original_goal = vague_goal.data[0]
            
            # Create new quantifiable goal
            new_goal_data = {
                'transcript_session_id': original_goal['transcript_session_id'],
                'organization_id': original_goal['organization_id'],
                'member_id': original_goal.get('member_id'),
                'participant_name': original_goal['participant_name'],
                'group_name': original_goal.get('group_name'),
                'goal_text': clarification_data['quantifiable_goal_text'],
                'target_number': clarification_data['target_number'],
                'target_unit': clarification_data.get('target_unit'),
                'goal_context': clarification_data.get('goal_context', 'Clarified from vague goal'),
                'source_type': 'qa_clarification',
                'source_details': {
                    'original_vague_goal_id': vague_goal_id,
                    'clarified_by': updated_by,
                    'clarification_method': 'human_review'
                },
                'updated_by': updated_by
            }
            
            result = self.supabase.schema('peer_progress').table('quantifiable_goals').insert(new_goal_data).execute()
            
            if result.data:
                print(f"✅ Created quantifiable goal from clarification by {updated_by}")
                return True
            else:
                print(f"❌ Failed to create quantifiable goal from clarification")
                return False
                
        except Exception as e:
            print(f"Error creating quantifiable goal from clarification: {e}")
            return False
    
    def update_goal_progress_with_source(self, goal_id: str, progress_data: Dict, source_type: str, updated_by: str, source_details: Dict = None) -> bool:
        """Update goal progress with source tracking"""
        try:
            # Validate source_type
            valid_sources = ['ai_extraction', 'human_input', 'member_update', 'qa_clarification', 'system_generated']
            if source_type not in valid_sources:
                raise ValueError(f"Invalid source_type. Must be one of: {valid_sources}")
            
            # Prepare update data with source information
            update_data = {
                **progress_data,
                'source_type': source_type,
                'updated_by': updated_by,
                'updated_at': 'now()',
                'source_details': source_details or {}
            }
            
            # Update the goal progress
            result = self.supabase.schema('peer_progress').table('goal_progress_tracking').update(update_data).eq('id', goal_id).execute()
            
            if result.data:
                print(f"✅ Updated goal progress {goal_id} from {source_type} by {updated_by}")
                return True
            else:
                print(f"❌ Failed to update goal progress {goal_id}")
                return False
                
        except Exception as e:
            print(f"Error updating goal progress with source tracking: {e}")
            return False
    
    def get_goal_update_history(self, goal_id: str) -> List[Dict]:
        """Get the update history for a specific goal"""
        try:
            # Get goal with all updates
            result = self.supabase.schema('peer_progress').table('quantifiable_goals').select('*').eq('id', goal_id).execute()
            
            if not result.data:
                return []
            
            goal = result.data[0]
            
            # Get progress tracking history
            progress_result = self.supabase.schema('peer_progress').table('goal_progress_tracking').select('*').eq('quantifiable_goal_id', goal_id).order('updated_at', desc=True).execute()
            
            history = []
            
            # Add creation event
            history.append({
                'event_type': 'goal_created',
                'timestamp': goal['created_at'],
                'source_type': goal.get('source_type', 'ai_extraction'),
                'updated_by': goal.get('updated_by', 'system'),
                'source_details': goal.get('source_details', {}),
                'changes': {
                    'goal_text': goal['goal_text'],
                    'target_number': goal['target_number']
                }
            })
            
            # Add progress updates
            for progress in progress_result.data:
                history.append({
                    'event_type': 'progress_updated',
                    'timestamp': progress['updated_at'],
                    'source_type': progress.get('source_type', 'ai_extraction'),
                    'updated_by': progress.get('updated_by', 'system'),
                    'source_details': progress.get('source_details', {}),
                    'changes': {
                        'current_value': progress['current_value'],
                        'target_value': progress['target_value'],
                        'status': progress['status']
                    }
                })
            
            return history
            
        except Exception as e:
            print(f"Error getting goal update history: {e}")
            return []
    
    def get_qa_clarification_queue(self, organization_id: str = None, limit: int = 20) -> List[Dict]:
        """Get vague goals that need QA team clarification"""
        try:
            org_filter = organization_id or self.organization_id
            
            result = self.supabase.schema('peer_progress').table('vague_goals_detected').select('*').eq('organization_id', org_filter).eq('status', 'pending_followup').order('created_at', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting QA clarification queue: {e}")
            return []
    
    def get_goal_source_analytics(self, organization_id: str = None, weeks_back: int = 8) -> Dict:
        """Get analytics about goal sources and updates"""
        try:
            org_filter = organization_id or self.organization_id
            
            # Get goals by source type
            goals_result = self.supabase.schema('peer_progress').table('quantifiable_goals').select('source_type, updated_by').eq('organization_id', org_filter).execute()
            
            # Get vague goals by source
            vague_goals_result = self.supabase.schema('peer_progress').table('vague_goals_detected').select('source_type, status').eq('organization_id', org_filter).execute()
            
            # Analyze source types
            goal_sources = {}
            for goal in goals_result.data:
                source = goal.get('source_type', 'ai_extraction')
                goal_sources[source] = goal_sources.get(source, 0) + 1
            
            vague_sources = {}
            for goal in vague_goals_result.data:
                source = goal.get('source_type', 'ai_extraction')
                vague_sources[source] = vague_sources.get(source, 0) + 1
            
            # Count by updater
            updaters = {}
            for goal in goals_result.data:
                updater = goal.get('updated_by', 'system')
                updaters[updater] = updaters.get(updater, 0) + 1
            
            return {
                'goal_sources': goal_sources,
                'vague_goal_sources': vague_sources,
                'top_updaters': sorted(updaters.items(), key=lambda x: x[1], reverse=True)[:10],
                'total_goals': len(goals_result.data),
                'total_vague_goals': len(vague_goals_result.data),
                'ai_extraction_percentage': round((goal_sources.get('ai_extraction', 0) / len(goals_result.data)) * 100, 2) if goals_result.data else 0,
                'human_input_percentage': round((goal_sources.get('human_input', 0) / len(goals_result.data)) * 100, 2) if goals_result.data else 0
            }
            
        except Exception as e:
            print(f"Error getting goal source analytics: {e}")
            return {}




def main():
    # Initialize the processor
    processor = TranscriptProcessor(organization_id='f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e')
    
    # Process yesterday's transcripts from the specific folder
    print("🔍 Looking for yesterday's transcripts...")
    yesterday_folder_url = "https://drive.google.com/drive/folders/1ku7IhbFWsYWDnYf0FJMcqOn2EIOfPnWu"
    results = processor.process_recent_transcripts(folder_url=yesterday_folder_url, days_back=7)
    
    print(f"\nProcessing Complete:")
    print(f"Successfully processed: {results['processed']}")
    print(f"Failed: {results['failed']}")
    
    if results['details']:
        print("\nDetails:")
        for detail in results['details']:
            print(f"  - {detail['filename']}: {detail['status']}")

if __name__ == "__main__":
    main()