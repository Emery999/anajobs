#!/usr/bin/env python3
"""
Job Titles Updater for MongoDB Organizations Collection

This script goes through every entry in the 'organizations' collection, scrapes job titles
from their career pages, and updates the MongoDB record with a 'job_titles' field.

- If job titles are found: job_titles = ["Title 1", "Title 2", ...]
- If no titles or scraping fails: job_titles = null
"""

import json
import requests
import time
import re
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, NavigableString
from typing import Dict, List, Optional
import logging
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JobTitlesUpdater:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # MongoDB connection
        self.uri = "mongodb+srv://seeotter_db_user:n8tfO3zzASvoxllr@cluster0.hxabnjn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.db_name = "social_impact_jobs"
        self.collection_name = "organizations"
        self.client = None
        self.collection = None

    def connect_to_mongodb(self):
        """Connect to MongoDB and get organizations collection"""
        try:
            self.client = MongoClient(self.uri, server_api=ServerApi('1'))
            self.client.admin.command('ping')
            db = self.client[self.db_name]
            self.collection = db[self.collection_name]
            logger.info("✅ Connected to MongoDB Atlas")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False

    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔐 MongoDB connection closed")

    def extract_job_titles(self, url: str) -> Optional[List[str]]:
        """Extract job titles from a career page"""
        try:
            logger.info(f"📄 Fetching job titles from: {url}")
            
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            
            job_titles = []
            
            # Strategy 1: Look for job title patterns in links and headings
            job_titles.extend(self.find_titles_in_links_and_headings(soup))
            
            # Strategy 2: Look for job listing containers
            job_titles.extend(self.find_titles_in_job_containers(soup))
            
            # Strategy 3: Text-based extraction using regex patterns
            job_titles.extend(self.find_titles_with_regex(soup.get_text()))
            
            # Strategy 4: Try to follow deeper job listing links
            if not job_titles:
                deeper_titles = self.explore_deeper_job_links(soup, url)
                job_titles.extend(deeper_titles)
            
            # Clean and deduplicate
            clean_titles = self.clean_and_filter_titles(job_titles)
            
            logger.info(f"✅ Extracted {len(clean_titles)} job titles from {url}")
            return clean_titles if clean_titles else None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error extracting titles from {url}: {e}")
            return None

    def find_titles_in_links_and_headings(self, soup: BeautifulSoup) -> List[str]:
        """Find job titles in links and headings"""
        titles = []
        
        # Look for job-related links
        job_link_selectors = [
            'a[href*="job"]',
            'a[href*="position"]',
            'a[href*="opening"]',
            'a[href*="career"]',
            'a[class*="job"]',
            'a[class*="position"]'
        ]
        
        for selector in job_link_selectors:
            links = soup.select(selector)
            for link in links:
                title = self.extract_title_from_element(link)
                if title:
                    titles.append(title)
        
        # Look in headings (h1, h2, h3, h4)
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
        for heading in headings:
            title = self.extract_title_from_element(heading)
            if title and self.looks_like_job_title(title):
                titles.append(title)
        
        return titles

    def find_titles_in_job_containers(self, soup: BeautifulSoup) -> List[str]:
        """Find job titles in structured job listing containers"""
        titles = []
        
        # Common job container selectors
        container_selectors = [
            'div[class*="job"]',
            'div[class*="position"]',
            'div[class*="opening"]',
            'div[class*="career"]',
            'li[class*="job"]',
            'tr[class*="job"]',
            '.job-listing',
            '.position-listing',
            '.career-listing'
        ]
        
        for selector in container_selectors:
            containers = soup.select(selector)
            for container in containers[:20]:  # Limit to prevent overload
                # Look for title within container
                title_elements = container.select('h1, h2, h3, h4, h5, .title, .job-title, .position-title')
                for element in title_elements:
                    title = self.extract_title_from_element(element)
                    if title:
                        titles.append(title)
                
                # Also check direct text of container if it's small
                if len(container.get_text(strip=True)) < 200:
                    title = self.extract_title_from_element(container)
                    if title and self.looks_like_job_title(title):
                        titles.append(title)
        
        return titles

    def find_titles_with_regex(self, text: str) -> List[str]:
        """Find job titles using regex patterns"""
        titles = []
        
        # Common job title patterns
        patterns = [
            # Standard job titles
            r'(?i)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Engineer|Manager|Director|Analyst|Specialist|Coordinator|Associate|Assistant|Lead|Senior|Junior|Intern)))\b',
            
            # Role-specific patterns
            r'(?i)\b((?:Senior|Junior|Lead|Principal|Staff|Sr\.?|Jr\.?)\s+[A-Za-z\s]+(?:Engineer|Developer|Manager|Analyst|Designer|Coordinator|Specialist))\b',
            
            # Department + role patterns
            r'(?i)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Manager|Director|Lead|Head|Coordinator|Specialist))\b',
            
            # Common specific titles
            r'(?i)\b(Software\s+(?:Engineer|Developer|Architect)|Data\s+(?:Scientist|Analyst|Engineer)|Product\s+Manager|Project\s+Manager|Program\s+Manager|Marketing\s+Manager|Sales\s+Manager|HR\s+Manager|Finance\s+Manager|Operations\s+Manager)\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, str) and self.looks_like_job_title(match):
                    titles.append(match.strip())
        
        return titles

    def explore_deeper_job_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Try to follow deeper job listing links if no titles found on main page"""
        titles = []
        
        # Look for "View Jobs", "See Openings", "Job Listings" type links
        deeper_link_patterns = [
            r'(?i)view.*job',
            r'(?i)see.*opening',
            r'(?i)job.*listing',
            r'(?i)all.*position',
            r'(?i)current.*opening',
            r'(?i)available.*position'
        ]
        
        links = soup.find_all('a', href=True)
        candidate_links = []
        
        for link in links:
            link_text = link.get_text(strip=True)
            href = link.get('href', '')
            
            for pattern in deeper_link_patterns:
                if re.search(pattern, link_text) or re.search(pattern, href):
                    full_url = urljoin(base_url, href)
                    candidate_links.append(full_url)
                    break
        
        # Try up to 2 deeper links to avoid infinite loops
        for deeper_url in candidate_links[:2]:
            try:
                logger.info(f"🔍 Exploring deeper link: {deeper_url}")
                time.sleep(1)  # Rate limiting
                
                deeper_response = self.session.get(deeper_url, timeout=10)
                deeper_response.raise_for_status()
                
                deeper_soup = BeautifulSoup(deeper_response.content, 'html.parser')
                
                # Extract titles from deeper page
                deeper_titles = []
                deeper_titles.extend(self.find_titles_in_links_and_headings(deeper_soup))
                deeper_titles.extend(self.find_titles_in_job_containers(deeper_soup))
                
                titles.extend(deeper_titles)
                
                if deeper_titles:
                    logger.info(f"✅ Found {len(deeper_titles)} titles from deeper link")
                    break  # Found titles, no need to check more links
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to explore deeper link {deeper_url}: {e}")
                continue
        
        return titles

    def extract_title_from_element(self, element) -> Optional[str]:
        """Extract clean title text from a BeautifulSoup element"""
        if not element:
            return None
        
        # Get text content
        if hasattr(element, 'get_text'):
            text = element.get_text(strip=True)
        else:
            text = str(element).strip()
        
        # Clean up the text
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()
        
        # Filter out non-title content
        if not text or len(text) < 3 or len(text) > 100:
            return None
        
        # Remove common non-title phrases
        exclude_phrases = [
            'apply now', 'learn more', 'view details', 'see more', 'read more',
            'click here', 'full time', 'part time', 'remote', 'on site',
            'job description', 'requirements', 'qualifications', 'apply',
            'careers', 'jobs', 'openings', 'positions'
        ]
        
        text_lower = text.lower()
        for phrase in exclude_phrases:
            if phrase in text_lower and len(text_lower) < 30:
                return None
        
        return text

    def looks_like_job_title(self, text: str) -> bool:
        """Check if text looks like a job title"""
        if not text or len(text) < 3 or len(text) > 80:
            return False
        
        text_lower = text.lower()
        
        # Positive indicators
        job_indicators = [
            'engineer', 'manager', 'director', 'analyst', 'specialist', 'coordinator',
            'associate', 'assistant', 'lead', 'senior', 'junior', 'intern', 'developer',
            'designer', 'consultant', 'advisor', 'officer', 'representative', 'supervisor',
            'administrator', 'technician', 'scientist', 'researcher', 'programmer'
        ]
        
        has_job_indicator = any(indicator in text_lower for indicator in job_indicators)
        
        # Negative indicators (common false positives)
        negative_indicators = [
            'http', 'www', '.com', '.org', 'click', 'apply now', 'learn more',
            'view all', 'see all', 'show more', 'load more', 'next page',
            'previous', 'back to', 'home', 'contact', 'about'
        ]
        
        has_negative = any(neg in text_lower for neg in negative_indicators)
        
        # Basic structure check (title case or reasonable word count)
        word_count = len(text.split())
        reasonable_length = 1 <= word_count <= 8
        
        return has_job_indicator and not has_negative and reasonable_length

    def clean_and_filter_titles(self, titles: List[str]) -> List[str]:
        """Clean and deduplicate job titles"""
        clean_titles = []
        seen_titles = set()
        
        for title in titles:
            if not title:
                continue
            
            # Additional cleaning
            clean_title = re.sub(r'^\W+|\W+$', '', title)  # Remove leading/trailing non-word chars
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()  # Normalize spaces
            
            # Skip if empty after cleaning
            if not clean_title or len(clean_title) < 3:
                continue
            
            # Skip duplicates (case insensitive)
            title_lower = clean_title.lower()
            if title_lower in seen_titles:
                continue
            
            # Final validation
            if self.looks_like_job_title(clean_title):
                clean_titles.append(clean_title)
                seen_titles.add(title_lower)
        
        return clean_titles

    def update_organization_job_titles(self, org_id: str, job_titles: Optional[List[str]]):
        """Update MongoDB document with job_titles field"""
        try:
            result = self.collection.update_one(
                {"_id": org_id},
                {
                    "$set": {
                        "job_titles": job_titles,
                        "job_titles_updated_at": datetime.utcnow().isoformat()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated organization {org_id} with job_titles")
                return True
            else:
                logger.warning(f"⚠️ No changes made to organization {org_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update organization {org_id}: {e}")
            return False

    def process_all_organizations(self, limit: Optional[int] = None, test_mode: bool = False):
        """Process all organizations in the collection"""
        
        if not self.connect_to_mongodb():
            return False
        
        try:
            # Get total count
            total_count = self.collection.count_documents({})
            logger.info(f"📊 Total organizations in collection: {total_count}")
            
            if limit:
                logger.info(f"🔢 Processing limit: {limit} organizations")
            
            if test_mode:
                logger.info("🧪 Running in TEST MODE - no database updates")
            
            # Query organizations
            query = {}
            cursor = self.collection.find(query)
            if limit:
                cursor = cursor.limit(limit)
            
            organizations = list(cursor)
            logger.info(f"📋 Retrieved {len(organizations)} organizations to process")
            
            # Process each organization
            processed = 0
            successful = 0
            with_titles = 0
            without_titles = 0
            
            for i, org in enumerate(organizations, 1):
                org_name = org.get('name', 'Unknown')
                org_id = org.get('_id')
                jobs_url = org.get('jobs', '')
                
                logger.info(f"\n🏢 Processing {i}/{len(organizations)}: {org_name}")
                logger.info(f"🔗 Jobs URL: {jobs_url}")
                
                if not jobs_url:
                    logger.warning(f"⚠️ No jobs URL for {org_name}")
                    if not test_mode:
                        self.update_organization_job_titles(org_id, None)
                    without_titles += 1
                    processed += 1
                    continue
                
                # Extract job titles
                job_titles = self.extract_job_titles(jobs_url)
                
                if job_titles:
                    logger.info(f"✅ Found {len(job_titles)} job titles:")
                    for title in job_titles[:5]:  # Show first 5
                        logger.info(f"   • {title}")
                    if len(job_titles) > 5:
                        logger.info(f"   ... and {len(job_titles) - 5} more")
                    with_titles += 1
                else:
                    logger.info(f"❌ No job titles found for {org_name}")
                    without_titles += 1
                
                # Update database
                if not test_mode:
                    if self.update_organization_job_titles(org_id, job_titles):
                        successful += 1
                else:
                    successful += 1  # In test mode, assume success
                
                processed += 1
                
                # Rate limiting
                time.sleep(2)
                
                # Progress update every 10 organizations
                if i % 10 == 0:
                    logger.info(f"📊 Progress: {i}/{len(organizations)} organizations processed")
            
            # Final statistics
            logger.info(f"\n🎉 Processing Complete!")
            logger.info(f"📊 Statistics:")
            logger.info(f"   Total processed: {processed}")
            logger.info(f"   Database updates: {successful}")
            logger.info(f"   With job titles: {with_titles}")
            logger.info(f"   Without job titles: {without_titles}")
            logger.info(f"   Success rate: {(with_titles/processed)*100:.1f}% found titles")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during processing: {e}")
            return False
        finally:
            self.close_connection()


def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(
        description="Update MongoDB organizations with job titles from career pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all organizations
  python job_titles_updater.py
  
  # Process only first 10 organizations
  python job_titles_updater.py --limit 10
  
  # Test mode (no database updates)
  python job_titles_updater.py --test --limit 5
        """
    )
    
    parser.add_argument('--limit', type=int, 
                       help='Limit number of organizations to process (for testing)')
    
    parser.add_argument('--test', action='store_true',
                       help='Test mode - extract titles but do not update database')
    
    args = parser.parse_args()
    
    print("🚀 Job Titles Updater for Organizations Collection")
    print("=" * 60)
    print("📋 This script will:")
    print("   1. Connect to MongoDB organizations collection")
    print("   2. For each organization, scrape job titles from career page")
    print("   3. Update MongoDB record with job_titles field")
    print("   4. Set job_titles = null if no titles found")
    print("=" * 60)
    
    if args.test:
        print("🧪 RUNNING IN TEST MODE - No database updates will be made")
    
    if args.limit:
        print(f"🔢 Processing limit: {args.limit} organizations")
    else:
        print("🔄 Processing ALL organizations in collection")
    
    # Confirmation for production runs
    if not args.test and not args.limit:
        confirm = input("\n❓ Process ALL organizations? This may take a long time. Type 'YES' to continue: ")
        if confirm != 'YES':
            print("❌ Operation cancelled")
            return 1
    
    # Initialize and run updater
    updater = JobTitlesUpdater()
    
    try:
        success = updater.process_all_organizations(
            limit=args.limit,
            test_mode=args.test
        )
        
        if success:
            print(f"\n✅ Job titles update process completed!")
            if not args.test:
                print(f"💾 MongoDB organizations collection has been updated")
                print(f"🔍 Each record now has a 'job_titles' field:")
                print(f"   • List of strings if titles found")
                print(f"   • null if no titles found")
            return 0
        else:
            print(f"\n❌ Job titles update process failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n❌ Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())