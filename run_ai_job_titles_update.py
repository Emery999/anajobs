#!/usr/bin/env python3
"""
Production Runner: AI Job Titles Update

This script provides safe options for running the AI-powered job titles updater.
"""

import sys
import os
from pathlib import Path

# Add utilities to path
sys.path.append(str(Path(__file__).parent / "utilities"))

def main():
    """Main runner with safe options"""
    print("🤖 AI-Powered Job Titles Updater")
    print("=" * 50)
    print("🎯 This script uses Claude AI to extract precise job titles")
    print("📋 Features:")
    print("   • Comprehensive content aggregation from career pages")
    print("   • Claude AI intelligent title extraction")
    print("   • Deletion of existing job_titles from previous runs")
    print("   • Updates MongoDB with extracted titles or null")
    print("=" * 50)
    
    # Check for API key
    claude_api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if claude_api_key:
        print("✅ Claude API key detected")
    else:
        print("❌ No Claude API key found")
        print("💡 Set your API key:")
        print("   export ANTHROPIC_API_KEY='your-claude-api-key'")
        print()
    
    print("🔧 Available Commands:")
    print()
    print("1. 🧪 SAFE TEST (2 organizations, no database changes):")
    print("   python utilities/ai_job_titles_updater.py --test --limit 2")
    print()
    print("2. 🔬 SMALL TEST (5 organizations, real database updates):")
    print("   python utilities/ai_job_titles_updater.py --limit 5")
    print()
    print("3. 📊 MEDIUM RUN (20 organizations):")
    print("   python utilities/ai_job_titles_updater.py --limit 20")
    print()
    print("4. 🚀 FULL PRODUCTION (all 390+ organizations):")
    print("   python utilities/ai_job_titles_updater.py")
    print("   ⚠️ Requires confirmation, takes 2-3 hours, costs $20-50")
    print()
    
    print("💰 Estimated Costs (Claude API):")
    print("   • Test (2 orgs): ~$0.10")
    print("   • Small (5 orgs): ~$0.25")  
    print("   • Medium (20 orgs): ~$1.00")
    print("   • Full (390 orgs): ~$20-50")
    print()
    
    print("⏱️ Estimated Times:")
    print("   • Test (2 orgs): 2-3 minutes")
    print("   • Small (5 orgs): 5-10 minutes")
    print("   • Medium (20 orgs): 20-30 minutes")
    print("   • Full (390 orgs): 2-3 hours")
    print()
    
    if not claude_api_key:
        print("🔑 First, set your Claude API key to proceed with any option")
        print("   You can get an API key from: https://console.anthropic.com/")
        
    print("📖 Use --help with the script for detailed options")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())