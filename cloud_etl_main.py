#!/usr/bin/env python3
"""
Cloud MongoDB ETL Script for AnaJobs
Uses cloud MongoDB Atlas instance and processes complete_social_impact_database.jsonl
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


def load_jsonl_data(file_path):
    """Load data from JSONL file"""
    organizations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        org = json.loads(line)
                        # Add default fields for consistency with existing schema
                        org.update({
                            'status': 'active',
                            'scraped': False,
                            'created_at': None,
                            'last_scraped': None
                        })
                        organizations.append(org)
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Warning: Invalid JSON on line {line_num}: {e}")
                        continue
        
        print(f"✅ Loaded {len(organizations)} organizations from {file_path}")
        return organizations
    
    except FileNotFoundError:
        print(f"❌ Error: File not found: {file_path}")
        return []
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return []


def setup_database_and_collection(client, db_name="social_impact_jobs", collection_name="organizations"):
    """Setup database and collection with indexes"""
    try:
        db = client[db_name]
        collection = db[collection_name]
        
        # Create indexes for better performance
        indexes = [
            ("name", 1),
            ("root", 1), 
            ("jobs", 1),
            ("status", 1),
            ("scraped", 1)
        ]
        
        for field, direction in indexes:
            collection.create_index([(field, direction)])
        
        # Create text index for search functionality
        collection.create_index([
            ("name", "text"),
            ("root", "text")
        ])
        
        print(f"✅ Database '{db_name}' and collection '{collection_name}' setup complete")
        print("✅ Created indexes for: name, root, jobs, status, scraped")
        print("✅ Created text search index")
        
        return db, collection
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return None, None


def populate_collection(collection, organizations):
    """Populate collection with organization data"""
    try:
        # Clear existing data
        result = collection.delete_many({})
        if result.deleted_count > 0:
            print(f"🗑️ Cleared {result.deleted_count} existing documents")
        
        # Insert new data
        if organizations:
            result = collection.insert_many(organizations)
            print(f"✅ Successfully inserted {len(result.inserted_ids)} organizations")
            return True
        else:
            print("❌ No organizations to insert")
            return False
            
    except Exception as e:
        print(f"❌ Error populating collection: {e}")
        return False


def perform_sanity_check(collection, num_samples=5):
    """Randomly select and display test entries for sanity check"""
    try:
        # Get total count
        total_count = collection.count_documents({})
        print(f"\n📊 Database Statistics:")
        print(f"   Total Organizations: {total_count}")
        
        if total_count == 0:
            print("❌ No data found for sanity check")
            return False
        
        # Get random sample
        pipeline = [{"$sample": {"size": min(num_samples, total_count)}}]
        sample_orgs = list(collection.aggregate(pipeline))
        
        print(f"\n🎲 Random Sample of {len(sample_orgs)} Organizations:")
        print("=" * 60)
        
        for i, org in enumerate(sample_orgs, 1):
            print(f"{i}. {org['name']}")
            print(f"   Root URL: {org['root']}")
            print(f"   Jobs URL: {org['jobs']}")
            print(f"   Status: {org['status']}")
            print(f"   Scraped: {org['scraped']}")
            print("-" * 40)
        
        # Test some basic queries
        print("\n🔍 Quick Query Tests:")
        
        # Count by domain type
        org_domains = collection.count_documents({"root": {"$regex": r"\.org(/|$)"}})
        com_domains = collection.count_documents({"root": {"$regex": r"\.com(/|$)"}})
        
        print(f"   .org domains: {org_domains}")
        print(f"   .com domains: {com_domains}")
        print(f"   Other domains: {total_count - org_domains - com_domains}")
        
        # Test text search
        search_result = collection.find({"$text": {"$search": "health"}}).limit(3)
        health_orgs = list(search_result)
        print(f"   Organizations mentioning 'health': {len(health_orgs)}")
        
        if health_orgs:
            print("   Sample health organizations:")
            for org in health_orgs:
                print(f"     - {org['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during sanity check: {e}")
        return False


def main():
    """Main ETL process"""
    print("🚀 Starting Cloud MongoDB ETL Process")
    print("=" * 50)
    
    # File path for the JSONL data
    data_file = Path("data/complete_social_impact_database.jsonl")
    
    # Step 1: Connect to cloud database
    print("\n1️⃣ Connecting to MongoDB Atlas...")
    client = connect_to_cloud_db()
    if not client:
        return 1
    
    # Step 2: Load data from JSONL file
    print("\n2️⃣ Loading data from JSONL file...")
    organizations = load_jsonl_data(data_file)
    if not organizations:
        client.close()
        return 1
    
    # Step 3: Setup database and collection
    print("\n3️⃣ Setting up database and collection...")
    db, collection = setup_database_and_collection(client)
    if collection is None:
        client.close()
        return 1
    
    # Step 4: Populate database
    print("\n4️⃣ Populating database...")
    if not populate_collection(collection, organizations):
        client.close()
        return 1
    
    # Step 5: Perform sanity check
    print("\n5️⃣ Performing sanity check...")
    if not perform_sanity_check(collection, 5):
        client.close()
        return 1
    
    # Success!
    print("\n🎉 ETL Process Completed Successfully!")
    print("=" * 50)
    print("✅ Connected to MongoDB Atlas")
    print(f"✅ Loaded {len(organizations)} organizations")
    print("✅ Setup database with proper indexes")
    print("✅ Populated collection with all data")
    print("✅ Verified data integrity with sanity checks")
    
    # Close connection
    client.close()
    print("\n🔐 Database connection closed")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())