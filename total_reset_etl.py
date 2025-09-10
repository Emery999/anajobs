#!/usr/bin/env python3
"""
Total Reset ETL Script for AnaJobs MongoDB Collections

This script provides total reset functionality for MongoDB collections:
- Completely clears specified collections
- Repopulates from zero using corrected data files
- Supports different input file formats

Usage:
    python total_reset_etl.py --total_reset data/complete_corrected_with_descriptions.jsonl --total_reset_collection organizations
"""

import json
import random
import argparse
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pathlib import Path
import logging
import time
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TotalResetETL:
    def __init__(self):
        self.uri = "mongodb+srv://seeotter_db_user:n8tfO3zzASvoxllr@cluster0.hxabnjn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.db_name = "social_impact_jobs"
        self.client = None
        self.db = None

    def connect_to_cloud_db(self):
        """Connect to MongoDB Atlas cloud instance"""
        try:
            self.client = MongoClient(self.uri, server_api=ServerApi('1'))
            # Ping to confirm connection
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            logger.info("✅ Successfully connected to MongoDB Atlas!")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB Atlas: {e}")
            return False

    def total_clear_collection(self, collection_name: str):
        """Completely clear all documents from a collection"""
        try:
            collection = self.db[collection_name]
            
            # Get current count for reporting
            current_count = collection.count_documents({})
            logger.info(f"📊 Current documents in '{collection_name}': {current_count}")
            
            if current_count == 0:
                logger.info(f"🔍 Collection '{collection_name}' is already empty")
                return True
            
            # Confirm the destructive operation
            logger.warning(f"⚠️  DESTRUCTIVE OPERATION: About to delete ALL {current_count} documents from '{collection_name}'")
            
            # Delete all documents
            result = collection.delete_many({})
            deleted_count = result.deleted_count
            
            logger.info(f"🗑️  Successfully deleted {deleted_count} documents from '{collection_name}'")
            
            # Verify collection is empty
            remaining_count = collection.count_documents({})
            if remaining_count == 0:
                logger.info(f"✅ Collection '{collection_name}' is now completely empty")
                return True
            else:
                logger.error(f"❌ Error: {remaining_count} documents still remain in '{collection_name}'")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error clearing collection '{collection_name}': {e}")
            return False

    def load_jsonl_data(self, file_path: str):
        """Load data from JSONL file with enhanced field handling"""
        organizations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            org = json.loads(line)
                            
                            # Ensure required fields exist
                            if 'name' not in org or 'root' not in org:
                                logger.warning(f"⚠️ Line {line_num}: Missing required fields (name/root)")
                                continue
                            
                            # Add default fields if missing, preserve existing ones
                            enhanced_org = {
                                'name': org['name'],
                                'root': org['root'],
                                'jobs': org.get('jobs', ''),
                                'sector': org.get('sector', 'Unknown'),
                                'status': org.get('status', 'active'),
                                'scraped': org.get('scraped', False),
                                'created_at': org.get('created_at', datetime.utcnow().isoformat()),
                                'last_scraped': org.get('last_scraped', None),
                                'processed_at': org.get('processed_at', None),
                                'description': org.get('description', None)
                            }
                            
                            organizations.append(enhanced_org)
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"⚠️ Invalid JSON on line {line_num}: {e}")
                            continue
            
            logger.info(f"✅ Loaded {len(organizations)} organizations from {file_path}")
            return organizations
        
        except FileNotFoundError:
            logger.error(f"❌ Error: File not found: {file_path}")
            return []
        except Exception as e:
            logger.error(f"❌ Error loading data: {e}")
            return []

    def setup_collection_indexes(self, collection_name: str):
        """Setup collection with proper indexes"""
        try:
            collection = self.db[collection_name]
            
            # Drop all existing indexes except _id (which can't be dropped)
            try:
                existing_indexes = collection.list_indexes()
                for index in existing_indexes:
                    if index['name'] != '_id_':
                        collection.drop_index(index['name'])
                        logger.info(f"🗑️ Dropped existing index: {index['name']}")
            except Exception as e:
                logger.warning(f"⚠️ Could not drop some indexes: {e}")
            
            # Create new indexes for better performance
            indexes = [
                ("name", 1),
                ("root", 1), 
                ("jobs", 1),
                ("sector", 1),
                ("status", 1),
                ("scraped", 1)
            ]
            
            for field, direction in indexes:
                try:
                    collection.create_index([(field, direction)])
                except Exception as e:
                    logger.warning(f"⚠️ Could not create index for {field}: {e}")
            
            # Create text index for search functionality
            try:
                collection.create_index([
                    ("name", "text"),
                    ("root", "text"),
                    ("description", "text")
                ])
                logger.info("✅ Created text search index for: name, root, description")
            except Exception as e:
                logger.warning(f"⚠️ Could not create text index: {e}")
            
            logger.info(f"✅ Setup indexes for collection '{collection_name}'")
            logger.info("✅ Created indexes for: name, root, jobs, sector, status, scraped")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up indexes for '{collection_name}': {e}")
            return False

    def populate_collection(self, collection_name: str, organizations: list):
        """Populate collection with organization data"""
        try:
            collection = self.db[collection_name]
            
            if not organizations:
                logger.error("❌ No organizations to insert")
                return False
            
            # Insert all data
            result = collection.insert_many(organizations)
            inserted_count = len(result.inserted_ids)
            
            logger.info(f"✅ Successfully inserted {inserted_count} organizations into '{collection_name}'")
            
            # Verify insertion
            total_count = collection.count_documents({})
            logger.info(f"📊 Total documents in '{collection_name}': {total_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error populating collection '{collection_name}': {e}")
            return False

    def perform_sanity_check(self, collection_name: str, num_samples: int = 5):
        """Perform sanity check on the reset collection"""
        try:
            collection = self.db[collection_name]
            
            # Get total count
            total_count = collection.count_documents({})
            logger.info(f"\n📊 Collection '{collection_name}' Statistics:")
            logger.info(f"   Total Organizations: {total_count}")
            
            if total_count == 0:
                logger.error("❌ No data found in collection after reset")
                return False
            
            # Get random sample
            pipeline = [{"$sample": {"size": min(num_samples, total_count)}}]
            sample_orgs = list(collection.aggregate(pipeline))
            
            logger.info(f"\n🎲 Random Sample of {len(sample_orgs)} Organizations:")
            logger.info("=" * 70)
            
            description_count = 0
            for i, org in enumerate(sample_orgs, 1):
                logger.info(f"{i}. {org['name']}")
                logger.info(f"   Root URL: {org['root']}")
                logger.info(f"   Jobs URL: {org.get('jobs', 'N/A')}")
                logger.info(f"   Sector: {org.get('sector', 'Unknown')}")
                logger.info(f"   Status: {org.get('status', 'Unknown')}")
                
                if org.get('description'):
                    description_count += 1
                    desc = org['description'][:80] + "..." if len(org['description']) > 80 else org['description']
                    logger.info(f"   Description: {desc}")
                
                if org.get('processed_at'):
                    logger.info(f"   Processed: {org['processed_at']}")
                
                logger.info("-" * 50)
            
            # Additional statistics
            logger.info(f"\n🔍 Additional Statistics:")
            
            # Count by sector
            sector_pipeline = [
                {"$group": {"_id": "$sector", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            sector_counts = list(collection.aggregate(sector_pipeline))
            
            logger.info(f"   Top sectors:")
            for sector in sector_counts[:5]:
                logger.info(f"     {sector['_id']}: {sector['count']} organizations")
            
            # Count organizations with descriptions
            with_descriptions = collection.count_documents({"description": {"$exists": True, "$ne": None, "$ne": ""}})
            logger.info(f"   Organizations with descriptions: {with_descriptions} ({with_descriptions/total_count*100:.1f}%)")
            
            # Count by status
            active_count = collection.count_documents({"status": "active"})
            logger.info(f"   Active organizations: {active_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during sanity check: {e}")
            return False

    def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("🔐 Database connection closed")


def main():
    """Main ETL reset process"""
    parser = argparse.ArgumentParser(
        description="Total Reset ETL for MongoDB Collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset organizations collection with corrected data
  python total_reset_etl.py --total_reset data/complete_corrected_with_descriptions.jsonl --total_reset_collection organizations
  
  # Reset aggregators collection 
  python total_reset_etl.py --total_reset data/aggregators_data.jsonl --total_reset_collection aggregators
        """
    )
    
    parser.add_argument('--total_reset', 
                       required=True,
                       help='Path to JSONL file for total reset data')
    
    parser.add_argument('--total_reset_collection',
                       required=True, 
                       help='Collection name to reset (e.g., organizations, aggregators)')
    
    args = parser.parse_args()
    
    print("🚨 TOTAL RESET ETL PROCESS")
    print("=" * 60)
    print(f"📁 Input file: {args.total_reset}")
    print(f"🗂️  Target collection: {args.total_reset_collection}")
    print("⚠️  WARNING: This will COMPLETELY DELETE all existing data!")
    print("=" * 60)
    
    # Confirmation prompt
    confirm = input("\n❓ Are you sure you want to proceed? Type 'YES' to continue: ")
    if confirm != 'YES':
        print("❌ Operation cancelled.")
        return 1
    
    etl = TotalResetETL()
    
    try:
        # Step 1: Connect to database
        print("\n1️⃣ Connecting to MongoDB Atlas...")
        if not etl.connect_to_cloud_db():
            return 1
        
        # Step 2: Load data from file
        print(f"\n2️⃣ Loading data from {args.total_reset}...")
        organizations = etl.load_jsonl_data(args.total_reset)
        if not organizations:
            return 1
        
        # Step 3: TOTAL CLEAR of collection
        print(f"\n3️⃣ CLEARING collection '{args.total_reset_collection}'...")
        if not etl.total_clear_collection(args.total_reset_collection):
            return 1
        
        # Step 4: Setup indexes
        print(f"\n4️⃣ Setting up indexes for '{args.total_reset_collection}'...")
        if not etl.setup_collection_indexes(args.total_reset_collection):
            return 1
        
        # Step 5: Populate with new data
        print(f"\n5️⃣ Populating '{args.total_reset_collection}' with new data...")
        if not etl.populate_collection(args.total_reset_collection, organizations):
            return 1
        
        # Step 6: Sanity check
        print(f"\n6️⃣ Performing sanity check...")
        if not etl.perform_sanity_check(args.total_reset_collection, 5):
            return 1
        
        # Success!
        print("\n🎉 TOTAL RESET COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"✅ Collection '{args.total_reset_collection}' completely reset")
        print(f"✅ Loaded {len(organizations)} organizations from {args.total_reset}")
        print(f"✅ Setup indexes for optimal performance")
        print(f"✅ Verified data integrity with sanity checks")
        print(f"✅ All data includes enhanced fields (descriptions, sectors, timestamps)")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ Operation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1
    finally:
        etl.close_connection()


if __name__ == "__main__":
    import sys
    sys.exit(main())