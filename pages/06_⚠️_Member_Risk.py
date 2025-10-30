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
def group_codes(_sb: Client) -> List[str]:
    res = _sb.schema('peer_progress').table('groups').select('group_code').order('group_code').execute()
    codes = [r['group_code'] for r in (res.data or []) if r.get('group_code')]
    return ['All Groups'] + codes


def main():
    st.set_page_config(page_title='Member Risk Analysis', page_icon='⚠️', layout='wide')
    st.title('Member Risk Analysis')
    st.caption('Attendance & goal achievement signals. Click a bucket to see members.')
    st.divider()

    sb = get_sb()
    if not sb:
        st.error('❌ Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.')
        return

    from risk_analysis import evaluate_risk, get_client, timeframe_to_range

    # Filters
    left, mid, right, right2, right3 = st.columns(5)
    timeframe = left.selectbox('Timeframe', ['Weekly', 'Monthly', 'Quarterly', 'All Time'], index=0)
    groups = group_codes(sb)
    group_code = mid.selectbox('Group', groups, index=0)
    status = right.selectbox('Status', ['All Statuses', 'active', 'renewed', 'paused', 'dropped_requested', 'dropped_ghosting', 'not_renewed'], index=0)
    channel = right2.selectbox('Marketing Channel', ['All Channels', 'LinkedIn', 'Network Activation', 'Cold Outreach'], index=0)
    tier_filter = right3.selectbox('Risk Tier', ['All Risk Tiers', 'High Risk', 'Medium Risk', 'On Track', 'Crushing It'], index=0)

    rows = evaluate_risk(sb, timeframe, group_code, status, channel)
    if tier_filter != 'All Risk Tiers':
        rows = [r for r in rows if r['risk_tier'] == tier_filter]

    # Buckets
    def bucket(name: str) -> List[Dict]:
        return [r for r in rows if r['risk_tier'] == name]

    high = bucket('High Risk')
    med = bucket('Medium Risk')
    on_track = bucket('On Track')
    crush = bucket('Crushing It')

    # Display cards
    def card(title: str, subtitle: str, members: List[Dict], color: str):
        with st.container():
            st.markdown(f"### {title}")
            st.caption(subtitle)
            st.metric(label=f"{len(members)} members", value=len(members))
            if members:
                names = ', '.join([m['name'] for m in members[:6]]) + (f" +{len(members)-6} more" if len(members) > 6 else '')
                st.caption(names)
            st.divider()

    c1, c2 = st.columns(2)
    with c1:
        card('High Risk', '2+ missed calls, no comms OR no goals 2 weeks', high, 'red')
        card('On Track', 'Attending with active goals', on_track, 'gray')
    with c2:
        card('Medium Risk', 'Missed 1 call, no goals/completion/meetings this period', med, 'orange')
        card('Crushing It', 'Has proposals and/or clients', crush, 'green')

    # Drilldowns
    st.subheader('Members')
    for tier_name, members in [('High Risk', high), ('Medium Risk', med), ('On Track', on_track), ('Crushing It', crush)]:
        if not members:
            continue
        with st.expander(f"{tier_name} · {len(members)}"):
            for m in members:
                badge = '⚠️' if m.get('intervention_flag') else ''
                st.markdown(f"**{m['name']}** · {m.get('group_code','?')} · {m.get('status','?')} {badge}")
                st.caption(f"Meetings {m['meetings']} · Proposals {m['proposals']} · Clients {m['clients']} · Goals upd {m['goals_updates']} · Goals done {m['goals_completed']}")
                for r in m.get('reasons', [])[:3]:
                    st.markdown(f"- {r}")
                st.markdown('---')


if __name__ == '__main__':
    main()


