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
def fetch_analysis(org_id: str, date: str) -> List[Dict]:
    sb = get_sb()
    if not sb:
        return []
    # find session ids for date
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
    # load transcript_analysis rows (activities & outcomes json stored here)
    ana = (
        sb.schema('peer_progress')
        .table('transcript_analysis')
        .select('transcript_session_id, marketing_activities_json, pipeline_outcomes_json')
        .in_('transcript_session_id', ids)
        .execute()
    ).data or []
    rows = []
    for a in ana:
        sid = a['transcript_session_id']
        meta = by_id.get(sid, {})
        rows.append({
            'group_name': meta.get('group_name') or meta.get('filename') or 'Unknown',
            'activities': a.get('marketing_activities_json') or [],
            'outcomes': a.get('pipeline_outcomes_json') or [],
        })
    return rows


def main():
    st.set_page_config(page_title='Marketing Activity', page_icon='📈', layout='wide')
    st.title('📈 Marketing Activity & Pipeline Outcomes')
    st.caption('Extracted from transcripts via Gemini; filter by session date.')
    st.divider()

    org_id = 'f58a2d22-4e96-4d4a-9348-b82c8e3f1f2e'
    if not get_sb():
        st.error('❌ Supabase not configured (SUPABASE_URL/SERVICE_KEY).')
        return

    dates = session_dates(org_id)
    if not dates:
        st.info('No session dates found. Run marketing_extractor.py first.')
        return
    date = st.sidebar.selectbox('📅 Session Date', dates, index=0)

    data = fetch_analysis(org_id, date)
    if not data:
        st.info('No analysis data for this date. Run marketing_extractor.py.')
        return

    # Render by group
    for row in data:
        st.subheader(f"👥 {row['group_name']} · {date}")
        left, right = st.columns(2)
        with left:
            st.markdown('**Marketing Activity**')
            acts = row['activities']
            if not acts:
                st.write('No activity found')
            else:
                for a in acts:
                    st.markdown(f"- **{a.get('name','Unknown')}**")
                    if a.get('none'):
                        st.write('  No marketing activity mentioned.')
                    else:
                        if a.get('network_activation'):
                            st.write(f"  - Network Activation: {a['network_activation']}")
                        if a.get('linkedin'):
                            st.write(f"  - LinkedIn: {a['linkedin']}")
                        if a.get('cold_outreach'):
                            st.write(f"  - Cold Outreach: {a['cold_outreach']}")
        with right:
            st.markdown('**Pipeline Outcomes**')
            outs = row['outcomes']
            if not outs:
                st.write('No outcomes found')
            else:
                for o in outs:
                    st.markdown(f"- **{o.get('name','Unknown')}**")
                    st.write(f"  Meetings: {o.get('meetings',0)}  ·  Proposals: {o.get('proposals',0)}  ·  Clients: {o.get('clients',0)}")
                    if o.get('notes'):
                        st.write(f"  Notes: {o['notes']}")
        st.divider()


if __name__ == '__main__':
    main()


