#!/usr/bin/env python3
"""
Non-interactive Total Reset Runner

Runs the total reset ETL process without requiring interactive confirmation.
"""

import sys
import os
from datetime import datetime

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from total_reset_etl import TotalResetETL

def run_reset():
    """Run the total reset process non-interactively"""
    
    # Configuration
    input_file = "data/complete_corrected_with_descriptions.jsonl"
    collection_name = "organizations"
    
    print("🚨 TOTAL RESET ETL PROCESS")
    print("=" * 60)
    print(f"📁 Input file: {input_file}")
    print(f"🗂️  Target collection: {collection_name}")
    print("⚠️  WARNING: This will COMPLETELY DELETE all existing data!")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    etl = TotalResetETL()
    
    try:
        # Step 1: Connect to database
        print("\n1️⃣ Connecting to MongoDB Atlas...")
        if not etl.connect_to_cloud_db():
            return 1
        
        # Step 2: Load data from file
        print(f"\n2️⃣ Loading data from {input_file}...")
        organizations = etl.load_jsonl_data(input_file)
        if not organizations:
            return 1
        
        # Step 3: TOTAL CLEAR of collection
        print(f"\n3️⃣ CLEARING collection '{collection_name}'...")
        if not etl.total_clear_collection(collection_name):
            return 1
        
        # Step 4: Setup indexes
        print(f"\n4️⃣ Setting up indexes for '{collection_name}'...")
        if not etl.setup_collection_indexes(collection_name):
            return 1
        
        # Step 5: Populate with new data
        print(f"\n5️⃣ Populating '{collection_name}' with new data...")
        if not etl.populate_collection(collection_name, organizations):
            return 1
        
        # Step 6: Sanity check
        print(f"\n6️⃣ Performing sanity check...")
        if not etl.perform_sanity_check(collection_name, 5):
            return 1
        
        # Success!
        print("\n🎉 TOTAL RESET COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"✅ Collection '{collection_name}' completely reset")
        print(f"✅ Loaded {len(organizations)} organizations from {input_file}")
        print(f"✅ Setup indexes for optimal performance")
        print(f"✅ Verified data integrity with sanity checks")
        print(f"✅ All data includes enhanced fields (descriptions, sectors, timestamps)")
        print(f"🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ Operation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    finally:
        etl.close_connection()

if __name__ == "__main__":
    sys.exit(run_reset())