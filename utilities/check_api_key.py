#!/usr/bin/env python3
"""
Check Claude API Key Setup

Verifies that the Claude API key is properly configured and working.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def check_api_key():
    """Check if Claude API key is properly configured"""
    print("🔍 Claude API Key Check")
    print("=" * 30)
    
    # Check environment variable
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("❌ No ANTHROPIC_API_KEY found in environment")
        
        # Check .env file
        env_file = Path('.env')
        if env_file.exists():
            print("🔍 Checking .env file...")
            try:
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith('ANTHROPIC_API_KEY='):
                            print("✅ Found ANTHROPIC_API_KEY in .env file")
                            print("💡 Load it with: source .env")
                            return 0
                print("❌ No ANTHROPIC_API_KEY in .env file")
            except Exception as e:
                print(f"❌ Error reading .env file: {e}")
        else:
            print("❌ No .env file found")
            
        print("\n🔧 Setup Instructions:")
        print("1. Get API key from: https://console.anthropic.com/")
        print("2. Set environment variable:")
        print("   export ANTHROPIC_API_KEY='your-key-here'")
        print("3. Or create .env file:")
        print("   echo 'ANTHROPIC_API_KEY=your-key-here' > .env")
        
        return 1
    
    # Validate API key format
    if not api_key.startswith('sk-ant-'):
        print(f"⚠️ API key format looks incorrect")
        print(f"   Expected: sk-ant-api03-...")
        print(f"   Got: {api_key[:15]}...")
        return 1
    
    # Mask key for display
    masked_key = api_key[:15] + "..." + api_key[-4:] if len(api_key) > 20 else "***masked***"
    print(f"✅ API key found: {masked_key}")
    print(f"✅ Format looks correct")
    
    # Test API connection
    print("\n🧪 Testing API connection...")
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Simple test request
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": "Say 'API test successful'"
            }]
        )
        
        response_text = response.content[0].text.strip()
        print(f"✅ API test successful!")
        print(f"   Response: {response_text}")
        
    except ImportError:
        print("⚠️ anthropic package not installed")
        print("   Install with: pip install anthropic")
        return 1
    except Exception as e:
        print(f"❌ API test failed: {e}")
        print("   Check your API key and try again")
        return 1
    
    print("\n🎉 Claude API is properly configured!")
    print("✅ Ready to run AI job titles extraction")
    
    return 0

if __name__ == "__main__":
    sys.exit(check_api_key())