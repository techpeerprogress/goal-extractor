"""Extract Challenges & Strategies per participant and save to transcript_analysis.challenges_strategies_json"""

import os
import re
from typing import List, Dict
from datetime import datetime

from dotenv import load_dotenv
import google.generativeai as genai
from supabase import create_client, Client

from main import TranscriptProcessor
from goal_extractor import _get_files_recursively


load_dotenv()


def _load_prompt(rel_path: str) -> str:
    p = os.path.join(os.path.dirname(__file__), rel_path)
    with open(p, 'r', encoding='utf-8') as f:
        return f.read().replace('[Transcript goes here]', '{transcript}')


PROMPT = _load_prompt('prompts/challenges_strategies.md')


def _parse_response(text: str) -> List[Dict]:
    # Split on Name: lines
    parts = re.split(r'(?=^Name:\s*)', text.strip(), flags=re.MULTILINE)
    items: List[Dict] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        name_m = re.search(r'^Name:\s*(.+)$', part, flags=re.MULTILINE)
        chall_m = re.search(r'^Challenge:\s*(.+)$', part, flags=re.MULTILINE)
        cat_m = re.search(r'^Category:\s*(.+)$', part, flags=re.MULTILINE)
        tips_m = re.search(r'^Strategies/Tips:\s*\n([\s\S]+)$', part, flags=re.MULTILINE)

        name = name_m.group(1).strip() if name_m else 'Unknown'
        challenge = chall_m.group(1).strip() if chall_m else ''
        category = cat_m.group(1).strip() if cat_m else ''
        tips_block = tips_m.group(1) if tips_m else ''
        tips: List[Dict] = []
        for line in tips_block.splitlines():
            line = line.strip('- ').strip()
            if not line:
                continue
            # pattern: <who>, <tip> (<tag>)
            who = None
            tag = None
            tip_text = line
            tag_m = re.search(r'\(([^\)]+)\)\s*$', line)
            if tag_m:
                tag = tag_m.group(1).strip()
                tip_text = line[:tag_m.start()].strip()
            if ',' in tip_text:
                parts2 = tip_text.split(',', 1)
                who = parts2[0].strip()
                tip_text = parts2[1].strip()
            tips.append({'who': who, 'tip': tip_text, 'tag': tag})

        items.append({'name': name, 'challenge': challenge, 'category': category, 'tips': tips})
    return items


def _save(sb: Client, session_id: str, org_id: str, items: List[Dict]) -> None:
    payload = {
        'challenges_strategies_json': items,
        'organization_id': org_id,
        'processing_status': 'completed',
    }
    existing = sb.schema('peer_progress').table('transcript_analysis').select('id').eq('transcript_session_id', session_id).execute()
    if existing.data:
        sb.schema('peer_progress').table('transcript_analysis').update(payload).eq('id', existing.data[0]['id']).execute()
    else:
        payload['transcript_session_id'] = session_id
        sb.schema('peer_progress').table('transcript_analysis').insert(payload).execute()


def extract_challenges(folder_url: str | None = None,
                       organization_id: str = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e',
                       days_back: int | None = None,
                       recursive: bool = True) -> None:
    genai.configure(api_key=os.getenv('GOOGLE_AI_API_KEY'))
    model = genai.GenerativeModel('gemini-2.5-pro')
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
    processor = TranscriptProcessor(organization_id=organization_id)

    files = _get_files_recursively(processor, folder_url, days_back) if recursive else processor.get_recent_transcripts(folder_url, days_back or 30)
    if not files:
        print('No files found')
        return

    for f in files:
        fname = f['name']
        print(f'Processing: {fname}')
        try:
            content = processor.download_and_read_file(f['id'], fname, f['mimeType'])
            if not content.strip():
                continue
            # session derive
            mod = f.get('modifiedTime') or ''
            try:
                session_date = datetime.fromisoformat(mod.replace('Z', '+00:00')).date().isoformat()
            except Exception:
                session_date = None
            session_rec = processor.create_transcript_session(filename=fname, group_name=fname, session_date=session_date, raw_transcript=None)
            if not session_rec:
                print('  ✗ could not create/find session')
                continue

            resp = model.generate_content(PROMPT.format(transcript=content))
            items = _parse_response(resp.text)
            _save(sb, session_rec['id'], organization_id, items)
            print(f'  ✓ Saved {len(items)} items')
        except Exception as e:
            print(f'  ✗ Error: {e}')


if __name__ == '__main__':
    folder = os.getenv('GOOGLE_DRIVE_FOLDER_URL')
    extract_challenges(folder_url=folder, days_back=None, recursive=True)


