#!/usr/bin/env python3
"""
Sector Correction Script

This script reads both the original and enhanced files, keeps the original sector
classifications (which were more accurate), but adds the new description and 
processed_at fields from the enhanced version.

Input files:
- data/complete_enhanced_jsonl.txt (original with better sectors)
- data/complete_enhanced_with_sectors_and_descriptions.jsonl (enhanced with descriptions)

Output:
- data/complete_corrected_with_descriptions.jsonl (best of both)
"""

import json
from pathlib import Path
from typing import Dict, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_original_data(file_path: str) -> Dict[str, Dict]:
    """Load original data and create lookup by organization name"""
    original_data = {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                org = json.loads(line)
                # Use name as key for lookup
                original_data[org['name']] = org
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON on line {line_num} in original file: {e}")
                continue
    
    logger.info(f"Loaded {len(original_data)} organizations from original file")
    return original_data

def load_enhanced_data(file_path: str) -> Dict[str, Dict]:
    """Load enhanced data and create lookup by organization name"""
    enhanced_data = {}
    
    if not Path(file_path).exists():
        logger.warning(f"Enhanced file not found: {file_path}")
        return enhanced_data
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                org = json.loads(line)
                # Use name as key for lookup
                enhanced_data[org['name']] = org
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON on line {line_num} in enhanced file: {e}")
                continue
    
    logger.info(f"Loaded {len(enhanced_data)} organizations from enhanced file")
    return enhanced_data

def merge_organization_data(original: Dict, enhanced: Optional[Dict]) -> Dict:
    """Merge original and enhanced data, preferring original sectors"""
    
    # Start with original data (keeps the better sector classification)
    merged = original.copy()
    
    # Add enhanced fields if available
    if enhanced:
        # Add description if it exists and is meaningful
        if 'description' in enhanced and enhanced['description']:
            # Only add if it's not a generic/poor description
            desc = enhanced['description'].strip()
            if (len(desc) > 10 and 
                not desc.lower().startswith('using cookies') and
                not desc.lower().startswith('them with') and
                'cookie' not in desc.lower()):
                merged['description'] = desc
        
        # Add processed timestamp
        if 'processed_at' in enhanced:
            merged['processed_at'] = enhanced['processed_at']
    
    return merged

def create_corrected_file(original_file: str, enhanced_file: str, output_file: str):
    """Create corrected file with original sectors and enhanced descriptions"""
    
    logger.info("Starting sector correction process...")
    
    # Load both datasets
    original_data = load_original_data(original_file)
    enhanced_data = load_enhanced_data(enhanced_file)
    
    # Track statistics
    stats = {
        'total_processed': 0,
        'descriptions_added': 0,
        'descriptions_skipped': 0,
        'sectors_preserved': 0,
        'not_found_in_enhanced': 0
    }
    
    # Create corrected dataset
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for name, original_org in original_data.items():
            # Get corresponding enhanced data if it exists
            enhanced_org = enhanced_data.get(name)
            
            # Merge the data
            corrected_org = merge_organization_data(original_org, enhanced_org)
            
            # Update statistics
            stats['total_processed'] += 1
            stats['sectors_preserved'] += 1  # We always preserve original sector
            
            if enhanced_org:
                if 'description' in corrected_org and corrected_org['description'] != original_org.get('description', ''):
                    stats['descriptions_added'] += 1
                else:
                    stats['descriptions_skipped'] += 1
            else:
                stats['not_found_in_enhanced'] += 1
            
            # Write corrected organization
            outfile.write(json.dumps(corrected_org, ensure_ascii=False) + '\n')
    
    # Log results
    logger.info("Sector correction completed!")
    logger.info(f"Statistics:")
    logger.info(f"  Total organizations processed: {stats['total_processed']}")
    logger.info(f"  Sectors preserved from original: {stats['sectors_preserved']}")
    logger.info(f"  Descriptions successfully added: {stats['descriptions_added']}")
    logger.info(f"  Descriptions skipped (poor quality): {stats['descriptions_skipped']}")
    logger.info(f"  Organizations not found in enhanced file: {stats['not_found_in_enhanced']}")
    
    return stats

def validate_output_file(output_file: str, original_count: int):
    """Validate the output file quality"""
    logger.info("Validating output file...")
    
    with open(output_file, 'r', encoding='utf-8') as f:
        count = 0
        sector_examples = {}
        description_count = 0
        
        for line in f:
            if line.strip():
                count += 1
                try:
                    org = json.loads(line)
                    
                    # Track sector diversity
                    sector = org.get('sector', 'Unknown')
                    if sector not in sector_examples:
                        sector_examples[sector] = []
                    if len(sector_examples[sector]) < 3:
                        sector_examples[sector].append(org['name'])
                    
                    # Count descriptions
                    if 'description' in org and org['description']:
                        description_count += 1
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON found in output file")
    
    logger.info(f"Validation Results:")
    logger.info(f"  Organizations in output: {count}")
    logger.info(f"  Expected from original: {original_count}")
    logger.info(f"  Organizations with descriptions: {description_count}")
    logger.info(f"  Unique sectors found: {len(sector_examples)}")
    
    logger.info(f"  Sector distribution examples:")
    for sector, examples in sector_examples.items():
        logger.info(f"    {sector}: {', '.join(examples)}")

def main():
    """Main correction process"""
    print("🔧 Starting Sector Correction Process")
    print("=" * 50)
    
    # File paths
    original_file = "data/complete_enhanced_jsonl.txt"
    enhanced_file = "data/complete_enhanced_with_sectors_and_descriptions.jsonl" 
    output_file = "data/complete_corrected_with_descriptions.jsonl"
    
    # Check if files exist
    if not Path(original_file).exists():
        print(f"❌ Error: Original file not found: {original_file}")
        return 1
    
    # Count original organizations
    original_count = 0
    with open(original_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                original_count += 1
    
    try:
        # Perform correction
        stats = create_corrected_file(original_file, enhanced_file, output_file)
        
        # Validate output
        validate_output_file(output_file, original_count)
        
        print(f"\n✅ Sector Correction Complete!")
        print(f"📥 Original file: {original_file}")
        print(f"📊 Enhanced file: {enhanced_file}")
        print(f"📤 Corrected output: {output_file}")
        print(f"\n📈 Results:")
        print(f"   🏷️  Preserved {stats['sectors_preserved']} original sector classifications")
        print(f"   📝 Added {stats['descriptions_added']} high-quality descriptions")
        print(f"   ⚠️  Skipped {stats['descriptions_skipped']} poor-quality descriptions")
        print(f"\n💡 The output file contains:")
        print(f"   ✅ Original, accurate sector classifications")
        print(f"   ✅ High-quality mission/vision descriptions where found")
        print(f"   ✅ Processing timestamps")
        print(f"   ✅ All original fields (name, root, jobs)")
        
    except Exception as e:
        logger.error(f"Error during correction process: {e}")
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())