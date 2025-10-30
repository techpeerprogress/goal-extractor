from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()


# ---------------- Time windows -----------------

def timeframe_to_range(timeframe: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Return (start, end) in UTC for timeframe. None for all-time."""
    now = datetime.now(timezone.utc)
    tf = (timeframe or 'All Time').lower()
    if tf.startswith('week'):
        return now - timedelta(days=7), now
    if tf.startswith('month'):
        return now - timedelta(days=30), now
    if tf.startswith('quarter'):
        return now - timedelta(days=90), now
    return None, None  # all time


# ------------- Data acquisition ----------------

def get_client() -> Optional[Client]:
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    if not url or not key:
        return None
    return create_client(url, key)


def fetch_group_map(sb: Client) -> Dict[str, str]:
    """Return mapping {group_id: group_code}. Supports legacy schemas where PK is 'id'."""
    # Select only columns that definitely exist: id (PK) and group_code
    res = sb.schema('peer_progress').table('groups').select('id, group_code').execute()
    mapping: Dict[str, str] = {}
    for r in (res.data or []):
        gid = r.get('id')
        if gid:
            mapping[gid] = r.get('group_code')
    return mapping


def fetch_members(sb: Client, group_id_filter: Optional[str], status: Optional[str]) -> List[Dict]:
    # Select explicit columns (avoid member_id to support legacy schemas with 'id' only)
    q = sb.schema('peer_progress').table('members').select('id, full_name, group_id, status')
    if group_id_filter:
        q = q.eq('group_id', group_id_filter)
    if status and status != 'All Statuses':
        q = q.eq('status', status)
    rows = (q.execute().data) or []
    # Normalize: ensure 'member_id' exists in returned dicts for downstream usage
    for r in rows:
        if 'member_id' not in r and 'id' in r:
            r['member_id'] = r['id']
    return rows


def fetch_activity(sb: Client, member_ids: List[str], start: Optional[datetime], end: Optional[datetime], channel: Optional[str]) -> List[Dict]:
    if not member_ids:
        return []
    # Select all columns to tolerate schema differences (e.g., type vs subtype)
    q = sb.schema('peer_progress').table('activity_events').select('*').in_('member_id', member_ids)
    rows = (q.execute().data) or []
    # Time filter in Python to handle varying timestamp column names
    def _row_ts(r: Dict) -> Optional[datetime]:
        ts_str = r.get('ts') or r.get('created_at') or r.get('timestamp') or r.get('time')
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            return None
    if start or end:
        filtered = []
        for r in rows:
            ts_val = _row_ts(r)
            if not ts_val:
                continue
            if start and ts_val < start:
                continue
            if end and ts_val > end:
                continue
            filtered.append(r)
        rows = filtered
    # Apply channel filter in Python to avoid column name issues upstream
    if channel and channel != 'All Channels':
        mapping = {'LinkedIn': 'linkedin', 'Network Activation': 'network_activation', 'Cold Outreach': 'cold_outreach'}
        target = mapping.get(channel, channel)
        rows = [r for r in rows if (r.get('channel') == target or r.get('marketing_channel') == target)]
    return rows


def fetch_goal_events(sb: Client, member_ids: List[str], start: Optional[datetime], end: Optional[datetime]) -> List[Dict]:
    if not member_ids:
        return []
    # Use activity_events as the unified store; filter to goal_* types
    q = sb.schema('peer_progress').table('activity_events').select('*').in_('member_id', member_ids)
    rows = (q.execute().data) or []
    def _row_ts(r: Dict) -> Optional[datetime]:
        ts_str = r.get('ts') or r.get('created_at') or r.get('timestamp')
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            return None
    # Keep only goal-related events
    def _etype(r: Dict) -> str:
        return (r.get('subtype') or r.get('type') or r.get('event_type') or '').lower()
    rows = [r for r in rows if _etype(r) in ('goal_set', 'goal_update', 'goal_completed')]

    if start or end:
        filtered = []
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


def fetch_attendance(sb: Client, member_ids: List[str], start: Optional[datetime], end: Optional[datetime]) -> List[Dict]:
    if not member_ids:
        return []
    q = sb.schema('peer_progress').table('member_attendance').select('*').in_('member_id', member_ids)
    rows = (q.execute().data) or []
    def _row_date(r: Dict) -> Optional[datetime]:
        # support 'date' (YYYY-MM-DD) or 'call_date' or 'created_at'
        ds = r.get('date') or r.get('call_date') or r.get('created_at')
        if not ds:
            return None
        try:
            # Handle pure date
            if len(ds) == 10:
                return datetime.fromisoformat(ds + 'T00:00:00+00:00')
            return datetime.fromisoformat(ds.replace('Z', '+00:00'))
        except Exception:
            return None
    if start or end:
        filtered = []
        for r in rows:
            dv = _row_date(r)
            if not dv:
                continue
            if start and dv < start:
                continue
            if end and dv > end:
                continue
            filtered.append(r)
        rows = filtered
    return rows


# ------------- Risk evaluation -----------------

@dataclass
class MemberAggregate:
    member_id: str
    name: str
    group_code: Optional[str]
    status: Optional[str]
    meetings: int = 0
    proposals: int = 0
    clients: int = 0
    goals_set_or_updated: int = 0
    goals_completed: int = 0
    missed_calls_unexcused: int = 0
    consecutive_unexcused_misses: int = 0


def aggregate_member_metrics(members: List[Dict], activity: List[Dict], goal_events: List[Dict], attendance: List[Dict], group_map: Dict[str, str]) -> Dict[str, MemberAggregate]:
    # Guard: skip rows without id
    id_to_member = { (m.get('member_id') or m.get('id')): m for m in members if (m.get('member_id') or m.get('id')) }
    agg: Dict[str, MemberAggregate] = {}
    for mid, mem in id_to_member.items():
        gid = mem.get('group_id')
        agg[mid] = MemberAggregate(
            member_id=mid,
            name=mem.get('full_name','Unknown'),
            group_code=group_map.get(gid) if gid else None,
            status=mem.get('status')
        )
    # Activity counts
    for row in activity:
        mid = row['member_id']
        if mid not in agg:
            continue
        st = row.get('subtype') or row.get('type') or row.get('event_type')
        cnt = int(row.get('count') or 0)
        if st == 'meeting_booked':
            agg[mid].meetings += cnt
        elif st == 'proposal_sent':
            agg[mid].proposals += cnt
        elif st == 'client_closed':
            agg[mid].clients += cnt
    # Goal events
    for ge in goal_events:
        mid = ge['member_id']
        if mid not in agg:
            continue
        et = ge.get('event_type')
        if et in ('goal_set', 'goal_update'):
            agg[mid].goals_set_or_updated += 1
        elif et == 'goal_completed':
            agg[mid].goals_completed += 1
    # Attendance
    from collections import defaultdict
    member_days = defaultdict(list)
    for att in attendance:
        mid = att.get('member_id') or att.get('member')
        if not mid:
            continue
        member_days[mid].append(att)
    for mid, days in member_days.items():
        # sort by date
        days_sorted = sorted(days, key=lambda d: d['date'])
        consecutive = 0
        for d in days_sorted:
            status_val = d.get('status') or d.get('attendance_status')
            if status_val == 'absent' and not d.get('reason'):
                agg[mid].missed_calls_unexcused += 1
                consecutive += 1
            else:
                consecutive = 0
            agg[mid].consecutive_unexcused_misses = max(agg[mid].consecutive_unexcused_misses, consecutive)
    return agg


def classify_risk(agg: MemberAggregate, timeframe: str) -> Tuple[str, List[str], bool]:
    """Return (risk_tier, reasons, special_flag_intervention)."""
    reasons: List[str] = []
    special_flag = False

    # Special notification
    if agg.meetings >= 4 and agg.proposals == 0:
        special_flag = True

    # High Risk
    if agg.consecutive_unexcused_misses >= 2:
        reasons.append('Missed 2 consecutive calls without communication')
        return 'High Risk', reasons, special_flag
    if timeframe.lower().startswith(('week','month','quarter')):
        # approximate: use goals_set_or_updated as proxy for “updated goals”
        if agg.goals_set_or_updated == 0 and timeframe.lower().startswith(('month','quarter')):
            reasons.append('No goal updates for >= 2 weeks')
            return 'High Risk', reasons, special_flag

    # Medium Risk
    if agg.missed_calls_unexcused >= 1:
        reasons.append('Missed 1 call without communication')
    if agg.goals_set_or_updated == 0:
        reasons.append('No goal set this period')
    if agg.goals_completed == 0:
        reasons.append('No goal completion this period')
    if agg.meetings == 0:
        reasons.append('No meetings scheduled this period')
    if reasons:
        return 'Medium Risk', reasons, special_flag

    # Crushing / On Track
    if agg.proposals > 0 or agg.clients > 0:
        return 'Crushing It', ['Has proposals or clients'], special_flag
    return 'On Track', ['Goals and meetings active'], special_flag


def evaluate_risk(sb: Client, timeframe: str, group_code: Optional[str], status: Optional[str], channel: Optional[str]) -> List[Dict]:
    start, end = timeframe_to_range(timeframe)
    group_map = fetch_group_map(sb)
    group_id_filter = None
    if group_code and group_code != 'All Groups':
        # reverse map to get id by code
        rev = {v: k for k, v in group_map.items() if v}
        group_id_filter = rev.get(group_code)
    members = fetch_members(sb, group_id_filter, status)
    member_ids = [(m.get('member_id') or m.get('id')) for m in members if (m.get('member_id') or m.get('id'))]
    activity = fetch_activity(sb, member_ids, start, end, channel)
    goal_events = fetch_goal_events(sb, member_ids, start, end)
    attendance = fetch_attendance(sb, member_ids, start, end)
    agg_map = aggregate_member_metrics(members, activity, goal_events, attendance, group_map)

    results = []
    for mid, agg in agg_map.items():
        tier, reasons, special = classify_risk(agg, timeframe)
        results.append({
            'member_id': mid,
            'name': agg.name,
            'group_code': agg.group_code,
            'status': agg.status,
            'risk_tier': tier,
            'reasons': reasons,
            'meetings': agg.meetings,
            'proposals': agg.proposals,
            'clients': agg.clients,
            'goals_updates': agg.goals_set_or_updated,
            'goals_completed': agg.goals_completed,
            'intervention_flag': special,
        })
    return results


