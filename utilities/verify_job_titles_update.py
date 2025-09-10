#!/usr/bin/env python3
"""
Verify Job Titles Update

Check that the job_titles field has been added to organizations
"""

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import json

def verify_updates():
    """Verify that job_titles field was added to organizations"""
    
    # Connect to MongoDB
    uri = "mongodb+srv://seeotter_db_user:n8tfO3zzASvoxllr@cluster0.hxabnjn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client["social_impact_jobs"]
        collection = db["organizations"]
        
        print("🔍 Verifying Job Titles Updates")
        print("=" * 40)
        
        # Check first few organizations
        orgs = list(collection.find().limit(5))
        
        for i, org in enumerate(orgs, 1):
            name = org.get('name', 'Unknown')
            job_titles = org.get('job_titles')
            job_titles_updated_at = org.get('job_titles_updated_at')
            
            print(f"{i}. {name}")
            print(f"   job_titles: {job_titles}")
            print(f"   updated_at: {job_titles_updated_at}")
            print()
        
        # Get statistics
        total_count = collection.count_documents({})
        with_job_titles = collection.count_documents({"job_titles": {"$ne": None}})
        with_null_titles = collection.count_documents({"job_titles": None})
        with_field = collection.count_documents({"job_titles": {"$exists": True}})
        
        print("📊 Statistics:")
        print(f"   Total organizations: {total_count}")
        print(f"   With job_titles field: {with_field}")
        print(f"   With job titles (not null): {with_job_titles}")
        print(f"   With null job_titles: {with_null_titles}")
        
        client.close()
        
        if with_field > 0:
            print("✅ job_titles field has been added to organizations!")
        else:
            print("❌ No job_titles field found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_updates()