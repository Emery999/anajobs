#!/usr/bin/env python3
"""
Dry Run Test - Job Titles Updater

Tests the full pipeline on 3 organizations without updating the database
"""

import sys
import os
from pathlib import Path

# Add utilities to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from job_titles_updater import JobTitlesUpdater

def main():
    """Dry run test on 3 organizations"""
    print("🧪 Dry Run Test: Job Titles Updater")
    print("=" * 50)
    print("✅ Safe mode - No database changes will be made")
    print("🔢 Processing 3 organizations for testing")
    print("=" * 50)
    
    updater = JobTitlesUpdater()
    
    try:
        success = updater.process_all_organizations(limit=3, test_mode=True)
        
        if success:
            print("\n🎉 Dry Run Test Completed Successfully!")
            print("✅ Job title extraction pipeline is working")
            print("✅ MongoDB connection established")
            print("✅ Ready for production use")
            return 0
        else:
            print("\n❌ Dry Run Test Failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error during dry run: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())