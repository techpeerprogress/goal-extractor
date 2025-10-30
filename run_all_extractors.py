"""Unified runner to populate all dashboard data in one go.

Runs, in order:
1) Goal extractor → quantifiable_goals + transcript_sessions
2) Marketing extractor → transcript_analysis.marketing_activities_json + pipeline_outcomes_json
3) Stuck extractor → transcript_analysis.stuck_signals_json
4) Challenges/Strategies extractor → transcript_analysis.challenges_strategies_json

Usage examples:
  python run_all_extractors.py --folder_key october_2025
  python run_all_extractors.py --folder_url https://drive.google.com/drive/folders/XXX --recursive --days_back 30
  python run_all_extractors.py --multiple_folders october_2025 folder_1 folder_2
"""

import os
import argparse
from dotenv import load_dotenv

# Import extractors
from goal_extractor import extract_goals_for_all_transcripts
from marketing_extractor import extract_and_save_marketing_data
from stuck_extractor import extract_stuck
from challenges_extractor import extract_challenges


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description='Run all extractors to populate dashboard data')
    parser.add_argument('--folder_key', type=str, help='Key into predefined FOLDER_URLS')
    parser.add_argument('--folder_url', type=str, help='Direct Google Drive folder URL')
    parser.add_argument('--multiple_folders', nargs='*', help='Multiple folder keys or URLs')
    parser.add_argument('--days_back', type=int, default=None, help='Only process files modified within N days')
    parser.add_argument('--recursive', action='store_true', help='Search subfolders recursively')
    args = parser.parse_args()

    folder_key = args.folder_key
    folder_url = args.folder_url
    multiple_folders = args.multiple_folders
    days_back = args.days_back
    recursive = bool(args.recursive)

    print('\n=== 1) Goals Extraction ===')
    try:
        extract_goals_for_all_transcripts(
            folder_key=folder_key,
            folder_url=folder_url,
            multiple_folders=multiple_folders,
            days_back=days_back,
            recursive=recursive,
        )
    except Exception as e:
        print(f'⚠️ Goals extraction error: {e}')

    print('\n=== 2) Marketing Activity & Pipeline Outcomes ===')
    try:
        extract_and_save_marketing_data(
            folder_key=folder_key,
            folder_url=folder_url,
            multiple_folders=multiple_folders,
            days_back=days_back,
            recursive=recursive,
        )
    except Exception as e:
        print(f'⚠️ Marketing extraction error: {e}')

    print('\n=== 3) Stuck / Support Needed ===')
    try:
        # Prefer folder_url; extract_stuck signature uses folder_url
        target_folder = folder_url or os.getenv('GOOGLE_DRIVE_FOLDER_URL')
        extract_stuck(
            folder_url=target_folder,
            days_back=days_back,
            recursive=recursive,
        )
    except Exception as e:
        print(f'⚠️ Stuck extraction error: {e}')

    print('\n=== 4) Challenges & Strategies ===')
    try:
        target_folder = folder_url or os.getenv('GOOGLE_DRIVE_FOLDER_URL')
        extract_challenges(
            folder_url=target_folder,
            days_back=days_back,
            recursive=recursive,
        )
    except Exception as e:
        print(f'⚠️ Challenges extraction error: {e}')

    print('\n✅ Completed all extractors.')


if __name__ == '__main__':
    main()


