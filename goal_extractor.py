"""
Simple script to extract quantifiable goals from transcripts.
Reads transcripts (excluding Main Room), extracts quantifiable goals using Gemini, saves to txt file.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
from main import TranscriptProcessor

load_dotenv()

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

def extract_goals_for_all_transcripts(folder_url=None, days_back=30):
    """Extract quantifiable goals from all transcripts and save to file"""
    
    # Setup Gemini
    genai.configure(api_key=os.getenv('GOOGLE_AI_API_KEY'))
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    # Use existing processor for Google Drive access
    processor = TranscriptProcessor(organization_id='f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e')
    
    # Get transcripts (excluding Main Room)
    print("Getting transcripts...")
    url = "https://drive.google.com/drive/folders/1Cess2d0pndMdBZ9Us16S8vZUSvnWHiUa?usp=drive_link"
    files = processor.get_recent_transcripts(folder_url=url, days_back=30)
    files = [f for f in files if 'Main Room' not in f.get('name', '')]
    
    print(f"Found {len(files)} transcripts\n")
    
    all_results = []
    
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
            
            # Extract goals with Gemini
            response = model.generate_content(PROMPT.format(transcript=content))
            
            # Add to results
            all_results.append(f"\n{'='*80}\n")
            all_results.append(f"File: {filename}\n")
            all_results.append(f"Session Date: {session_date}\n")
            all_results.append(f"{'='*80}\n\n")
            all_results.append(response.text)
            all_results.append("\n\n")
            
            print("  ✓ Done")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_results.append(f"\nError processing {filename}: {e}\n\n")
    
    # Save to file
    output_file = "quantifiable_goals.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("QUANTIFIABLE GOALS EXTRACTED\n\n")
        f.write("".join(all_results))
    
    print(f"\n✓ Saved to {output_file}")

if __name__ == "__main__":
    extract_goals_for_all_transcripts(
        folder_url=os.getenv('GOOGLE_DRIVE_FOLDER_URL'),
        days_back=30
    )
