import os
import streamlit as st
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def sb() -> Client:
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    if not url or not key:
        return None
    return create_client(url, key)


@st.cache_data(ttl=120)
def dates(org_id: str) -> List[str]:
    client = sb()
    if not client:
        return []
    res = (
        client.schema('peer_progress')
        .table('transcript_sessions')
        .select('session_date')
        .eq('organization_id', org_id)
        .not_.is_('session_date', 'null')
        .order('session_date', desc=True)
        .execute()
    )
    vals = [r['session_date'] for r in (res.data or []) if r.get('session_date')]
    seen, out = set(), []
    for d in vals:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


@st.cache_data(ttl=120)
def fetch(org_id: str, date: str) -> List[Dict]:
    client = sb()
    if not client:
        return []
    sess = (
        client.schema('peer_progress')
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
        client.schema('peer_progress')
        .table('transcript_analysis')
        .select('transcript_session_id, challenges_strategies_json')
        .in_('transcript_session_id', ids)
        .execute()
    ).data or []
    rows = []
    for a in ana:
        sid = a['transcript_session_id']
        meta = by_id.get(sid, {})
        rows.append({
            'group_name': meta.get('group_name') or meta.get('filename') or 'Unknown',
            'items': a.get('challenges_strategies_json') or [],
        })
    return rows


def main():
    st.set_page_config(page_title='Challenges & Strategies', page_icon='🧠', layout='wide')
    st.title('🧠 Challenges & Strategies')
    st.caption('Per participant: challenge summary, category, and tips shared during the call.')
    st.divider()

    org = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e'
    if not sb():
        st.error('❌ Supabase not configured (SUPABASE_URL/SERVICE_KEY).')
        return

    ds = dates(org)
    if not ds:
        st.info('No session dates found. Run challenges_extractor.py first.')
        return
    d = st.sidebar.selectbox('📅 Session Date', ds, index=0)

    data = fetch(org, d)
    if not data:
        st.info('No challenges/strategies found for this date.')
        return

    for row in data:
        st.subheader(f"👥 {row['group_name']} · {d}")
        items = row['items']
        if not items:
            st.write('No entries')
            st.divider()
            continue
        for it in items:
            st.markdown(f"#### {it.get('name','Unknown')}")
            if it.get('category'):
                st.markdown(f"**Category:** {it['category']}")
            if it.get('challenge'):
                st.markdown(f"**Challenge:** {it['challenge']}")
            tips = it.get('tips') or []
            if tips:
                st.markdown('**Strategies/Tips:**')
                for t in tips:
                    who = t.get('who') or 'Someone'
                    tag = f" ({t['tag']})" if t.get('tag') else ''
                    st.markdown(f"- {who}: {t.get('tip','')}{tag}")
            st.markdown('---')
        st.divider()


if __name__ == '__main__':
    main()


