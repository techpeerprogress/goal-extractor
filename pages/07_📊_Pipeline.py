import os
import streamlit as st
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone

load_dotenv()


def sb() -> Client:
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    if not url or not key:
        return None
    return create_client(url, key)


def timeframe_range(tf: str):
    now = datetime.now(timezone.utc)
    tf = (tf or 'This Week').lower()
    if tf.startswith('last'):
        start = now - timedelta(days=14)
        end = now - timedelta(days=7)
        return start, end
    if tf.startswith('this'):
        return now - timedelta(days=7), now + timedelta(days=7)
    if tf.startswith('next'):
        start = now + timedelta(days=0)
        end = now + timedelta(days=14)
        return start, end
    return None, None


@st.cache_data(ttl=120)
def fetch_pipeline(_sb: Client, tf_label: str, stage_filter: str) -> List[Dict]:
    start, end = timeframe_range(tf_label)
    # Select all columns to tolerate schema diffs (no assumptions about group_id/ts)
    q = _sb.schema('peer_progress').table('activity_events').select('*')
    rows = (q.execute().data) or []

    # Stage filter
    if stage_filter != 'All':
        mapping = {'Meetings': 'meeting_booked', 'Proposals': 'proposal_sent', 'Closed Client': 'client_closed'}
        target = mapping.get(stage_filter)
        rows = [r for r in rows if (r.get('subtype') or r.get('type') or r.get('event_type')) == target]

    # Time filter in Python using any timestamp-like field
    def _row_ts(r: Dict):
        ts = r.get('ts') or r.get('created_at') or r.get('timestamp')
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return None
    if start or end:
        filtered: List[Dict] = []
        for r in rows:
            tsv = _row_ts(r)
            if not tsv:
                continue
            if start and tsv < start:
                continue
            if end and tsv > end:
                continue
            filtered.append(r)
        rows = filtered

    return rows


def main():
    st.set_page_config(page_title='Pipeline', page_icon='📊', layout='wide')
    st.title('📊 Pipeline (3‑week window)')
    st.caption('Closed Clients → Proposals → Meetings. Entries parsed from transcripts.')
    st.divider()

    client = sb()
    if not client:
        st.error('❌ Supabase not configured.')
        return

    left, right = st.columns(2)
    tf = left.selectbox('Window', ['Last Week', 'This Week', 'Next Week'], index=1)
    stage = right.selectbox('Stage', ['All', 'Closed Client', 'Proposals', 'Meetings'], index=0)

    rows = fetch_pipeline(client, tf, stage)
    if not rows:
        st.info('No pipeline outcomes in the selected window.')
        return

    # Order by priority and ts
    priority = {'client_closed': 0, 'proposal_sent': 1, 'meeting_booked': 2}
    def _key(r):
        p = priority.get(r.get('subtype'), 3)
        ts = r.get('ts') or ''
        return (p, ts)
    rows = sorted(rows, key=_key)

    # Render
    for r in rows:
        st.markdown(f"**{r.get('subtype','?')}** · {r.get('marketing_channel') or r.get('channel') or 'unknown'}")
        st.caption(r.get('note','').strip())
        st.markdown('---')


if __name__ == '__main__':
    main()


