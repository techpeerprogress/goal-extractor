import os
import re
import streamlit as st
from typing import Any, List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()


def get_supabase_client() -> Client:
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    if not url or not key:
        return None
    return create_client(url, key)


@st.cache_data(show_spinner=False, ttl=120)
def fetch_session_dates(org_id: str) -> List[str]:
    sb = get_supabase_client()
    if not sb:
        return []
    try:
        res = (
            sb.schema('peer_progress')
            .table('transcript_sessions')
            .select('session_date')
            .eq('organization_id', org_id)
            .not_.is_('session_date', 'null')
            .order('session_date', desc=True)
            .execute()
        )
        dates = [r['session_date'] for r in (res.data or []) if r.get('session_date')]
        seen, ordered = set[Any](), []
        for d in dates:
            if d not in seen:
                seen.add(d)
                ordered.append(d)
        return ordered
    except Exception:
        return []


@st.cache_data(show_spinner=True, ttl=120)
def fetch_vague_goals(org_id: str, session_date: str) -> List[Dict]:
    """Return list of dict rows with group, participant, goal_text, classification, reason."""
    sb = get_supabase_client()
    if not sb:
        return []

    # Get sessions for the date
    sessions = (
        sb.schema('peer_progress')
        .table('transcript_sessions')
        .select('id, group_name, filename, session_date')
        .eq('organization_id', org_id)
        .eq('session_date', session_date)
        .execute()
    ).data or []
    if not sessions:
        return []

    session_by_id = {s['id']: s for s in sessions}
    session_ids = list(session_by_id.keys())

    # Fetch all goals for these sessions
    goals = (
        sb.schema('peer_progress')
        .table('quantifiable_goals')
        .select('id, transcript_session_id, participant_name, goal_text, source_details')
        .in_('transcript_session_id', session_ids)
        .execute()
    ).data or []

    # Filter to vague-like: not_quantifiable, no_goal, decision_pending
    rows = []
    for g in goals:
        details = g.get('source_details') or {}
        cls = (details.get('classification') or '').lower()
        if cls in ('not_quantifiable', 'no_goal', 'decision_pending'):
            sid = g['transcript_session_id']
            sess = session_by_id.get(sid, {})
            rows.append({
                'id': g.get('id'),
                'group_name': sess.get('group_name') or sess.get('filename') or 'Unknown',
                'session_date': sess.get('session_date'),
                'participant_name': g.get('participant_name', 'Unknown'),
                'classification': details.get('classification', 'not_quantifiable'),
                'goal_text': g.get('goal_text', ''),
                'reason': details.get('classification_reason', ''),
            })
    return rows


def badge_for_classification(cls: str) -> str:
    c = (cls or '').lower()
    if c == 'not_quantifiable':
        return '❌ Not Quantifiable'
    if c == 'no_goal':
        return '⚪ No Goal'
    if c == 'decision_pending':
        return '🤔 Decision Pending'
    return cls or 'N/A'


def update_goal(goal_id: str, new_text: str, new_classification: str, source_type: str, note: str = "") -> bool:
    """Update a goal with new text/classification and set the source of update."""
    sb = get_supabase_client()
    if not sb or not goal_id:
        return False
    # Merge existing source_details with update metadata
    try:
        existing = sb.schema('peer_progress').table('quantifiable_goals').select('source_details').eq('id', goal_id).execute()
        existing_details = (existing.data[0].get('source_details') if existing.data else {}) or {}
        from datetime import datetime
        updates_meta = existing_details.get('updates', [])
        updates_meta.append({
            'at': datetime.utcnow().isoformat() + 'Z',
            'source': source_type,
            'note': note or 'updated from Vague Goals UI',
        })
        existing_details['updates'] = updates_meta
        # Preserve prior discussion/classification_reason, but set classification for quick use
        existing_details['classification'] = new_classification

        data = {
            'goal_text': new_text,
            'source_type': source_type,
            'source_details': existing_details,
        }
        res = sb.schema('peer_progress').table('quantifiable_goals').update(data).eq('id', goal_id).execute()
        return bool(res.data)
    except Exception:
        return False


def main():
    st.set_page_config(page_title='Vague Goals', page_icon='📝', layout='wide')

    st.title('📝 Vague Goals')
    st.caption('See who has vague goals (or no goal) and why.')
    st.divider()

    org_id = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e'
    sb = get_supabase_client()
    if not sb:
        st.error('❌ Could not connect to Supabase. Check SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.')
        return

    # Date selector (cached)
    dates = fetch_session_dates(org_id)
    if not dates:
        st.info('No sessions available yet. Run the extractor to populate data.')
        return

    selected_date = st.sidebar.selectbox('📅 Session Date', dates, index=0)

    rows = fetch_vague_goals(org_id, selected_date)
    if not rows:
        st.info('No vague goals for the selected date.')
        return

    # Summary
    st.subheader(f'Summary · {selected_date}')
    total = len(rows)
    not_q = sum(1 for r in rows if r['classification'] == 'not_quantifiable')
    no_goal = sum(1 for r in rows if r['classification'] == 'no_goal')
    pending = sum(1 for r in rows if r['classification'] == 'decision_pending')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Total Vague Items', total)
    c2.metric('❌ Not Quantifiable', not_q)
    c3.metric('⚪ No Goal', no_goal)
    c4.metric('🤔 Decision Pending', pending)
    st.divider()

    # Group by group_name for readability
    from collections import defaultdict
    by_group = defaultdict[Any, list](list)
    for r in rows:
        by_group[r['group_name']].append(r)

    for group_name, items in by_group.items():
        with st.expander(f"👥 {group_name} · {selected_date} · {len(items)} item(s)", expanded=False):
            for r in items:
                st.markdown(f"#### {r['participant_name']}")
                st.markdown(f"**Classification:** {badge_for_classification(r['classification'])}")
                if r['goal_text']:
                    st.markdown(f"**Commitment:** {r['goal_text']}")
                if r['reason']:
                    st.markdown(f"**Why:** {r['reason']}")
                with st.popover("Update goal", use_container_width=True):
                    new_text = st.text_area("New/clarified goal", value=r['goal_text'], key=f"txt_{r['id']}", height=100)
                    colu1, colu2 = st.columns(2)
                    with colu1:
                        new_cls = st.selectbox(
                            "Classification",
                            options=["quantifiable", "not_quantifiable", "no_goal", "decision_pending"],
                            index=["quantifiable", "not_quantifiable", "no_goal", "decision_pending"].index(r['classification']),
                            key=f"cls_{r['id']}"
                        )
                    with colu2:
                        src = st.radio("Source", options=["human_input", "ai_extraction"], index=0, key=f"src_{r['id']}")
                    note = st.text_input("Note (optional)", key=f"note_{r['id']}")
                    if st.button("Save update", key=f"btn_{r['id']}"):
                        ok = update_goal(r['id'], new_text, new_cls, src, note)
                        if ok:
                            st.success("Saved. Refresh the page to see changes reflected.")
                            # Invalidate caches so a rerun reflects changes quickly
                            fetch_vague_goals.clear()
                            fetch_session_dates.clear()
                        else:
                            st.error("Failed to save the update.")
                st.markdown("---")


if __name__ == '__main__':
    main()


