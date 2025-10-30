"""
Extract stuck/frustrated/support-needed signals from transcripts
and save structured JSON into peer_progress.transcript_analysis.stuck_signals_json.
"""

import os
import re
from typing import List, Dict
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client, Client

from main import TranscriptProcessor
from goal_extractor import _get_files_recursively
from ai_llm_fallback import ai_generate_content


load_dotenv()


def _load_prompt(path: str) -> str:
    p = os.path.join(os.path.dirname(__file__), path)
    with open(p, 'r', encoding='utf-8') as f:
        return f.read().replace('[Transcript goes here]', '{transcript}')


PROMPT_STUCK = _load_prompt('prompts/stuck_signals.md')


def _parse_stuck_blocks(text: str) -> List[Dict]:
    # Split blocks by participant header: a line on its own in brackets or normal name lines
    blocks = re.split(r'(?=^\[.*?\]$)|(?=^[A-Z].*\nStuck Summary:)', text, flags=re.MULTILINE)
    items: List[Dict] = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        # name could be in [NAME] or first line before Stuck Summary
        name = None
        m1 = re.match(r'^\[(.+?)\]\s*$', b)
        if m1:
            name = m1.group(1).strip()
        else:
            m2 = re.match(r'^(.+?)\nStuck Summary:', b, flags=re.DOTALL)
            if m2:
                name = m2.group(1).strip()
        if not name:
            continue

        def _section(label: str) -> str:
            m = re.search(rf'{label}:\n(.+?)(?:\n[A-Z][a-zA-Z ]+:|\Z)', b, flags=re.DOTALL)
            return m.group(1).strip() if m else ''

        summary = _section('Stuck Summary')
        quotes_raw = _section('Exact Quotes')
        quotes = [q.strip('" ').strip() for q in re.findall(r'"(.+?)"', quotes_raw)] or [q.strip() for q in quotes_raw.split('\n') if q.strip().startswith('-')]
        timestamp = _section('Timestamp')
        classification = _section('Stuck Classification')
        nudge = _section('Potential Next Step or Nudge \(Optional\)')

        items.append({
            'name': name,
            'summary': summary,
            'quotes': quotes[:3],
            'timestamp': timestamp,
            'classification': classification,
            'nudge': nudge,
        })
    return items


def _save_stuck(supabase: Client, session_id: str, org_id: str, stuck_items: List[Dict]) -> None:
    payload = {
        'stuck_signals_json': stuck_items,
        'organization_id': org_id,
        'processing_status': 'completed',
    }
    existing = supabase.schema('peer_progress').table('transcript_analysis').select('id').eq('transcript_session_id', session_id).execute()
    if existing.data:
        supabase.schema('peer_progress').table('transcript_analysis').update(payload).eq('id', existing.data[0]['id']).execute()
    else:
        payload['transcript_session_id'] = session_id
        supabase.schema('peer_progress').table('transcript_analysis').insert(payload).execute()


def extract_stuck(organization_id: str = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e',
                  folder_url: str | None = None,
                  days_back: int | None = None,
                  recursive: bool = True) -> None:

    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
    processor = TranscriptProcessor(organization_id=organization_id)

    files = _get_files_recursively(processor, folder_url, days_back) if recursive else processor.get_recent_transcripts(folder_url, days_back or 30)
    if not files:
        print('No files found')
        return

    for f in files:
        name = f['name']
        print(f'Processing: {name}')
        try:
            content = processor.download_and_read_file(f['id'], name, f['mimeType'])
            if not content.strip():
                continue
            # derive session
            mod = f.get('modifiedTime') or ''
            try:
                session_date = datetime.fromisoformat(mod.replace('Z', '+00:00')).date().isoformat()
            except Exception:
                session_date = None
            session_rec = processor.create_transcript_session(filename=name, group_name=name, session_date=session_date, raw_transcript=None)
            if not session_rec:
                print('  ✗ could not create/find session')
                continue

            stuck_text = ai_generate_content(PROMPT_STUCK.format(transcript=content))
            stuck_items = _parse_stuck_blocks(stuck_text)
            _save_stuck(supabase, session_rec['id'], organization_id, stuck_items)
            print(f'  ✓ Saved {len(stuck_items)} stuck signals')
        except Exception as e:
            print(f'  ✗ Error: {e}')


if __name__ == '__main__':
    folder = os.getenv('GOOGLE_DRIVE_FOLDER_URL')
    extract_stuck(folder_url=folder, days_back=None, recursive=True)


