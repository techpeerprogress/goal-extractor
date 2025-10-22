#!/usr/bin/env python3
"""
Google Drive API Test Script
Tests the connection and permissions for Google Drive access
"""

import os
import json
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def test_google_drive_connection():
    """Test Google Drive API connection and permissions"""
    
    print("🔍 Testing Google Drive API Connection")
    print("=" * 50)
    
    load_dotenv()
    
    # Check service account file
    sa_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'sa-key.json')
    print(f"📁 Service account file: {sa_file}")
    
    if not os.path.exists(sa_file):
        print("❌ Service account file not found")
        return False
    
    try:
        # Load service account credentials
        with open(sa_file, 'r') as f:
            service_account_info = json.load(f)
        
        print(f"✅ Service account loaded")
        print(f"   Project ID: {service_account_info.get('project_id')}")
        print(f"   Client Email: {service_account_info.get('client_email')}")
        
        # Initialize credentials
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        # Build Drive service
        drive_service = build('drive', 'v3', credentials=credentials)
        print("✅ Drive service initialized")
        
        # Test basic API call
        print("\n🧪 Testing basic API call...")
        try:
            # Test with a simple query
            results = drive_service.files().list(
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            print("✅ Basic API call successful")
            print(f"   Found {len(results.get('files', []))} files")
            
        except HttpError as e:
            print(f"❌ API call failed: {e}")
            print(f"   Status: {e.resp.status}")
            print(f"   Reason: {e.resp.reason}")
            return False
        
        # Test folder access
        print("\n📁 Testing folder access...")
        folder_url = os.getenv('GOOGLE_DRIVE_FOLDER_URL')
        if folder_url:
            print(f"   Folder URL: {folder_url}")
            
            # Extract folder ID from URL
            import re
            folder_match = re.search(r'folders/([a-zA-Z0-9_-]+)', folder_url)
            if folder_match:
                folder_id = folder_match.group(1)
                print(f"   Folder ID: {folder_id}")
                
                try:
                    # Test folder access
                    folder_results = drive_service.files().list(
                        q=f"'{folder_id}' in parents",
                        pageSize=5,
                        fields="files(id, name, mimeType)"
                    ).execute()
                    
                    print("✅ Folder access successful")
                    print(f"   Found {len(folder_results.get('files', []))} items in folder")
                    
                    for file in folder_results.get('files', []):
                        print(f"   - {file.get('name')} ({file.get('mimeType')})")
                        
                except HttpError as e:
                    print(f"❌ Folder access failed: {e}")
                    print(f"   Status: {e.resp.status}")
                    print(f"   Reason: {e.resp.reason}")
                    return False
            else:
                print("❌ Could not extract folder ID from URL")
                return False
        else:
            print("⚠️  No folder URL configured")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_google_drive_connection()
    
    if not success:
        print("\n🔧 Troubleshooting suggestions:")
        print("1. Check if the service account has access to the Google Drive folder")
        print("2. Verify the folder URL is correct")
        print("3. Ensure the service account has 'Viewer' permissions on the folder")
        print("4. Check if the folder ID in the URL is correct")
        print("5. Try regenerating the service account key")
    else:
        print("\n🎉 Google Drive API is working correctly!")
