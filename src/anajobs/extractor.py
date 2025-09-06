#!/usr/bin/env python3
"""
Web Content Extraction Module for AnaJobs
Extracts text content from job pages and linked pages
"""

import re
import time
import logging
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebExtractor:
    """Extracts text content from job websites"""
    
    def __init__(self, max_pages: int = 10, delay: float = 1.0, timeout: int = 10):
        """
        Initialize web extractor
        
        Args:
            max_pages: Maximum number of pages to crawl per site
            delay: Delay between requests (seconds)
            timeout: Request timeout (seconds)
        """
        self.max_pages = max_pages
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AnaJobs/1.0; +https://github.com/Emery999/anajobs)'
        })
        
    def extract_organization_content(self, org_data: Dict[str, str]) -> Dict[str, str]:
        """
        Extract content from an organization's job pages
        
        Args:
            org_data: Dictionary with 'name', 'root', 'jobs' keys
            
        Returns:
            Dictionary with extracted content and metadata
        """
        result = {
            'organization': org_data.get('name', 'Unknown'),
            'root_url': org_data.get('root', ''),
            'jobs_url': org_data.get('jobs', ''),
            'extracted_text': '',
            'pages_crawled': [],
            'errors': [],
            'total_pages': 0,
            'extraction_successful': False
        }
        
        try:
            # Extract content from jobs page and linked pages
            jobs_url = org_data.get('jobs', '')
            if not jobs_url:
                result['errors'].append("No jobs URL provided")
                return result
                
            logger.info(f"Extracting content from {result['organization']}: {jobs_url}")
            
            # Check robots.txt
            if not self._check_robots_txt(jobs_url):
                result['errors'].append("Robots.txt disallows crawling")
                return result
            
            # Extract content from the main jobs page and linked pages
            all_text, crawled_pages, errors = self._extract_from_url_tree(jobs_url)
            
            result['extracted_text'] = all_text
            result['pages_crawled'] = crawled_pages
            result['errors'].extend(errors)
            result['total_pages'] = len(crawled_pages)
            result['extraction_successful'] = len(crawled_pages) > 0
            
            logger.info(f"Extraction complete for {result['organization']}: {result['total_pages']} pages crawled")
            
        except Exception as e:
            error_msg = f"Failed to extract content: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(f"Error extracting content for {result['organization']}: {error_msg}")
            
        return result
    
    def _extract_from_url_tree(self, start_url: str) -> tuple[str, List[str], List[str]]:
        """
        Extract text from a URL and linked pages within the same domain
        
        Args:
            start_url: Starting URL to crawl from
            
        Returns:
            Tuple of (combined_text, crawled_urls, errors)
        """
        visited_urls: Set[str] = set()
        crawled_urls: List[str] = []
        all_text_parts: List[str] = []
        errors: List[str] = []
        
        base_domain = urlparse(start_url).netloc
        urls_to_visit = [start_url]
        
        while urls_to_visit and len(visited_urls) < self.max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in visited_urls:
                continue
                
            try:
                # Add delay between requests
                if visited_urls:  # Skip delay for first request
                    time.sleep(self.delay)
                
                # Extract content from current page
                text_content, linked_urls = self._extract_single_page(current_url)
                
                if text_content:
                    all_text_parts.append(f"\n=== Content from {current_url} ===\n{text_content}\n")
                    visited_urls.add(current_url)
                    crawled_urls.append(current_url)
                    
                    # Add new URLs from same domain to visit queue
                    for url in linked_urls:
                        parsed_url = urlparse(url)
                        if (parsed_url.netloc == base_domain and 
                            url not in visited_urls and 
                            url not in urls_to_visit):
                            urls_to_visit.append(url)
                else:
                    errors.append(f"No content extracted from {current_url}")
                    
            except Exception as e:
                error_msg = f"Error processing {current_url}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue
        
        combined_text = '\n'.join(all_text_parts)
        return combined_text, crawled_urls, errors
    
    def _extract_single_page(self, url: str) -> tuple[str, List[str]]:
        """
        Extract text content and links from a single page
        
        Args:
            url: URL to extract content from
            
        Returns:
            Tuple of (text_content, linked_urls)
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # Extract text content
            text_content = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_content = ' '.join(chunk for chunk in chunks if chunk)
            
            # Extract links that might be job-related
            linked_urls = self._extract_job_related_links(soup, url)
            
            logger.debug(f"Extracted {len(text_content)} characters from {url}")
            return text_content, linked_urls
            
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return "", []
        except Exception as e:
            logger.warning(f"Error extracting content from {url}: {e}")
            return "", []
    
    def _extract_job_related_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract links that are likely job-related from the page
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
            
        Returns:
            List of job-related URLs
        """
        job_keywords = [
            'job', 'career', 'employment', 'position', 'opening', 'opportunity',
            'hiring', 'vacancy', 'work', 'apply', 'application'
        ]
        
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            
            # Check if link or text contains job-related keywords
            if any(keyword in href or keyword in text for keyword in job_keywords):
                absolute_url = urljoin(base_url, link['href'])
                # Clean the URL
                parsed = urlparse(absolute_url)
                clean_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path, 
                    parsed.params, parsed.query, ''  # Remove fragment
                ))
                links.append(clean_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        return unique_links[:20]  # Limit to prevent too many links
    
    def _check_robots_txt(self, url: str) -> bool:
        """
        Check if URL is allowed by robots.txt
        
        Args:
            url: URL to check
            
        Returns:
            True if allowed, False if disallowed
        """
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            user_agent = self.session.headers.get('User-Agent', '*')
            return rp.can_fetch(user_agent, url)
            
        except Exception as e:
            logger.debug(f"Could not check robots.txt for {url}: {e}")
            return True  # If can't check, assume allowed
    
    def close(self):
        """Close the session"""
        self.session.close()


def extract_organization_text(org_data: Dict[str, str], 
                            max_pages: int = 5, 
                            delay: float = 1.0) -> Dict[str, str]:
    """
    Convenience function to extract text from an organization's job pages
    
    Args:
        org_data: Dictionary with organization info
        max_pages: Maximum pages to crawl
        delay: Delay between requests
        
    Returns:
        Dictionary with extracted content
    """
    extractor = WebExtractor(max_pages=max_pages, delay=delay)
    try:
        return extractor.extract_organization_content(org_data)
    finally:
        extractor.close()