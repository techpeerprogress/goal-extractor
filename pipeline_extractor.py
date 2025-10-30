"""Extract strict-window pipeline outcomes and save to peer_progress.activity_events.

Writes standardized rows:
- subtype: meeting_booked | proposal_sent | client_closed
- marketing_channel: linkedin | network_activation | cold_outreach
- note: exact quote (with timestamp if available) + outcome text
- ts: call_date if unknown per item
"""

import os
import re
from typing import List, Dict, Optional
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client, Client

from main import TranscriptProcessor
from goal_extractor import _get_files_recursively, _ensure_group as ensure_group, _ensure_member as ensure_member
from ai_llm_fallback import ai_generate_content


load_dotenv()


def _load_prompt(rel_path: str) -> str:
    p = os.path.join(os.path.dirname(__file__), rel_path)
    with open(p, 'r', encoding='utf-8') as f:
        return f.read().replace('[Transcript goes here]', '{transcript}')


PROMPT = _load_prompt('prompts/pipeline_strict.md')


def _parse_blocks(text: str) -> List[Dict]:
    blocks = re.split(r'(?=^Name:\s*)', text.strip(), flags=re.MULTILINE)
    out: List[Dict] = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        m_name = re.search(r'^Name:\s*(.+)$', b, flags=re.MULTILINE)
        m_stage = re.search(r'^Stage:\s*(.+)$', b, flags=re.MULTILINE)
        m_channel = re.search(r'^Marketing Activity:\s*(.+)$', b, flags=re.MULTILINE)
        m_outcome = re.search(r'^Win / Outcome:\s*(.+)$', b, flags=re.MULTILINE)
        m_quote = re.search(r'^Quote:\s*"([\s\S]+?)"\s*$', b, flags=re.MULTILINE)
        name = m_name.group(1).strip() if m_name else 'Unknown'
        stage = (m_stage.group(1).strip().lower() if m_stage else '')
        channel = (m_channel.group(1).strip().lower() if m_channel else '')
        outcome = m_outcome.group(1).strip() if m_outcome else ''
        quote = m_quote.group(1).strip() if m_quote else ''
        out.append({'name': name, 'stage': stage, 'channel': channel, 'outcome': outcome, 'quote': quote})
    return out


def _stage_to_subtype(stage: str) -> Optional[str]:
    s = (stage or '').lower()
    if 'closed' in s:
        return 'client_closed'
    if 'proposal' in s:
        return 'proposal_sent'
    if 'meeting' in s:
        return 'meeting_booked'
    return None


def _channel_to_db(ch: str) -> Optional[str]:
    c = (ch or '').lower()
    if 'linkedin' in c:
        return 'linkedin'
    if 'network' in c:
        return 'network_activation'
    if 'cold' in c:
        return 'cold_outreach'
    return None


def extract_pipeline(folder_url: Optional[str] = None,
                     organization_id: str = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e',
                     days_back: Optional[int] = None,
                     recursive: bool = True) -> None:
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
            # derive session date
            mod = f.get('modifiedTime') or ''
            try:
                call_date = datetime.fromisoformat(mod.replace('Z', '+00:00')).date().isoformat()
            except Exception:
                call_date = None
            # run LLM
            text = ai_generate_content(PROMPT.format(transcript=content))
            rows = _parse_blocks(text)
            group_id = ensure_group(sb, fname)
            for r in rows:
                subtype = _stage_to_subtype(r['stage'])
                channel = _channel_to_db(r['channel'])
                if not subtype:
                    continue
                member_id = ensure_member(sb, r['name'], fname)
                if not member_id or not group_id:
                    continue
                note = (r['outcome'] + ' | ' + r['quote']).strip()[:500]
                payload = {
                    'member_id': member_id,
                    'group_id': group_id,
                    'subtype': subtype,
                    'marketing_channel': channel,
                    'count': 1,
                    'ts': call_date + 'T00:00:00Z' if call_date else None,
                    'source': 'transcript',
                    'note': note
                }
                sb.schema('peer_progress').table('activity_events').insert(payload).execute()
            print(f'  ✓ Saved {len(rows)} pipeline entries')
        except Exception as e:
            print(f'  ✗ Error: {e}')


if __name__ == '__main__':
    folder = os.getenv('GOOGLE_DRIVE_FOLDER_URL')
    extract_pipeline(folder_url=folder, days_back=None, recursive=True)


