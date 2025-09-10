#!/usr/bin/env python3
"""
Complete AI Setup Verification

This script runs through all the setup verification steps to ensure
the AI job title extraction is ready to use.
"""

import sys
import os
from pathlib import Path

def verify_complete_setup():
    """Run complete verification of AI setup"""
    print("🔧 Complete AI Setup Verification")
    print("=" * 45)
    
    checks_passed = 0
    total_checks = 6
    
    # Check 1: Python environment
    print("\n1️⃣ Checking Python environment...")
    try:
        import anthropic
        print("✅ anthropic package installed")
        checks_passed += 1
    except ImportError:
        print("❌ anthropic package not found")
        print("   Install with: pip install anthropic")
    
    # Check 2: API key in environment
    print("\n2️⃣ Checking API key...")
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key and api_key.startswith('sk-ant-'):
        masked_key = api_key[:15] + "..." + api_key[-4:] if len(api_key) > 20 else "***"
        print(f"✅ API key found: {masked_key}")
        checks_passed += 1
    else:
        print("❌ No valid API key found")
        print("   Set with: export ANTHROPIC_API_KEY='your-key'")
    
    # Check 3: .env file
    print("\n3️⃣ Checking .env file...")
    env_file = Path('.env')
    if env_file.exists():
        print("✅ .env file exists")
        checks_passed += 1
    else:
        print("⚠️ No .env file found (optional)")
        print("   Create with: echo 'ANTHROPIC_API_KEY=your-key' > .env")
    
    # Check 4: MongoDB connection
    print("\n4️⃣ Checking MongoDB connection...")
    try:
        from pymongo.mongo_client import MongoClient
        from pymongo.server_api import ServerApi
        
        uri = "mongodb+srv://seeotter_db_user:n8tfO3zzASvoxllr@cluster0.hxabnjn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        client = MongoClient(uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        
        # Check organizations collection
        db = client["social_impact_jobs"]
        collection = db["organizations"]
        count = collection.count_documents({})
        
        print(f"✅ MongoDB connected ({count} organizations)")
        checks_passed += 1
        client.close()
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
    
    # Check 5: Script files
    print("\n5️⃣ Checking script files...")
    required_files = [
        'utilities/ai_job_titles_updater.py',
        'utilities/test_ai_job_titles.py',
        'utilities/check_api_key.py'
    ]
    
    all_files_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")
            all_files_exist = False
    
    if all_files_exist:
        print("✅ All required script files present")
        checks_passed += 1
    
    # Check 6: API test (if API key available)
    print("\n6️⃣ Testing Claude API...")
    if api_key and api_key.startswith('sk-ant-'):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=20,
                messages=[{
                    "role": "user",
                    "content": "Extract job titles: Software Engineer, Apply Now, Data Scientist, Learn More. Return as JSON array."
                }]
            )
            
            response_text = response.content[0].text.strip()
            print(f"✅ API test successful")
            print(f"   Sample response: {response_text[:100]}...")
            checks_passed += 1
        except Exception as e:
            print(f"❌ API test failed: {e}")
    else:
        print("⚠️ Skipping API test (no valid key)")
    
    # Summary
    print(f"\n📊 Setup Verification Summary:")
    print(f"   Checks passed: {checks_passed}/{total_checks}")
    print(f"   Success rate: {(checks_passed/total_checks)*100:.0f}%")
    
    if checks_passed >= 5:
        print("\n🎉 Setup is ready!")
        print("✅ You can run AI job title extraction:")
        print("   python utilities/ai_job_titles_updater.py --test --limit 2")
    elif checks_passed >= 3:
        print("\n⚠️ Setup mostly ready, minor issues:")
        print("💡 Fix the issues above and try again")
    else:
        print("\n❌ Setup needs attention:")
        print("📖 Check CLAUDE_API_SETUP.md for detailed instructions")
    
    return 0 if checks_passed >= 5 else 1

if __name__ == "__main__":
    sys.exit(verify_complete_setup())