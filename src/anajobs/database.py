#!/usr/bin/env python3
"""
MongoDB Setup Script for Non-Profit Job Site Data
Parses the corrupted JSONL file, cleans the data, and populates MongoDB
"""

import os
import re
import json
import logging
from typing import List, Dict, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mongodb_setup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NonProfitJobSiteDB:
    """Manages MongoDB operations for non-profit job site data"""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", 
                 database_name: str = "nonprofit_jobs"):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB connection URI
            database_name: Name of the database to create/use
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client = None
        self.db = None
        self.collection_name = "organizations"
        
    def connect(self) -> bool:
        """
        Establish connection to MongoDB
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            logger.info(f"Successfully connected to MongoDB: {self.database_name}")
            return True
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
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
            
            logger.info(f"Collection '{self.collection_name}' setup complete with indexes")
            return True
        except Exception as e:
            logger.error(f"Failed to setup collection: {e}")
            return False
    
    def parse_corrupted_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Parse the corrupted JSONL file and extract organization data
        
        Args:
            file_path: Path to the corrupted data file
            
        Returns:
            List of cleaned organization dictionaries
        """
        organizations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            logger.info(f"Processing {len(lines)} lines from {file_path}")
            
            for i, line in enumerate(lines, 1):
                org_data = self._extract_org_data(line.strip())
                if org_data:
                    organizations.append(org_data)
                else:
                    logger.warning(f"Failed to parse line {i}: {line[:100]}...")
            
            logger.info(f"Successfully parsed {len(organizations)} organizations")
            return organizations
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return []
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []
    
    def _extract_org_data(self, line: str) -> Optional[Dict[str, str]]:
        """
        Extract organization data from a corrupted JSON line
        
        Args:
            line: Single line from the corrupted file
            
        Returns:
            Dictionary with name, root, and jobs fields or None if parsing fails
        """
        try:
            # Extract organization name
            name_match = re.search(r'"name":"([^"]+)"', line)
            if not name_match:
                return None
            
            name = name_match.group(1)
            
            # Extract URLs - look for https:// patterns
            url_pattern = r'https://[^\s",%]+'
            urls = re.findall(url_pattern, line)
            
            if len(urls) < 2:
                return None
            
            # First URL is typically the root, second is jobs page
            root_url = urls[0]
            jobs_url = urls[1]
            
            # Clean up any trailing characters
            root_url = re.sub(r'[^\w\-\./:]+$', '', root_url)
            jobs_url = re.sub(r'[^\w\-\./:]+$', '', jobs_url)
            
            return {
                "name": name,
                "root": root_url,
                "jobs": jobs_url,
                "status": "active",  # Add status field for future use
                "scraped": False     # Track which sites have been scraped
            }
            
        except Exception as e:
            logger.debug(f"Error extracting data from line: {e}")
            return None
    
    def populate_database(self, organizations: List[Dict[str, str]]) -> bool:
        """
        Insert organization data into MongoDB
        
        Args:
            organizations: List of organization dictionaries
            
        Returns:
            bool: True if population successful, False otherwise
        """
        if not organizations:
            logger.warning("No organizations to insert")
            return False
        
        try:
            collection = self.db[self.collection_name]
            
            # Clear existing data (optional - comment out to preserve existing data)
            collection.delete_many({})
            logger.info("Cleared existing data from collection")
            
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
    
    def test_database(self, test_org_name: str = "American Red Cross") -> Dict:
        """
        Test database connectivity and queries
        
        Args:
            test_org_name: Name of organization to search for
            
        Returns:
            Dictionary with test results
        """
        results = {
            "connection_test": False,
            "count_test": 0,
            "query_test": None,
            "sample_organizations": []
        }
        
        try:
            collection = self.db[self.collection_name]
            
            # Test 1: Count documents
            count = collection.count_documents({})
            results["count_test"] = count
            results["connection_test"] = True
            logger.info(f"Database contains {count} organizations")
            
            # Test 2: Query specific organization
            org = collection.find_one({"name": test_org_name})
            results["query_test"] = org
            
            if org:
                logger.info(f"Found test organization: {org['name']}")
                logger.info(f"  Root URL: {org['root']}")
                logger.info(f"  Jobs URL: {org['jobs']}")
            else:
                logger.warning(f"Test organization '{test_org_name}' not found")
            
            # Test 3: Get sample of organizations
            sample = list(collection.find({}).limit(5))
            results["sample_organizations"] = sample
            
            logger.info("Sample organizations in database:")
            for i, org in enumerate(sample, 1):
                logger.info(f"  {i}. {org['name']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Database test failed: {e}")
            return results
    
    def search_organizations(self, search_term: str, limit: int = 10) -> List[Dict]:
        """
        Search organizations by name (case-insensitive)
        
        Args:
            search_term: Text to search for in organization names
            limit: Maximum number of results to return
            
        Returns:
            List of matching organizations
        """
        try:
            collection = self.db[self.collection_name]
            
            # Case-insensitive regex search
            query = {"name": {"$regex": search_term, "$options": "i"}}
            results = list(collection.find(query).limit(limit))
            
            logger.info(f"Found {len(results)} organizations matching '{search_term}'")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_organizations_by_domain(self, domain_filter: str) -> List[Dict]:
        """
        Get organizations filtered by domain (e.g., '.org', '.com')
        
        Args:
            domain_filter: Domain extension to filter by
            
        Returns:
            List of organizations with matching domains
        """
        try:
            collection = self.db[self.collection_name]
            
            query = {"root": {"$regex": f"{domain_filter}", "$options": "i"}}
            results = list(collection.find(query))
            
            logger.info(f"Found {len(results)} organizations with domain '{domain_filter}'")
            return results
            
        except Exception as e:
            logger.error(f"Domain filter failed: {e}")
            return []
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

def main():
    """Main execution function"""
    
    # Configuration
    DATA_FILE = "publicserviceopenings copy.txt"  # Update path as needed
    DB_CONNECTION = "mongodb://localhost:27017/"  # Update for your MongoDB instance
    DATABASE_NAME = "nonprofit_jobs"
    
    # Initialize database manager
    db_manager = NonProfitJobSiteDB(DB_CONNECTION, DATABASE_NAME)
    
    try:
        # Step 1: Connect to MongoDB
        logger.info("Step 1: Connecting to MongoDB...")
        if not db_manager.connect():
            logger.error("Failed to connect to MongoDB. Ensure MongoDB is running.")
            return False
        
        # Step 2: Setup collection and indexes
        logger.info("Step 2: Setting up collection...")
        if not db_manager.setup_collection():
            logger.error("Failed to setup collection")
            return False
        
        # Step 3: Parse data file
        logger.info("Step 3: Parsing data file...")
        organizations = db_manager.parse_corrupted_file(DATA_FILE)
        
        if not organizations:
            logger.error("No organizations found in data file")
            return False
        
        # Step 4: Populate database
        logger.info("Step 4: Populating database...")
        if not db_manager.populate_database(organizations):
            logger.error("Failed to populate database")
            return False
        
        # Step 5: Test database
        logger.info("Step 5: Testing database...")
        test_results = db_manager.test_database()
        
        if test_results["connection_test"]:
            logger.info("✅ Database setup completed successfully!")
            logger.info(f"✅ Total organizations: {test_results['count_test']}")
            
            # Additional test queries
            logger.info("\n--- Additional Test Queries ---")
            
            # Search for environmental organizations
            env_orgs = db_manager.search_organizations("environmental", 3)
            logger.info(f"Environmental organizations sample: {[org['name'] for org in env_orgs]}")
            
            # Count .org domains
            org_domains = db_manager.get_organizations_by_domain(".org")
            logger.info(f"Organizations with .org domains: {len(org_domains)}")
            
            return True
        else:
            logger.error("❌ Database tests failed")
            return False
            
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        return False
    
    finally:
        db_manager.close_connection()

if __name__ == "__main__":
    # Example usage and additional functions
    
    print("MongoDB Non-Profit Job Sites Setup")
    print("=" * 40)
    
    # Check if required dependencies are available
    try:
        import pymongo
        print(f"✅ PyMongo version: {pymongo.__version__}")
    except ImportError:
        print("❌ PyMongo not installed. Install with: pip install pymongo")
        exit(1)
    
    # Run main setup
    success = main()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Use the database for your job scraping project")
        print("2. Query organizations by name, domain, or other criteria")
        print("3. Update scraped status as you process each site")
        
        # Example query code
        print("\n--- Example Usage ---")
        print("""
# Connect to database
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
db = client['nonprofit_jobs']
collection = db['organizations']

# Find specific organization
org = collection.find_one({"name": "American Red Cross"})
print(f"Jobs URL: {org['jobs']}")

# Find all environmental organizations
env_orgs = collection.find({"name": {"$regex": "environment", "$options": "i"}})
for org in env_orgs:
    print(f"{org['name']}: {org['jobs']}")

# Update scraped status
collection.update_one(
    {"name": "American Red Cross"}, 
    {"$set": {"scraped": True, "last_scraped": "2024-03-20"}}
)
        """)
    else:
        print("❌ Setup failed. Check logs for details.")
        exit(1)