#!/usr/bin/env python3
"""
Aggregators Collection ETL Script for AnaJobs
Processes social_impact_job_boards_all_apis_sept06.jsonl into 'aggregators' collection
"""

import json
import random
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pathlib import Path


def connect_to_cloud_db():
    """Connect to MongoDB Atlas cloud instance"""
    uri = "mongodb+srv://seeotter_db_user:n8tfO3zzASvoxllr@cluster0.hxabnjn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        # Ping to confirm connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB Atlas: {e}")
        return None


def load_aggregators_jsonl_data(file_path):
    """Load aggregator data from JSONL file"""
    aggregators = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        aggregator = json.loads(line)
                        # Add default fields for consistency
                        aggregator.update({
                            'status': 'active',
                            'scraped': False,
                            'created_at': None,
                            'last_scraped': None,
                            'has_api': aggregator.get('api', 'unknown').lower() == 'true',
                            'api_status': aggregator.get('api', 'unknown').lower(),
                            'api_type_status': aggregator.get('api_type', 'unknown').lower()
                        })
                        aggregators.append(aggregator)
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Warning: Invalid JSON on line {line_num}: {e}")
                        continue
        
        print(f"✅ Loaded {len(aggregators)} aggregators from {file_path}")
        return aggregators
    
    except FileNotFoundError:
        print(f"❌ Error: File not found: {file_path}")
        return []
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return []


def setup_aggregators_collection(client, db_name="social_impact_jobs", collection_name="aggregators"):
    """Setup aggregators collection with indexes"""
    try:
        db = client[db_name]
        collection = db[collection_name]
        
        # Create indexes for better performance
        indexes = [
            ("name", 1),
            ("root", 1), 
            ("jobs", 1),
            ("status", 1),
            ("scraped", 1),
            ("has_api", 1),
            ("api_status", 1),
            ("api_type_status", 1)
        ]
        
        for field, direction in indexes:
            collection.create_index([(field, direction)])
        
        # Create text index for search functionality
        collection.create_index([
            ("name", "text"),
            ("root", "text")
        ])
        
        print(f"✅ Database '{db_name}' and collection '{collection_name}' setup complete")
        print("✅ Created indexes for: name, root, jobs, status, scraped, has_api, api_status, api_type_status")
        print("✅ Created text search index")
        
        return db, collection
        
    except Exception as e:
        print(f"❌ Error setting up collection: {e}")
        return None, None


def populate_aggregators_collection(collection, aggregators):
    """Populate aggregators collection with data"""
    try:
        # Clear existing data
        result = collection.delete_many({})
        if result.deleted_count > 0:
            print(f"🗑️ Cleared {result.deleted_count} existing documents")
        
        # Insert new data
        if aggregators:
            result = collection.insert_many(aggregators)
            print(f"✅ Successfully inserted {len(result.inserted_ids)} aggregators")
            return True
        else:
            print("❌ No aggregators to insert")
            return False
            
    except Exception as e:
        print(f"❌ Error populating collection: {e}")
        return False


def perform_aggregators_sanity_check(collection, num_samples=5):
    """Randomly select and display test entries for sanity check"""
    try:
        # Get total count
        total_count = collection.count_documents({})
        print(f"\n📊 Aggregators Database Statistics:")
        print(f"   Total Job Board Aggregators: {total_count}")
        
        if total_count == 0:
            print("❌ No data found for sanity check")
            return False
        
        # Get random sample
        pipeline = [{"$sample": {"size": min(num_samples, total_count)}}]
        sample_aggregators = list(collection.aggregate(pipeline))
        
        print(f"\n🎲 Random Sample of {len(sample_aggregators)} Job Board Aggregators:")
        print("=" * 70)
        
        for i, agg in enumerate(sample_aggregators, 1):
            print(f"{i}. {agg['name']}")
            print(f"   Root URL: {agg['root']}")
            print(f"   Jobs URL: {agg['jobs']}")
            print(f"   API Available: {agg.get('api', 'unknown')}")
            print(f"   API Type: {agg.get('api_type', 'unknown')}")
            print(f"   Has API (boolean): {agg['has_api']}")
            print(f"   Status: {agg['status']}")
            print("-" * 50)
        
        # Test some basic queries
        print("\n🔍 Aggregators Analysis:")
        
        # Count by API availability
        with_api = collection.count_documents({"has_api": True})
        without_api = collection.count_documents({"has_api": False})
        unknown_api = collection.count_documents({"api_status": "unknown"})
        
        print(f"   With API: {with_api}")
        print(f"   Without API: {without_api}")
        print(f"   Unknown API status: {unknown_api}")
        
        # Count by API type
        public_api = collection.count_documents({"api_type_status": "public"})
        private_api = collection.count_documents({"api_type_status": "private"})
        unknown_type = collection.count_documents({"api_type_status": "unknown"})
        
        print(f"   Public APIs: {public_api}")
        print(f"   Private APIs: {private_api}")
        print(f"   Unknown API type: {unknown_type}")
        
        # Domain analysis
        org_domains = collection.count_documents({"root": {"$regex": r"\.org(/|$)"}})
        com_domains = collection.count_documents({"root": {"$regex": r"\.com(/|$)"}})
        
        print(f"   .org domains: {org_domains}")
        print(f"   .com domains: {com_domains}")
        print(f"   Other domains: {total_count - org_domains - com_domains}")
        
        # Test text search for common terms
        search_terms = ["job", "impact", "nonprofit"]
        for term in search_terms:
            search_result = collection.find({"$text": {"$search": term}}).limit(3)
            results = list(search_result)
            if results:
                print(f"   Aggregators mentioning '{term}': {len(results)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during sanity check: {e}")
        return False


def main():
    """Main ETL process for aggregators"""
    print("🚀 Starting Aggregators Collection ETL Process")
    print("=" * 55)
    
    # File path for the aggregators JSONL data
    data_file = Path("data/social_impact_job_boards_all_apis_sept06.jsonl")
    
    # Step 1: Connect to cloud database
    print("\n1️⃣ Connecting to MongoDB Atlas...")
    client = connect_to_cloud_db()
    if not client:
        return 1
    
    # Step 2: Load data from JSONL file
    print("\n2️⃣ Loading aggregators data from JSONL file...")
    aggregators = load_aggregators_jsonl_data(data_file)
    if not aggregators:
        client.close()
        return 1
    
    # Step 3: Setup database and collection
    print("\n3️⃣ Setting up aggregators collection...")
    db, collection = setup_aggregators_collection(client)
    if collection is None:
        client.close()
        return 1
    
    # Step 4: Populate database
    print("\n4️⃣ Populating aggregators collection...")
    if not populate_aggregators_collection(collection, aggregators):
        client.close()
        return 1
    
    # Step 5: Perform sanity check
    print("\n5️⃣ Performing aggregators sanity check...")
    if not perform_aggregators_sanity_check(collection, 5):
        client.close()
        return 1
    
    # Success!
    print("\n🎉 Aggregators ETL Process Completed Successfully!")
    print("=" * 55)
    print("✅ Connected to MongoDB Atlas")
    print(f"✅ Loaded {len(aggregators)} job board aggregators")
    print("✅ Setup aggregators collection with proper indexes")
    print("✅ Populated collection with all aggregator data")
    print("✅ Verified data integrity with sanity checks")
    print("\n📝 Collection Details:")
    print("   Database: social_impact_jobs")
    print("   Collection: aggregators")
    
    # Close connection
    client.close()
    print("\n🔐 Database connection closed")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())