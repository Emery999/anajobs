"""
Tests for extractor module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from anajobs.extractor import WebExtractor, extract_organization_text


class TestWebExtractor:
    """Test cases for WebExtractor class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = WebExtractor(max_pages=2, delay=0.1, timeout=5)
    
    def teardown_method(self):
        """Clean up after tests"""
        self.extractor.close()
    
    def test_init(self):
        """Test extractor initialization"""
        assert self.extractor.max_pages == 2
        assert self.extractor.delay == 0.1
        assert self.extractor.timeout == 5
        assert self.extractor.session is not None
    
    def test_check_robots_txt_allowed(self):
        """Test robots.txt check when crawling is allowed"""
        with patch('urllib.robotparser.RobotFileParser') as mock_rp_class:
            mock_rp = Mock()
            mock_rp.can_fetch.return_value = True
            mock_rp_class.return_value = mock_rp
            
            result = self.extractor._check_robots_txt("https://example.com/jobs")
            assert result is True
    
    def test_check_robots_txt_disallowed(self):
        """Test robots.txt check when crawling is disallowed"""
        with patch('urllib.robotparser.RobotFileParser') as mock_rp_class:
            mock_rp = Mock()
            mock_rp.can_fetch.return_value = False
            mock_rp_class.return_value = mock_rp
            
            result = self.extractor._check_robots_txt("https://example.com/jobs")
            assert result is False
    
    def test_check_robots_txt_exception(self):
        """Test robots.txt check when there's an exception"""
        with patch('urllib.robotparser.RobotFileParser') as mock_rp_class:
            mock_rp_class.side_effect = Exception("Connection error")
            
            # Should default to allowed when can't check
            result = self.extractor._check_robots_txt("https://example.com/jobs")
            assert result is True
    
    @patch('requests.Session.get')
    def test_extract_single_page_success(self, mock_get):
        """Test successful single page extraction"""
        # Mock successful response
        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <head><title>Jobs</title></head>
            <body>
                <h1>Career Opportunities</h1>
                <p>We are hiring for various positions.</p>
                <a href="/job1">Software Engineer</a>
                <a href="/job2">Data Scientist</a>
                <script>console.log('test');</script>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        text, links = self.extractor._extract_single_page("https://example.com/careers")
        
        assert "Career Opportunities" in text
        assert "hiring for various positions" in text
        assert "console.log" not in text  # Script should be removed
        assert len(links) >= 2  # Should find job-related links
    
    @patch('requests.Session.get')
    def test_extract_single_page_request_error(self, mock_get):
        """Test single page extraction with request error"""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        text, links = self.extractor._extract_single_page("https://example.com/careers")
        
        assert text == ""
        assert links == []
    
    def test_extract_job_related_links(self):
        """Test extraction of job-related links"""
        from bs4 import BeautifulSoup
        
        html = """
        <html>
            <body>
                <a href="/jobs">Jobs</a>
                <a href="/careers">Career Opportunities</a>
                <a href="/about">About Us</a>
                <a href="/employment">Employment</a>
                <a href="https://external.com/job">External Job</a>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'lxml')
        base_url = "https://example.com/careers"
        
        links = self.extractor._extract_job_related_links(soup, base_url)
        
        # Should find job-related links
        job_related_count = sum(1 for link in links if any(keyword in link.lower() 
                               for keyword in ['job', 'career', 'employment']))
        assert job_related_count >= 3
    
    def test_extract_organization_content_no_jobs_url(self):
        """Test extraction when no jobs URL is provided"""
        org_data = {
            'name': 'Test Org',
            'root': 'https://example.com',
            'jobs': ''
        }
        
        result = self.extractor.extract_organization_content(org_data)
        
        assert result['organization'] == 'Test Org'
        assert result['extraction_successful'] is False
        assert 'No jobs URL provided' in result['errors']
    
    @patch.object(WebExtractor, '_check_robots_txt')
    def test_extract_organization_content_robots_disallowed(self, mock_robots):
        """Test extraction when robots.txt disallows crawling"""
        mock_robots.return_value = False
        
        org_data = {
            'name': 'Test Org',
            'root': 'https://example.com',
            'jobs': 'https://example.com/jobs'
        }
        
        result = self.extractor.extract_organization_content(org_data)
        
        assert result['extraction_successful'] is False
        assert 'Robots.txt disallows crawling' in result['errors']


class TestConvenienceFunction:
    """Test the convenience function"""
    
    @patch('anajobs.extractor.WebExtractor')
    def test_extract_organization_text(self, mock_extractor_class):
        """Test the convenience function"""
        # Mock extractor instance
        mock_extractor = Mock()
        mock_result = {
            'organization': 'Test Org',
            'extraction_successful': True,
            'extracted_text': 'Sample text',
            'total_pages': 2
        }
        mock_extractor.extract_organization_content.return_value = mock_result
        mock_extractor_class.return_value = mock_extractor
        
        org_data = {
            'name': 'Test Org',
            'jobs': 'https://example.com/jobs'
        }
        
        result = extract_organization_text(org_data, max_pages=3, delay=0.5)
        
        # Check that extractor was initialized with correct parameters
        mock_extractor_class.assert_called_once_with(max_pages=3, delay=0.5)
        
        # Check that extraction was called
        mock_extractor.extract_organization_content.assert_called_once_with(org_data)
        
        # Check that close was called
        mock_extractor.close.assert_called_once()
        
        # Check result
        assert result == mock_result


class TestExtractorIntegration:
    """Integration tests for the extractor (require network access)"""
    
    @pytest.mark.integration
    def test_extract_from_example_site(self):
        """Test extraction from a real website (if accessible)"""
        # This test requires network access and should be marked as integration
        extractor = WebExtractor(max_pages=1, delay=1.0, timeout=10)
        
        try:
            org_data = {
                'name': 'Example Org',
                'root': 'https://httpbin.org',
                'jobs': 'https://httpbin.org/html'  # Returns sample HTML
            }
            
            result = extractor.extract_organization_content(org_data)
            
            # Should succeed (httpbin is reliable for testing)
            assert result['organization'] == 'Example Org'
            # May or may not succeed depending on network, robots.txt, etc.
            # Just check that we get a result structure
            assert 'extraction_successful' in result
            assert 'extracted_text' in result
            assert 'errors' in result
            
        except Exception as e:
            pytest.skip(f"Integration test skipped due to network issues: {e}")
        finally:
            extractor.close()


if __name__ == "__main__":
    pytest.main([__file__])