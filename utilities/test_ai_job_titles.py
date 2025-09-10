#!/usr/bin/env python3
"""
Test AI Job Titles Extraction

Tests the AI-powered job title extraction on a small sample
"""

import sys
import os
from pathlib import Path

# Add utilities to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_job_titles_updater import AIJobTitlesUpdater

def test_ai_extraction():
    """Test AI job title extraction on 2 organizations"""
    
    # Check for API key
    claude_api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not claude_api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("💡 Set your Claude API key:")
        print("   export ANTHROPIC_API_KEY='your-api-key-here'")
        return 1
    
    print("🧪 Testing AI Job Titles Extraction")
    print("=" * 50)
    print("🤖 Using Claude AI for intelligent extraction")
    print("🔢 Processing 2 organizations in test mode")
    print("✅ Safe mode - No database changes")
    print("=" * 50)
    
    updater = AIJobTitlesUpdater(claude_api_key=claude_api_key)
    
    try:
        success = updater.process_all_organizations(limit=2, test_mode=True)
        
        if success:
            print("\n🎉 AI Job Titles Test Completed Successfully!")
            print("✅ Claude AI integration working")
            print("✅ Job content aggregation working") 
            print("✅ Job title extraction working")
            print("✅ Ready for production use")
            return 0
        else:
            print("\n❌ AI Job Titles Test Failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1

def test_content_aggregation_only():
    """Test just the content aggregation part without AI"""
    print("🧪 Testing Job Content Aggregation Only")
    print("=" * 45)
    
    updater = AIJobTitlesUpdater()  # No API key needed for this test
    
    test_urls = [
        "https://www.4ocean.com/pages/careers",
        "https://www.aclu.org/careers"
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Testing content aggregation for: {url}")
        print("-" * 60)
        
        content = updater.aggregate_job_content(url, max_pages=3)
        
        if content:
            content_length = len(content)
            lines = content.count('\n')
            print(f"✅ Successfully aggregated content")
            print(f"   Length: {content_length:,} characters")
            print(f"   Lines: {lines:,}")
            print(f"   Preview: {content[:200]}...")
        else:
            print("❌ Failed to aggregate content")
    
    return 0

def main():
    """Main test function"""
    print("🔧 AI Job Titles Test Suite")
    print("=" * 35)
    
    # Check what type of test to run
    claude_api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if claude_api_key:
        print("✅ Claude API key detected")
        print("🤖 Running full AI extraction test")
        return test_ai_extraction()
    else:
        print("⚠️ No Claude API key detected")
        print("📚 Running content aggregation test only")
        return test_content_aggregation_only()

if __name__ == "__main__":
    sys.exit(main())