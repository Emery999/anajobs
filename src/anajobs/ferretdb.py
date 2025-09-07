#!/usr/bin/env python3
"""
FerretDB Database Adapter for AnaJobs
MongoDB-compatible interface using FerretDB (PostgreSQL backend)
"""

import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, DuplicateKeyError
    FERRETDB_AVAILABLE = True
except ImportError:
    FERRETDB_AVAILABLE = False
    MongoClient = None

logger = logging.getLogger(__name__)


class FerretJobSiteDB:
    """FerretDB adapter with MongoDB-compatible interface"""
    
    def __init__(self, ferret_uri: str = "mongodb://localhost:27017/", 
                 database_name: str = "nonprofit_jobs"):
        """
        Initialize FerretDB connection
        
        Args:
            ferret_uri: FerretDB connection URI (MongoDB-compatible)
            database_name: Name of the database to create/use
        """
        if not FERRETDB_AVAILABLE:
            raise ImportError("FerretDB dependencies not installed. Run: pip install pymongo")
        
        self.ferret_uri = ferret_uri
        self.database_name = database_name
        self.client = None
        self.db = None
        self.collection_name = "organizations"
        
    def connect(self) -> bool:
        """
        Establish connection to FerretDB
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.client = MongoClient(self.ferret_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            logger.info(f"Successfully connected to FerretDB: {self.database_name}")
            return True
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to FerretDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to FerretDB: {e}")
            return False
    
    def setup_collection(self) -> bool:
        """
        Set up the organizations collection with indexes
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            collection = self.db[self.collection_name]
            
            # Create indexes for better query performance
            collection.create_index("name", unique=True)
            collection.create_index("root")
            collection.create_index("jobs")
            collection.create_index("status")
            collection.create_index("scraped")
            
            # Text index for full-text search
            collection.create_index([
                ("name", "text"),
                ("extracted_data.text", "text")
            ])
            
            logger.info(f"Collection '{self.collection_name}' setup complete with indexes")
            return True
        except Exception as e:
            logger.error(f"Failed to setup collection: {e}")
            return False
    
    def populate_database(self, organizations: List[Dict[str, str]]) -> bool:
        """
        Insert organization data into FerretDB
        
        Args:
            organizations: List of organization dictionaries
            
        Returns:
            bool: True if population successful, False otherwise
        """
        if not organizations or not self._is_connected():
            return False
            
        try:
            collection = self.db[self.collection_name]
            
            # Clear existing data
            collection.delete_many({})
            logger.info("Cleared existing data from collection")
            
            # Add default fields to organizations
            for org in organizations:
                org.setdefault('status', 'active')
                org.setdefault('scraped', False)
                org.setdefault('created_at', datetime.utcnow())
            
            # Insert all organizations
            result = collection.insert_many(organizations, ordered=False)
            
            logger.info(f"Successfully inserted {len(result.inserted_ids)} organizations")
            return True
            
        except DuplicateKeyError as e:
            logger.warning(f"Some duplicate entries were skipped: {e}")
            return True  # Partial success is still success
        except Exception as e:
            logger.error(f"Failed to populate database: {e}")
            return False
    
    def search_organizations(self, search_term: str, limit: int = 10) -> List[Dict]:
        """
        Search organizations by name or extracted content
        
        Args:
            search_term: Text to search for
            limit: Maximum number of results
            
        Returns:
            List of matching organizations
        """
        if not self._is_connected():
            return []
            
        try:
            collection = self.db[self.collection_name]
            
            # Try text search first (if indexed content exists)
            text_results = list(collection.find(
                {"$text": {"$search": search_term}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit))
            
            if text_results:
                return text_results
            
            # Fallback to regex search on name
            regex_results = list(collection.find(
                {"name": {"$regex": search_term, "$options": "i"}}
            ).limit(limit))
            
            logger.info(f"Found {len(regex_results)} organizations matching '{search_term}'")
            return regex_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_organizations_by_domain(self, domain_filter: str) -> List[Dict]:
        """
        Get organizations filtered by domain
        
        Args:
            domain_filter: Domain extension to filter by
            
        Returns:
            List of organizations with matching domains
        """
        if not self._is_connected():
            return []
            
        try:
            collection = self.db[self.collection_name]
            
            query = {"root": {"$regex": f"{domain_filter}", "$options": "i"}}
            results = list(collection.find(query))
            
            logger.info(f"Found {len(results)} organizations with domain '{domain_filter}'")
            return results
            
        except Exception as e:
            logger.error(f"Domain filter failed: {e}")
            return []
    
    def test_database(self, test_org_name: str = "Idealist") -> Dict:
        """
        Test database connectivity and queries
        
        Returns:
            Dictionary with test results
        """
        results = {
            "connection_test": False,
            "count_test": 0,
            "query_test": None,
            "sample_organizations": []
        }
        
        if not self._is_connected():
            return results
            
        try:
            collection = self.db[self.collection_name]
            
            # Test 1: Count documents
            count = collection.count_documents({})
            results["count_test"] = count
            results["connection_test"] = True
            
            # Test 2: Query specific organization
            org = collection.find_one({"name": {"$regex": test_org_name, "$options": "i"}})
            if org:
                # Convert ObjectId to string for JSON serialization
                if '_id' in org:
                    org['_id'] = str(org['_id'])
                results["query_test"] = org
            
            # Test 3: Get sample organizations
            sample = list(collection.find({}).limit(5))
            for org in sample:
                if '_id' in org:
                    org['_id'] = str(org['_id'])
            results["sample_organizations"] = sample
            
            logger.info(f"Database contains {count} organizations")
            return results
            
        except Exception as e:
            logger.error(f"Database test failed: {e}")
            return results
    
    def store_extracted_content(self, org_name: str, extracted_data: Dict[str, Any]) -> bool:
        """
        Store extracted content for an organization
        
        Args:
            org_name: Name of the organization
            extracted_data: Extracted content data
            
        Returns:
            bool: Success status
        """
        if not self._is_connected():
            return False
            
        try:
            collection = self.db[self.collection_name]
            
            result = collection.update_one(
                {"name": org_name},
                {
                    "$set": {
                        "extracted_data": extracted_data,
                        "scraped": True,
                        "last_scraped": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to store extracted content: {e}")
            return False
    
    def get_unscraped_organizations(self, limit: int = 10) -> List[Dict]:
        """
        Get organizations that haven't been scraped yet
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of unscraped organizations
        """
        if not self._is_connected():
            return []
            
        try:
            collection = self.db[self.collection_name]
            
            results = list(collection.find(
                {"scraped": {"$ne": True}},
                {"name": 1, "jobs": 1, "root": 1}
            ).limit(limit))
            
            # Convert ObjectIds to strings
            for org in results:
                if '_id' in org:
                    org['_id'] = str(org['_id'])
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get unscraped organizations: {e}")
            return []
    
    def update_scrape_status(self, org_name: str, status: bool, error_msg: str = None) -> bool:
        """
        Update the scrape status for an organization
        
        Args:
            org_name: Name of the organization
            status: Success/failure status
            error_msg: Optional error message if failed
            
        Returns:
            bool: Update success status
        """
        if not self._is_connected():
            return False
            
        try:
            collection = self.db[self.collection_name]
            
            update_data = {
                "scraped": status,
                "last_attempt": datetime.utcnow()
            }
            
            if error_msg:
                update_data["last_error"] = error_msg
            
            result = collection.update_one(
                {"name": org_name},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update scrape status: {e}")
            return False
    
    def _is_connected(self) -> bool:
        """Check if connected to database"""
        return self.client is not None and self.db is not None
    
    def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
        logger.info("FerretDB connection closed")


# Compatibility functions
def load_organizations_to_ferret(organizations: List[Dict], ferret_uri: str, database_name: str = "nonprofit_jobs") -> bool:
    """
    Convenience function to load organizations into FerretDB
    """
    db = FerretJobSiteDB(ferret_uri, database_name)
    
    if not db.connect():
        return False
        
    try:
        db.setup_collection()
        return db.populate_database(organizations)
    finally:
        db.close_connection()


def compare_databases(organizations: List[Dict], mongo_uri: str, ferret_uri: str):
    """
    Side-by-side comparison of MongoDB Atlas vs FerretDB performance
    """
    import time
    from .database import NonProfitJobSiteDB
    
    results = {
        "mongodb_atlas": {"setup_time": 0, "query_time": 0, "search_results": []},
        "ferretdb": {"setup_time": 0, "query_time": 0, "search_results": []}
    }
    
    # Test MongoDB Atlas
    print("Testing MongoDB Atlas...")
    start_time = time.time()
    mongo_db = NonProfitJobSiteDB(mongo_uri, "test_comparison_mongo")
    if mongo_db.connect():
        mongo_db.setup_collection()
        mongo_db.populate_database(organizations)
        results["mongodb_atlas"]["setup_time"] = time.time() - start_time
        
        # Test query
        start_time = time.time()
        results["mongodb_atlas"]["search_results"] = mongo_db.search_organizations("climate", 5)
        results["mongodb_atlas"]["query_time"] = time.time() - start_time
        
        mongo_db.close_connection()
    
    # Test FerretDB
    print("Testing FerretDB...")
    start_time = time.time()
    ferret_db = FerretJobSiteDB(ferret_uri, "test_comparison_ferret")
    if ferret_db.connect():
        ferret_db.setup_collection()
        ferret_db.populate_database(organizations)
        results["ferretdb"]["setup_time"] = time.time() - start_time
        
        # Test query
        start_time = time.time()
        results["ferretdb"]["search_results"] = ferret_db.search_organizations("climate", 5)
        results["ferretdb"]["query_time"] = time.time() - start_time
        
        ferret_db.close_connection()
    
    return results