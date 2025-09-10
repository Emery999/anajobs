#!/usr/bin/env python3
"""
Test Job Extraction Script (Without Claude AI)

Tests the job extraction functionality using fallback parsing method.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from job_extractor import JobExtractor

def main():
    """Test job extraction without Claude API"""
    
    print("🧪 Testing Job Extraction (Fallback Mode)")
    print("=" * 50)
    print("⚠️ Running without Claude AI - using fallback parsing")
    print("💡 For full AI-powered extraction, set ANTHROPIC_API_KEY")
    print("=" * 50)
    
    # Initialize extractor without Claude API key
    extractor = JobExtractor(claude_api_key=None)
    
    # Test with 3 organizations
    success = extractor.process_organizations(
        site_limit=3,
        output_file="test_jobs_extraction.jsonl"
    )
    
    if success:
        print("\n✅ Test completed successfully!")
        print("📁 Output: test_jobs_extraction.jsonl")
        
        # Show sample of output
        try:
            with open("test_jobs_extraction.jsonl", 'r') as f:
                first_line = f.readline()
                if first_line:
                    import json
                    sample = json.loads(first_line)
                    print(f"\n📋 Sample organization processed:")
                    print(f"   🏢 {sample['name']}")
                    print(f"   🔗 Jobs URL: {sample.get('jobs', 'N/A')}")
                    print(f"   📊 Jobs found: {sample.get('extraction_metadata', {}).get('jobs_found', 0)}")
                    print(f"   🏷️ Categories: {sample.get('extraction_metadata', {}).get('categories_detected', [])}")
        except Exception as e:
            print(f"⚠️ Could not display sample: {e}")
        
        return 0
    else:
        print("\n❌ Test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())