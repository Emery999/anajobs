"""
Tests for database module
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

from anajobs.database import NonProfitJobSiteDB


class TestNonProfitJobSiteDB:
    """Test cases for NonProfitJobSiteDB class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.db_manager = NonProfitJobSiteDB(
            "mongodb://localhost:27017/", 
            "test_nonprofit_jobs"
        )
    
    def test_init(self):
        """Test database manager initialization"""
        assert self.db_manager.connection_string == "mongodb://localhost:27017/"
        assert self.db_manager.database_name == "test_nonprofit_jobs"
        assert self.db_manager.collection_name == "organizations"
        assert self.db_manager.client is None
        assert self.db_manager.db is None
    
    @patch('anajobs.database.MongoClient')
    def test_connect_success(self, mock_mongo_client):
        """Test successful MongoDB connection"""
        # Mock successful connection
        mock_client = Mock()
        mock_client.admin.command.return_value = True
        mock_mongo_client.return_value = mock_client
        
        result = self.db_manager.connect()
        
        assert result is True
        assert self.db_manager.client == mock_client
        mock_mongo_client.assert_called_once_with(
            "mongodb://localhost:27017/", 
            serverSelectionTimeoutMS=5000
        )
    
    @patch('anajobs.database.MongoClient')
    def test_connect_failure(self, mock_mongo_client):
        """Test failed MongoDB connection"""
        from pymongo.errors import ConnectionFailure
        
        # Mock connection failure
        mock_mongo_client.side_effect = ConnectionFailure("Connection failed")
        
        result = self.db_manager.connect()
        
        assert result is False
        assert self.db_manager.client is None
    
    def test_extract_org_data_valid(self):
        """Test extracting organization data from valid line"""
        line = '{"name":"Test Organization","url":"https://test.org","jobs":"https://test.org/jobs"}'
        
        result = self.db_manager._extract_org_data(line)
        
        assert result is not None
        assert result["name"] == "Test Organization"
        assert "https://test.org" in result["root"]
        assert "https://test.org/jobs" in result["jobs"]
        assert result["status"] == "active"
        assert result["scraped"] is False
    
    def test_extract_org_data_invalid(self):
        """Test extracting organization data from invalid line"""
        line = 'invalid json line with no proper format'
        
        result = self.db_manager._extract_org_data(line)
        
        assert result is None
    
    def test_extract_org_data_no_urls(self):
        """Test extracting organization data with no URLs"""
        line = '{"name":"Test Organization"}'
        
        result = self.db_manager._extract_org_data(line)
        
        assert result is None
    
    def test_parse_corrupted_file_valid(self):
        """Test parsing a valid data file"""
        # Create temporary test file
        test_data = '''{"name":"Org1","root":"https://org1.org","jobs":"https://org1.org/jobs"}
{"name":"Org2","root":"https://org2.org","jobs":"https://org2.org/careers"}'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(test_data)
            temp_file_path = f.name
        
        try:
            result = self.db_manager.parse_corrupted_file(temp_file_path)
            
            assert len(result) == 2
            assert result[0]["name"] == "Org1"
            assert result[1]["name"] == "Org2"
        finally:
            os.unlink(temp_file_path)
    
    def test_parse_corrupted_file_not_found(self):
        """Test parsing non-existent file"""
        result = self.db_manager.parse_corrupted_file("nonexistent_file.jsonl")
        
        assert result == []
    
    @patch('anajobs.database.NonProfitJobSiteDB.connect')
    def test_setup_collection_success(self, mock_connect):
        """Test successful collection setup"""
        # Mock database and collection
        mock_collection = Mock()
        mock_db = Mock()
        mock_db.__getitem__.return_value = mock_collection
        
        self.db_manager.db = mock_db
        
        result = self.db_manager.setup_collection()
        
        assert result is True
        mock_collection.create_index.assert_any_call("name", unique=True)
        mock_collection.create_index.assert_any_call("root")
        mock_collection.create_index.assert_any_call("jobs")
    
    @patch('anajobs.database.NonProfitJobSiteDB.connect')
    def test_populate_database_success(self, mock_connect):
        """Test successful database population"""
        # Mock database and collection
        mock_collection = Mock()
        mock_result = Mock()
        mock_result.inserted_ids = ["id1", "id2"]
        mock_collection.insert_many.return_value = mock_result
        mock_collection.delete_many.return_value = Mock()
        
        mock_db = Mock()
        mock_db.__getitem__.return_value = mock_collection
        
        self.db_manager.db = mock_db
        
        organizations = [
            {"name": "Org1", "root": "https://org1.org", "jobs": "https://org1.org/jobs"},
            {"name": "Org2", "root": "https://org2.org", "jobs": "https://org2.org/jobs"}
        ]
        
        result = self.db_manager.populate_database(organizations)
        
        assert result is True
        mock_collection.delete_many.assert_called_once()
        mock_collection.insert_many.assert_called_once_with(organizations, ordered=False)
    
    def test_populate_database_empty(self):
        """Test populating database with empty data"""
        result = self.db_manager.populate_database([])
        
        assert result is False
    
    @patch('anajobs.database.NonProfitJobSiteDB.connect')
    def test_search_organizations(self, mock_connect):
        """Test searching organizations"""
        # Mock database and collection
        mock_collection = Mock()
        mock_results = [
            {"name": "Environmental Org", "root": "https://env.org", "jobs": "https://env.org/jobs"}
        ]
        mock_collection.find.return_value.limit.return_value = mock_results
        
        mock_db = Mock()
        mock_db.__getitem__.return_value = mock_collection
        
        self.db_manager.db = mock_db
        
        result = self.db_manager.search_organizations("environmental", 5)
        
        assert len(result) == 1
        assert result[0]["name"] == "Environmental Org"
        mock_collection.find.assert_called_once_with({
            "name": {"$regex": "environmental", "$options": "i"}
        })
    
    @patch('anajobs.database.NonProfitJobSiteDB.connect')
    def test_get_organizations_by_domain(self, mock_connect):
        """Test getting organizations by domain"""
        # Mock database and collection
        mock_collection = Mock()
        mock_results = [
            {"name": "Org1", "root": "https://org1.org", "jobs": "https://org1.org/jobs"}
        ]
        mock_collection.find.return_value = mock_results
        
        mock_db = Mock()
        mock_db.__getitem__.return_value = mock_collection
        
        self.db_manager.db = mock_db
        
        result = self.db_manager.get_organizations_by_domain(".org")
        
        assert len(result) == 1
        mock_collection.find.assert_called_once_with({
            "root": {"$regex": ".org", "$options": "i"}
        })
    
    def test_close_connection(self):
        """Test closing database connection"""
        mock_client = Mock()
        self.db_manager.client = mock_client
        
        self.db_manager.close_connection()
        
        mock_client.close.assert_called_once()


class TestDatabaseIntegration:
    """Integration tests that require a running MongoDB instance"""
    
    @pytest.mark.integration
    def test_full_workflow(self):
        """Test complete workflow with real MongoDB (if available)"""
        # This test requires a running MongoDB instance
        # Skip if MongoDB is not available
        db_manager = NonProfitJobSiteDB("mongodb://localhost:27017/", "test_integration")
        
        try:
            if not db_manager.connect():
                pytest.skip("MongoDB not available for integration testing")
            
            # Setup collection
            assert db_manager.setup_collection() is True
            
            # Test with sample data
            organizations = [
                {
                    "name": "Test Org 1",
                    "root": "https://test1.org",
                    "jobs": "https://test1.org/jobs",
                    "status": "active",
                    "scraped": False
                }
            ]
            
            # Populate database
            assert db_manager.populate_database(organizations) is True
            
            # Test database
            results = db_manager.test_database("Test Org 1")
            assert results["connection_test"] is True
            assert results["count_test"] >= 1
            
            # Search organizations
            search_results = db_manager.search_organizations("Test", 5)
            assert len(search_results) >= 1
            
        finally:
            # Cleanup
            if db_manager.db:
                db_manager.db["organizations"].drop()
            db_manager.close_connection()


if __name__ == "__main__":
    pytest.main([__file__])