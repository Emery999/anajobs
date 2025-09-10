#!/usr/bin/env python3
"""
Test Job Titles Updater

Tests the job titles extraction and MongoDB update functionality on a small sample
"""

import sys
import os
from pathlib import Path

# Add utilities to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from job_titles_updater import JobTitlesUpdater

def test_extraction_only():
    """Test job title extraction without database updates"""
    print("🧪 Testing Job Titles Extraction (No Database Updates)")
    print("=" * 60)
    
    updater = JobTitlesUpdater()
    
    # Test URLs
    test_urls = [
        "https://www.4ocean.com/pages/careers",
        "https://www.aclu.org/careers"
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Testing URL: {url}")
        titles = updater.extract_job_titles(url)
        
        if titles:
            print(f"✅ Found {len(titles)} job titles:")
            for title in titles:
                print(f"   • {title}")
        else:
            print("❌ No job titles found")
    
    return 0

def test_database_update():
    """Test database update functionality on 3 organizations"""
    print("🧪 Testing Job Titles Database Update (3 Organizations)")
    print("=" * 60)
    print("⚠️ This will actually update the database with job_titles fields")
    
    confirm = input("Continue? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Test cancelled")
        return 1
    
    updater = JobTitlesUpdater()
    
    success = updater.process_all_organizations(limit=3, test_mode=False)
    
    if success:
        print("✅ Database update test completed")
        return 0
    else:
        print("❌ Database update test failed")
        return 1

def test_dry_run():
    """Test with dry run (test mode) on 5 organizations"""
    print("🧪 Testing Job Titles Updater (Dry Run - 5 Organizations)")
    print("=" * 60)
    print("✅ Safe mode - no database changes will be made")
    
    updater = JobTitlesUpdater()
    
    success = updater.process_all_organizations(limit=5, test_mode=True)
    
    if success:
        print("✅ Dry run test completed successfully")
        return 0
    else:
        print("❌ Dry run test failed")
        return 1

def main():
    """Main test function"""
    print("🔧 Job Titles Updater Test Suite")
    print("=" * 40)
    print("Choose a test to run:")
    print("1. Extract titles only (no database)")
    print("2. Dry run on 5 organizations (no database updates)")
    print("3. Real database update on 3 organizations")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        return test_extraction_only()
    elif choice == '2':
        return test_dry_run()
    elif choice == '3':
        return test_database_update()
    elif choice == '4':
        print("👋 Goodbye!")
        return 0
    else:
        print("❌ Invalid choice")
        return 1

if __name__ == "__main__":
    sys.exit(main())