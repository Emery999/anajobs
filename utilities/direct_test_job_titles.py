#!/usr/bin/env python3
"""
Direct Test for Job Titles Extraction
"""

import sys
import os
from pathlib import Path

# Add utilities to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from job_titles_updater import JobTitlesUpdater

def main():
    """Direct test of job title extraction"""
    print("🧪 Direct Test: Job Titles Extraction")
    print("=" * 50)
    
    updater = JobTitlesUpdater()
    
    # Test URLs
    test_urls = [
        "https://www.4ocean.com/pages/careers",
        "https://www.aclu.org/careers"
    ]
    
    total_found = 0
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Testing URL: {url}")
        print("-" * 40)
        
        titles = updater.extract_job_titles(url)
        
        if titles:
            print(f"✅ Found {len(titles)} job titles:")
            for title in titles:
                print(f"   • {title}")
            total_found += len(titles)
        else:
            print("❌ No job titles found or extraction failed")
        
        print()  # Empty line for readability
    
    print(f"📊 Summary:")
    print(f"   URLs tested: {len(test_urls)}")
    print(f"   Total job titles found: {total_found}")
    
    if total_found > 0:
        print("✅ Job title extraction is working!")
        return 0
    else:
        print("⚠️ No job titles found - check extraction logic")
        return 1

if __name__ == "__main__":
    sys.exit(main())