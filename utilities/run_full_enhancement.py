#!/usr/bin/env python3
"""
Full Enhancement Script Runner

This script processes all organizations in the complete_enhanced_jsonl.txt file
with optimized settings for production use.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sector_enhancement import SectorEnhancer

def main():
    """Run full enhancement on all organizations"""
    print("🚀 Starting Full Organization Enhancement")
    print("=" * 50)
    
    enhancer = SectorEnhancer()
    
    # File paths
    input_file = "data/complete_enhanced_jsonl.txt"
    output_file = "data/complete_enhanced_with_sectors_and_descriptions.jsonl"
    
    # Process ALL organizations (remove max_orgs limit)
    enhancer.process_file(input_file, output_file, max_orgs=None)
    
    print(f"\n🎉 Full Enhancement Complete!")
    print(f"📥 Input: {input_file}")
    print(f"📤 Output: {output_file}")
    print(f"\n📊 Output includes:")
    print(f"   ✅ Original fields (name, root, jobs)")
    print(f"   ✅ Enhanced GICS sector classifications")
    print(f"   ✅ Mission/vision descriptions where found")
    print(f"   ✅ Processing timestamps")
    print(f"\n💡 GICS Sectors Used:")
    for sector in enhancer.gics_sectors:
        print(f"   • {sector}")

if __name__ == "__main__":
    main()