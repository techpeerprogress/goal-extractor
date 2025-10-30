"""
Extract marketing activities and pipeline outcomes from transcripts
and save structured JSON into peer_progress.transcript_analysis.

This does not alter existing goals data. It attaches analysis payloads
to the session via transcript_analysis rows for each session.
"""

import os
import re
from typing import Dict, List, Optional
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client, Client
from ai_llm_fallback import ai_generate_content

from main import TranscriptProcessor
from goal_extractor import _get_files_recursively  # reuse folder crawl
from goal_extractor import _ensure_group as _ensure_group_ref, _ensure_member as _ensure_member_ref


load_dotenv()


def _load_prompt(path: str, placeholder: str = '{transcript}') -> str:
    p = os.path.join(os.path.dirname(__file__), path)
    with open(p, 'r', encoding='utf-8') as f:
        return f.read().replace('[Transcript goes here]', placeholder)


PROMPT_ACTIVITY = _load_prompt('prompts/marketing_activity.md')
PROMPT_OUTCOMES = _load_prompt('prompts/pipeline_outcomes.md')


def _parse_activity_block(text: str) -> Dict[str, Dict[str, str]]:
    """Parse the activity output for a single participant block.
    Returns {'name': str, 'network_activation': str, 'linkedin': str, 'cold_outreach': str, 'none': bool}
    """
    name_match = re.search(r'^Name:\s*(.+)', text, re.MULTILINE)
    name = name_match.group(1).strip() if name_match else 'Unknown'
    if 'No marketing activity mentioned' in text:
        return {'name': name, 'network_activation': '', 'linkedin': '', 'cold_outreach': '', 'none': True}

    def _line_for(label: str) -> str:
        m = re.search(rf'^-\s*{label}:\s*(.+)$', text, re.MULTILINE)
        return m.group(1).strip() if m else ''

    return {
        'name': name,
        'network_activation': _line_for('Network Activation'),
        'linkedin': _line_for('LinkedIn'),
        'cold_outreach': _line_for('Cold Outreach'),
        'none': False,
    }


def _parse_outcome_block(text: str) -> Dict[str, str]:
    name_match = re.search(r'^Name:\s*(.+)', text, re.MULTILINE)
    name = name_match.group(1).strip() if name_match else 'Unknown'
    def _num(label: str) -> int:
        m = re.search(rf'^{label}:\s*(\d+)', text, re.MULTILINE)
        return int(m.group(1)) if m else 0
    notes_match = re.search(r'^Notes:\s*(.+)', text, re.MULTILINE)
    return {
        'name': name,
        'meetings': _num('Meetings'),
        'proposals': _num('Proposals'),
        'clients': _num('Clients'),
        'notes': notes_match.group(1).strip() if notes_match else '',
    }


def _parse_multi_blocks(text: str, parse_fn) -> List[Dict]:
    # Split by occurrences starting with Name:
    blocks = re.split(r'(?=^Name:\s*)', text, flags=re.MULTILINE)
    items: List[Dict] = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        try:
            items.append(parse_fn(b))
        except Exception:
            continue
    return items


def _save_analysis(supabase: Client, session_id: str, org_id: str, activities: List[Dict], outcomes: List[Dict]) -> None:
    # Upsert transcript_analysis row per session
    payload = {
        'marketing_activities_json': activities,
        'pipeline_outcomes_json': outcomes,
        'processing_status': 'completed',
        'organization_id': org_id,
    }
    # Try update then insert
    existing = supabase.schema('peer_progress').table('transcript_analysis').select('id').eq('transcript_session_id', session_id).execute()
    if existing.data:
        supabase.schema('peer_progress').table('transcript_analysis').update(payload).eq('id', existing.data[0]['id']).execute()
    else:
        payload['transcript_session_id'] = session_id
        supabase.schema('peer_progress').table('transcript_analysis').insert(payload).execute()


def _record_activity_rows(sb: Client, group_code: str, session_date: str, activities: List[Dict], outcomes: List[Dict]) -> None:
    """Persist activity table rows based on parsed marketing activities and pipeline outcomes."""
    group_id = _ensure_group_ref(sb, group_code)
    # Activities: per participant
    for a in activities or []:
        name = a.get('name') or 'Unknown'
        member_id = _ensure_member_ref(sb, name, group_code)
        if not member_id or not group_id:
            continue
        if a.get('none'):
            continue
        # Map categories to channel marketing_touch
        if a.get('network_activation'):
            sb.schema('peer_progress').table('activity_events').insert({
                'member_id': member_id,
                'group_id': group_id,
                'subtype': 'marketing_touch',
                'count': 1,
                'channel': 'network_activation',
                'ts': session_date + 'T00:00:00Z' if session_date else None,
                'source': 'transcript',
                'note': a['network_activation'][:250]
            }).execute()
        if a.get('linkedin'):
            sb.schema('peer_progress').table('activity_events').insert({
                'member_id': member_id,
                'group_id': group_id,
                'subtype': 'marketing_touch',
                'count': 1,
                'channel': 'linkedin',
                'ts': session_date + 'T00:00:00Z' if session_date else None,
                'source': 'transcript',
                'note': a['linkedin'][:250]
            }).execute()
        if a.get('cold_outreach'):
            sb.schema('peer_progress').table('activity_events').insert({
                'member_id': member_id,
                'group_id': group_id,
                'subtype': 'marketing_touch',
                'count': 1,
                'channel': 'cold_outreach',
                'ts': session_date + 'T00:00:00Z' if session_date else None,
                'source': 'transcript',
                'note': a['cold_outreach'][:250]
            }).execute()
    # Outcomes: meetings, proposals, clients (counts)
    for o in outcomes or []:
        name = o.get('name') or 'Unknown'
        member_id = _ensure_member_ref(sb, name, group_code)
        if not member_id or not group_id:
            continue
        def _ins(subtype: str, count_val: int):
            if count_val and count_val > 0:
                sb.schema('peer_progress').table('activity_events').insert({
                    'member_id': member_id,
                    'group_id': group_id,
                    'subtype': subtype,
                    'count': int(count_val),
                    'ts': session_date + 'T00:00:00Z' if session_date else None,
                    'source': 'transcript',
                    'note': (o.get('notes') or '')[:250]
                }).execute()
        _ins('meeting_booked', int(o.get('meetings', 0)))
        _ins('proposal_sent', int(o.get('proposals', 0)))
        _ins('client_closed', int(o.get('clients', 0)))


def extract_marketing(organization_id: str = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e',
                      folder_url: Optional[str] = None,
                      days_back: Optional[int] = None,
                      recursive: bool = True) -> None:

    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
    processor = TranscriptProcessor(organization_id=organization_id)

    files = _get_files_recursively(processor, folder_url, days_back) if recursive else processor.get_recent_transcripts(folder_url, days_back or 30)
    if not files:
        print('No files found')
        return

    for f in files:
        name = f['name']
        print(f"Processing: {name}")
        try:
            content = processor.download_and_read_file(f['id'], name, f['mimeType'])
            if not content.strip():
                continue
            # Derive session_date & create/find session to attach analysis to
            mod = f.get('modifiedTime') or ''
            try:
                session_date = datetime.fromisoformat(mod.replace('Z', '+00:00')).date().isoformat()
            except Exception:
                session_date = None
            session_rec = processor.create_transcript_session(filename=name, group_name=name, session_date=session_date, raw_transcript=None)
            session_id = session_rec['id'] if session_rec else None
            if not session_id:
                print('  ✗ could not create/find session')
                continue

            # Use LLM (Gemini or ChatGPT) for activities
            act_text = ai_generate_content(PROMPT_ACTIVITY.format(transcript=content))
            activities = _parse_multi_blocks(act_text, _parse_activity_block)

            # Use LLM for outcomes
            out_text = ai_generate_content(PROMPT_OUTCOMES.format(transcript=content))
            outcomes = _parse_multi_blocks(out_text, _parse_outcome_block)

            _save_analysis(supabase, session_id, organization_id, activities, outcomes)
            # Also persist normalized activity rows for KPIs
            session_date_str = session_date or None
            _record_activity_rows(supabase, name, session_date_str, activities, outcomes)
            print(f"  ✓ Saved analysis for session {session_id}")
        except Exception as e:
            print(f"  ✗ Error: {e}")


if __name__ == '__main__':
    # Example: run against October folder env var if set
    folder = os.getenv('GOOGLE_DRIVE_FOLDER_URL')
    extract_marketing(folder_url=folder, days_back=None, recursive=True)


