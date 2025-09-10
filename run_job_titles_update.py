#!/usr/bin/env python3
"""
Production Runner: Job Titles Update for Organizations Collection

This script updates ALL organizations in the MongoDB collection with job_titles fields.
Use with caution as it processes the entire collection.
"""

import sys
from pathlib import Path

# Add utilities to path
sys.path.append(str(Path(__file__).parent / "utilities"))

from job_titles_updater import JobTitlesUpdater

def main():
    """Run job titles update for all organizations"""
    print("🚀 Job Titles Update: Production Runner")
    print("=" * 60)
    print("📋 This will update ALL 390 organizations in MongoDB with:")
    print("   • job_titles: ['Title 1', 'Title 2', ...] (if found)")
    print("   • job_titles: null (if no titles found)")  
    print("   • job_titles_updated_at: timestamp")
    print("=" * 60)
    print("⚠️  WARNING: This will modify the MongoDB database!")
    print("⏱️  Estimated time: 15-30 minutes (2 second delay between requests)")
    print("=" * 60)
    
    # Safety confirmation
    print("\n❓ This is a production run that will update ALL organizations.")
    print("   Make sure you want to proceed.")
    
    # Since we can't use input() in this environment, we'll provide options
    print("\n🔧 To run this script:")
    print("1. For a SAFE TEST on 10 organizations:")
    print("   python utilities/job_titles_updater.py --test --limit 10")
    print()
    print("2. For PRODUCTION run on all organizations:")
    print("   python utilities/job_titles_updater.py")
    print()
    print("3. For LIMITED production run (e.g., 50 organizations):")
    print("   python utilities/job_titles_updater.py --limit 50")
    
    print("\n💡 Options explained:")
    print("   --test     : Safe mode, no database changes")
    print("   --limit N  : Process only N organizations") 
    print("   (no flags) : Process ALL organizations")
    
    print(f"\n📁 Script location: utilities/job_titles_updater.py")
    print(f"📖 Use --help for detailed usage information")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())