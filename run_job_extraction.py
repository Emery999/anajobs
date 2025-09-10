#!/usr/bin/env python3
"""
Production Job Extraction Runner

Runs job extraction with the default parameters specified in requirements:
- site_limit: 5 (default)
- output: sample_jobs_extraction_5.jsonl
"""

import sys
import os
from pathlib import Path

# Add utilities to path
sys.path.append(str(Path(__file__).parent / "utilities"))

from job_extractor import JobExtractor

def main():
    """Run job extraction with production settings"""
    
    print("🚀 Starting Production Job Extraction")
    print("=" * 60)
    print("🔧 Settings:")
    print("   📊 Site limit: 5 organizations")
    print("   📁 Output file: sample_jobs_extraction_5.jsonl")
    print("   🤖 AI Parsing: Claude AI (if API key available)")
    print("   🔄 Fallback: Regex-based parsing (if no API key)")
    print("=" * 60)
    
    # Check for Claude API key
    claude_api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if claude_api_key:
        print("✅ Claude AI API key found - using advanced AI parsing")
    else:
        print("⚠️  No Claude AI API key - using fallback parsing")
        print("💡 Set ANTHROPIC_API_KEY environment variable for AI parsing")
    
    print("\n🏃 Starting extraction process...")
    
    # Initialize extractor
    extractor = JobExtractor(claude_api_key=claude_api_key)
    
    try:
        # Run extraction with specified parameters
        success = extractor.process_organizations(
            site_limit=5,
            output_file="sample_jobs_extraction_5.jsonl"
        )
        
        if success:
            print("\n🎉 Job Extraction Completed Successfully!")
            print("=" * 60)
            print("📁 Output file: sample_jobs_extraction_5.jsonl")
            
            # Display sample of results
            try:
                with open("sample_jobs_extraction_5.jsonl", 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                print(f"📊 Organizations processed: {len(lines)}")
                
                total_jobs = 0
                total_categories = 0
                
                for line in lines:
                    if line.strip():
                        import json
                        org_data = json.loads(line)
                        job_count = org_data.get('extraction_metadata', {}).get('jobs_found', 0)
                        total_jobs += job_count
                        
                        categories = org_data.get('extraction_metadata', {}).get('categories_detected', [])
                        total_categories += len(categories)
                
                print(f"📋 Total jobs extracted: {total_jobs}")
                print(f"🏷️  Total job categories detected: {total_categories}")
                
                # Show first organization sample
                if lines:
                    sample_org = json.loads(lines[0])
                    print(f"\n📋 Sample Organization:")
                    print(f"   🏢 Name: {sample_org['name']}")
                    print(f"   🔗 Jobs URL: {sample_org.get('jobs', 'N/A')}")
                    print(f"   📊 Jobs found: {sample_org.get('extraction_metadata', {}).get('jobs_found', 0)}")
                    print(f"   🏷️  Categories: {sample_org.get('extraction_metadata', {}).get('categories_detected', [])}")
                    
                    # Show first job sample
                    jobs = sample_org.get('extracted_jobs', [])
                    if jobs:
                        job = jobs[0]
                        print(f"\n📝 Sample Job:")
                        print(f"   🆔 ID: {job.get('job_id', 'N/A')}")
                        print(f"   📋 Title: {job.get('position', {}).get('title', 'N/A')}")
                        print(f"   🏢 Department: {job.get('position', {}).get('department', 'N/A')}")
                        print(f"   🏷️  Parent Category: {job.get('parent_category', 'N/A')}")
                        print(f"   📍 Location Type: {job.get('location', {}).get('type', 'N/A')}")
                        
            except Exception as e:
                print(f"⚠️ Could not display sample results: {e}")
            
            print(f"\n💡 Next Steps:")
            print(f"   📂 Review the output file: sample_jobs_extraction_5.jsonl")
            print(f"   🔍 Each organization entry contains:")
            print(f"     • All original organization fields")
            print(f"     • Extraction metadata (date, categories detected)")
            print(f"     • Array of extracted jobs with full schema compliance")
            print(f"     • Parent category mapping for jobs")
            
            return 0
        else:
            print("\n❌ Job extraction failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())