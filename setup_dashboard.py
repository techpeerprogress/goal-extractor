#!/usr/bin/env python3
"""
Dashboard Setup Script
Helps configure the Goal Extractor Dashboard
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Create .env file with Supabase configuration"""
    env_path = Path(".env")
    
    if env_path.exists():
        print("✅ .env file already exists")
        return
    
    print("🔧 Creating .env file...")
    
    supabase_url = input("Enter your Supabase URL: ").strip()
    supabase_service_key = input("Enter your Supabase Service Key: ").strip()
    supabase_anon_key = input("Enter your Supabase Anon Key (optional): ").strip()
    organization_id = input("Enter Organization ID (optional, press Enter to skip): ").strip()
    
    env_content = f"""# Supabase Configuration
SUPABASE_URL={supabase_url}
SUPABASE_SERVICE_KEY={supabase_service_key}
SUPABASE_ANON_KEY={supabase_anon_key}
"""
    
    if organization_id:
        env_content += f"ORGANIZATION_ID={organization_id}\n"
    
    with open(env_path, "w") as f:
        f.write(env_content)
    
    print("✅ .env file created successfully!")

def check_dependencies():
    """Check if required dependencies are installed"""
    # Package name -> module name mapping
    packages = {
        "streamlit": "streamlit",
        "pandas": "pandas", 
        "plotly": "plotly",
        "supabase": "supabase",
        "python-dotenv": "dotenv"  # Package name -> module name
    }
    
    missing_packages = []
    
    for package_name, module_name in packages.items():
        try:
            __import__(module_name)
            print(f"✅ {package_name} is installed")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name} is missing")
    
    if missing_packages:
        print(f"\n🔧 Install missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def test_supabase_connection():
    """Test Supabase connection"""
    try:
        from supabase import create_client, Client
        from dotenv import load_dotenv
        
        load_dotenv()
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ Missing Supabase credentials in .env file")
            print("   Make sure you have SUPABASE_URL and SUPABASE_SERVICE_KEY set")
            return False
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Test connection by querying a simple table
        try:
            result = supabase.schema('peer_progress').table('transcript_sessions').select('id').limit(1).execute()
            print("✅ Supabase connection successful!")
            return True
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            return False
            
    except ImportError:
        print("❌ Required packages not installed")
        return False

def main():
    """Main setup function"""
    print("🎯 Goal Extractor Dashboard Setup")
    print("=" * 40)
    
    # Check dependencies
    print("\n📦 Checking dependencies...")
    if not check_dependencies():
        print("\n❌ Please install missing dependencies and run again")
        return
    
    # Create .env file
    print("\n🔧 Setting up environment variables...")
    create_env_file()
    
    # Test Supabase connection
    print("\n🔌 Testing Supabase connection...")
    if test_supabase_connection():
        print("\n✅ Dashboard setup complete!")
        print("\n🚀 To run the dashboard:")
        print("streamlit run dashboard.py")
    else:
        print("\n❌ Setup incomplete. Please check your Supabase credentials.")

if __name__ == "__main__":
    main()
