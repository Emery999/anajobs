#!/usr/bin/env python3
"""
Claude API Setup Helper

This script helps you set up the Claude API key for the AI job titles extraction.
"""

import os
from pathlib import Path

def setup_claude_api():
    """Guide user through Claude API setup"""
    print("🔑 Claude API Setup Helper")
    print("=" * 40)
    print("📋 Follow these steps to get your Claude API key:")
    print()
    
    print("1️⃣ **Get Claude API Key:**")
    print("   • Visit: https://console.anthropic.com/")
    print("   • Sign up or log in to your Anthropic account")
    print("   • Navigate to API Keys section")
    print("   • Click 'Create Key' or 'Generate API Key'")
    print("   • Copy the key (starts with 'sk-ant-api03-')")
    print()
    
    print("2️⃣ **Set Up Environment:**")
    print("   Option A - Create .env file:")
    print("   ```")
    print("   echo 'ANTHROPIC_API_KEY=your-key-here' > .env")
    print("   ```")
    print()
    print("   Option B - Export environment variable:")
    print("   ```")
    print("   export ANTHROPIC_API_KEY='your-key-here'")
    print("   ```")
    print()
    
    print("3️⃣ **Test Your Setup:**")
    print("   ```")
    print("   python utilities/test_ai_job_titles.py")
    print("   ```")
    print()
    
    print("4️⃣ **Run AI Job Titles Extraction:**")
    print("   ```")
    print("   # Safe test with 2 organizations")
    print("   python utilities/ai_job_titles_updater.py --test --limit 2")
    print("   ```")
    print()
    
    # Check current environment
    current_key = os.getenv('ANTHROPIC_API_KEY')
    if current_key:
        # Mask the key for security
        masked_key = current_key[:15] + "..." + current_key[-4:] if len(current_key) > 20 else "***masked***"
        print(f"✅ Current API key detected: {masked_key}")
    else:
        print("❌ No API key detected in environment")
    
    # Check for .env file
    env_file = Path('.env')
    if env_file.exists():
        print("✅ .env file exists")
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                if 'ANTHROPIC_API_KEY' in content:
                    print("✅ ANTHROPIC_API_KEY found in .env file")
                else:
                    print("⚠️ ANTHROPIC_API_KEY not found in .env file")
        except Exception as e:
            print(f"⚠️ Could not read .env file: {e}")
    else:
        print("⚠️ No .env file found")
    
    print("\n🔒 **Security Reminders:**")
    print("   • Never commit .env files to git")
    print("   • Never share API keys publicly")  
    print("   • Add .env to your .gitignore file")
    print("   • Rotate keys periodically")
    
    return 0

if __name__ == "__main__":
    setup_claude_api()