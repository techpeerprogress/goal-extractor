"""
Simple deduplication script for Goal Extractor.
"""

import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

def init_supabase():
    """Initialize Supabase connection"""
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return None
        
    return create_client(supabase_url, supabase_key)

def find_and_remove_duplicates(supabase: Client, dry_run: bool = True):
    """Find and remove duplicate goals"""
    print("🔍 Finding duplicate quantifiable goals...")
    
    result = supabase.schema('peer_progress').table('quantifiable_goals').select('*').order('created_at', desc=True).execute()
    
    if not result.data:
        print("📝 No goals found")
        return
    
    goals = result.data
    print(f"📊 Total goals found: {len(goals)}")
    
    seen_goals = {}
    duplicates = []
    
    for goal in goals:
        key = f"{goal['participant_name']}|{goal['goal_text']}|{goal['call_date']}"
        
        if key in seen_goals:
            duplicates.append(goal)
            print(f"🔄 Duplicate found: {goal['participant_name']} - {goal['goal_text'][:50]}... ({goal['call_date']})")
        else:
            seen_goals[key] = goal
    
    print(f"\n📈 Summary:")
    print(f"   • Total goals: {len(goals)}")
    print(f"   • Unique goals: {len(seen_goals)}")
    print(f"   • Duplicates: {len(duplicates)}")
    
    if duplicates:
        if dry_run:
            print(f"\n🧪 DRY RUN: Would remove {len(duplicates)} duplicate goals")
        else:
            print(f"\n🗑️  Removing {len(duplicates)} duplicate goals...")
            removed_count = 0
            
            for duplicate in duplicates:
                try:
                    supabase.schema('peer_progress').table('quantifiable_goals').delete().eq('id', duplicate['id']).execute()
                    removed_count += 1
                    print(f"   ✅ Removed: {duplicate['participant_name']} - {duplicate['goal_text'][:30]}...")
                except Exception as e:
                    print(f"   ❌ Error removing {duplicate['id']}: {e}")
            
            print(f"\n🎉 Successfully removed {removed_count} duplicate goals")

def show_recent_goals(supabase: Client, days: int = 7):
    """Show goals from recent transcripts"""
    print(f"\n📅 Goals from the last {days} days:")
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    result = supabase.schema('peer_progress').table('quantifiable_goals').select('*').gte('call_date', cutoff_date).order('call_date', desc=True).execute()
    
    if not result.data:
        print("   No recent goals found")
        return
    
    goals = result.data
    print(f"   Found {len(goals)} goals from recent transcripts")
    
    by_date = {}
    for goal in goals:
        date = goal['call_date']
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(goal)
    
    for date in sorted(by_date.keys(), reverse=True):
        goals_for_date = by_date[date]
        print(f"\n   📆 {date} ({len(goals_for_date)} goals):")
        
        for goal in goals_for_date:
            print(f"      • {goal['participant_name']}: {goal['goal_text'][:60]}... (target: {goal['target_number']})")

if __name__ == "__main__":
    print("🎯 Goal Extractor - Simple Deduplication")
    print("=" * 50)
    
    supabase = init_supabase()
    if not supabase:
        exit(1)
    
    show_recent_goals(supabase, days=14)
    find_and_remove_duplicates(supabase, dry_run=True)
    
    print("\n" + "=" * 50)
    print("💡 To remove duplicates, run:")
    print("   find_and_remove_duplicates(supabase, dry_run=False)")
