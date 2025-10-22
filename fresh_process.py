#!/usr/bin/env python3
"""
Fresh transcript processing script
Clears database and processes all transcripts with new source tracking
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import TranscriptProcessor

def main():
    """Process all transcripts fresh with source tracking"""
    
    print("🎯 Goal Extractor - Fresh Processing")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Get organization ID
    organization_id = os.getenv("ORGANIZATION_ID")
    if not organization_id:
        print("❌ ORGANIZATION_ID not found in environment variables")
        return
    
    print(f"📋 Organization ID: {organization_id}")
    
    # Initialize processor
    processor = TranscriptProcessor(organization_id)
    
    print("\n🔄 Processing all transcripts...")
    
    # Process October transcripts (assuming this is your main dataset)
    try:
        result = processor.process_october_transcripts()
        
        print(f"\n📊 Processing Results:")
        print(f"   • Processed: {result['processed']}")
        print(f"   • Failed: {result['failed']}")
        print(f"   • Total: {result['processed'] + result['failed']}")
        
        if result['details']:
            print(f"\n📝 Details:")
            for detail in result['details']:
                print(f"   • {detail}")
        
        if result.get('error'):
            print(f"\n❌ Error: {result['error']}")
        
        print(f"\n✅ Fresh processing completed!")
        print(f"   All goals now have proper source tracking:")
        print(f"   • AI-extracted goals: source_type='ai_extraction'")
        print(f"   • Manual goals: source_type='human_input'")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return
    
    print("\n" + "=" * 50)
    print("🎉 Fresh processing complete!")
    print("   Check the dashboard to see goals with source tracking")

if __name__ == "__main__":
    main()
