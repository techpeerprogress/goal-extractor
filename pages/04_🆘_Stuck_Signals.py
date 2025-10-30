import os
import streamlit as st
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def get_sb() -> Client:
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    if not url or not key:
        return None
    return create_client(url, key)


@st.cache_data(ttl=120)
def session_dates(org_id: str) -> List[str]:
    sb = get_sb()
    if not sb:
        return []
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
    seen, out = set(), []
    for d in dates:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


@st.cache_data(ttl=120)
def fetch_stuck(org_id: str, date: str) -> List[Dict]:
    sb = get_sb()
    if not sb:
        return []
    sess = (
        sb.schema('peer_progress')
        .table('transcript_sessions')
        .select('id, group_name, filename')
        .eq('organization_id', org_id)
        .eq('session_date', date)
        .execute()
    ).data or []
    if not sess:
        return []
    by_id = {s['id']: s for s in sess}
    ids = list(by_id.keys())
    ana = (
        sb.schema('peer_progress')
        .table('transcript_analysis')
        .select('transcript_session_id, stuck_signals_json')
        .in_('transcript_session_id', ids)
        .execute()
    ).data or []
    rows = []
    for a in ana:
        sid = a['transcript_session_id']
        sess_meta = by_id.get(sid, {})
        rows.append({
            'group_name': sess_meta.get('group_name') or sess_meta.get('filename') or 'Unknown',
            'signals': a.get('stuck_signals_json') or [],
        })
    return rows


def main():
    st.set_page_config(page_title='Stuck Signals', page_icon='🆘', layout='wide')
    st.title('🆘 Stuck / Support Needed')
    st.caption('Detects and summarizes stuck moments per participant with quotes and timestamps.')
    st.divider()

    org_id = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e'
    if not get_sb():
        st.error('❌ Supabase not configured (SUPABASE_URL/SERVICE_KEY).')
        return

    dates = session_dates(org_id)
    if not dates:
        st.info('No session dates found. Run stuck_extractor.py first.')
        return
    date = st.sidebar.selectbox('📅 Session Date', dates, index=0)

    data = fetch_stuck(org_id, date)
    if not data:
        st.info('No stuck signals found for this date.')
        return

    for row in data:
        st.subheader(f"👥 {row['group_name']} · {date}")
        signals = row['signals']
        if not signals:
            st.write('No signals')
            st.divider()
            continue
        for s in signals:
            st.markdown(f"#### {s.get('name','Unknown')}")
            if s.get('classification'):
                st.markdown(f"**Classification:** {s['classification']}")
            if s.get('summary'):
                st.markdown(f"**Stuck Summary:** {s['summary']}")
            if s.get('quotes'):
                st.markdown("**Exact Quotes:**")
                for q in s['quotes']:
                    st.markdown(f"> {q}")
            if s.get('timestamp'):
                st.markdown(f"**Timestamp:** {s['timestamp']}")
            if s.get('nudge'):
                st.markdown(f"**Nudge:** {s['nudge']}")
            st.markdown('---')
        st.divider()


if __name__ == '__main__':
    main()


