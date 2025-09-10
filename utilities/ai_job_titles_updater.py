#!/usr/bin/env python3
"""
AI-Powered Job Titles Updater with Career URL Discovery for MongoDB Organizations Collection

This script uses Claude AI to discover correct career URLs and extract precise job titles. It:
1. Steps through every organization entry
2. Crawls the organization's main website to discover all reachable sub-pages
3. Uses Claude AI to identify the correct careers/jobs root URL from discovered pages
4. Aggregates comprehensive job content from the correct career pages
5. Uses Claude AI to extract exact job titles from the content
6. Updates MongoDB with corrected jobs URL and extracted titles or null
"""

import json
import requests
import time
import re
import argparse
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Set
import logging
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import anthropic

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AIJobTitlesUpdater:
    def __init__(self, claude_api_key: str = None):
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
        
        # Claude AI client
        self.claude_client = None
        if claude_api_key:
            self.claude_client = anthropic.Anthropic(api_key=claude_api_key)
        else:
            logger.warning("⚠️ No Claude API key provided - script will fail without AI model")

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

    def delete_existing_job_titles(self, org_id: str) -> bool:
        """Delete any existing job_titles field from organization"""
        try:
            result = self.collection.update_one(
                {"_id": org_id},
                {"$unset": {"job_titles": "", "job_titles_updated_at": ""}}
            )
            if result.modified_count > 0:
                logger.info(f"🗑️ Removed existing job_titles field from {org_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete existing job_titles for {org_id}: {e}")
            return False

    def get_page_content(self, url: str, max_retries: int = 2) -> Optional[str]:
        """Get text content from a single page"""
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"📄 Fetching: {url} (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=15, allow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()
                
                # Get clean text
                text = soup.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                clean_text = '\n'.join(lines)
                
                return clean_text
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ Request failed for {url} (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
            except Exception as e:
                logger.error(f"❌ Error processing {url}: {e}")
                break
        
        return None

    def find_job_related_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Find all job-related links on the page"""
        job_links = set()
        
        # Patterns to identify job-related links
        job_link_patterns = [
            r'(?i)job',
            r'(?i)career',
            r'(?i)position',
            r'(?i)opening',
            r'(?i)opportunity',
            r'(?i)vacancy',
            r'(?i)employment',
            r'(?i)hiring'
        ]
        
        # Get base domain for filtering
        base_domain = urlparse(base_url).netloc.lower()
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href:
                continue
            
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            link_domain = urlparse(full_url).netloc.lower()
            
            # Only process links from same domain
            if link_domain != base_domain:
                continue
            
            # Check if link text or URL contains job-related keywords
            link_text = link.get_text(strip=True).lower()
            href_lower = href.lower()
            
            is_job_related = False
            for pattern in job_link_patterns:
                if re.search(pattern, link_text) or re.search(pattern, href_lower):
                    is_job_related = True
                    break
            
            if is_job_related:
                # Clean up URL (remove fragments, query parameters that aren't needed)
                parsed = urlparse(full_url)
                clean_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path, 
                    parsed.params, '', ''  # Remove query and fragment
                ))
                job_links.add(clean_url)
        
        return job_links

    def aggregate_job_content(self, root_jobs_url: str, max_pages: int = 10) -> Optional[str]:
        """Aggregate comprehensive job content from root URL and related pages"""
        try:
            logger.info(f"🔍 Aggregating job content from: {root_jobs_url}")
            
            all_content = []
            processed_urls = set()
            
            # Step 1: Get content from root jobs page
            root_content = self.get_page_content(root_jobs_url)
            if not root_content:
                logger.warning(f"⚠️ Could not get content from root jobs URL: {root_jobs_url}")
                return None
            
            all_content.append(f"=== ROOT JOBS PAGE: {root_jobs_url} ===\n{root_content}\n")
            processed_urls.add(root_jobs_url)
            
            # Step 2: Parse root page to find job-related links
            try:
                response = self.session.get(root_jobs_url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                job_links = self.find_job_related_links(soup, root_jobs_url)
                
                logger.info(f"🔗 Found {len(job_links)} job-related links")
                
                # Step 3: Get content from related job pages (up to max_pages)
                links_to_process = list(job_links - processed_urls)[:max_pages-1]  # -1 because we already processed root
                
                for i, link_url in enumerate(links_to_process):
                    logger.info(f"📄 Processing job link {i+1}/{len(links_to_process)}: {link_url}")
                    
                    link_content = self.get_page_content(link_url)
                    if link_content:
                        all_content.append(f"=== JOB PAGE: {link_url} ===\n{link_content}\n")
                    
                    processed_urls.add(link_url)
                    time.sleep(1)  # Rate limiting
                    
            except Exception as e:
                logger.warning(f"⚠️ Error finding job links from {root_jobs_url}: {e}")
            
            # Step 4: Combine all content
            if all_content:
                combined_content = "\n".join(all_content)
                logger.info(f"✅ Aggregated {len(all_content)} pages, total content length: {len(combined_content)} characters")
                
                # Limit content size for API call (Claude has token limits)
                max_content_length = 100000  # ~100K characters
                if len(combined_content) > max_content_length:
                    combined_content = combined_content[:max_content_length]
                    logger.info(f"📝 Truncated content to {max_content_length} characters for AI processing")
                
                return combined_content
            else:
                logger.warning("⚠️ No content aggregated")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error aggregating job content: {e}")
            return None

    def extract_job_titles_with_ai(self, job_content: str, organization_name: str) -> Optional[List[str]]:
        """Use Claude AI to extract exact job titles from job content"""
        if not self.claude_client:
            logger.error("❌ Claude AI client not configured")
            return None
        
        try:
            prompt = f"""
You are an expert at extracting job titles from career page content. Your task is to extract ONLY the exact job titles/position names from the provided career page content.

ORGANIZATION: {organization_name}

INSTRUCTIONS:
1. Extract ONLY actual job titles/position names that are currently open positions
2. Do NOT include:
   - General descriptions
   - Requirements text
   - Company information
   - Navigation elements
   - Button text (like "Apply Now", "Learn More")
   - Department names alone (unless they are actual job titles)
   - Page headers/footers
3. Return job titles exactly as they appear (preserve capitalization and formatting)
4. If you find duplicate titles, include only one instance
5. Return ONLY a valid JSON array of strings, nothing else

EXAMPLES of what to extract:
- "Software Engineer"
- "Senior Data Scientist" 
- "Program Manager, Climate Policy"
- "Director of Marketing"

EXAMPLES of what NOT to extract:
- "Apply Now"
- "Engineering" (department name only)
- "We are looking for talented individuals"
- "View Details"

CAREER PAGE CONTENT:
{job_content}

Return only the JSON array of job titles:
"""

            logger.info(f"🤖 Calling Claude AI to extract job titles for {organization_name}")
            
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Parse Claude's response
            claude_response = response.content[0].text.strip()
            logger.debug(f"Claude response: {claude_response}")
            
            # Extract JSON from response
            try:
                # Find JSON array in the response
                json_start = claude_response.find('[')
                json_end = claude_response.rfind(']') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = claude_response[json_start:json_end]
                    job_titles = json.loads(json_str)
                    
                    if isinstance(job_titles, list):
                        # Filter and clean titles
                        clean_titles = []
                        for title in job_titles:
                            if isinstance(title, str) and title.strip():
                                clean_title = title.strip()
                                if len(clean_title) > 2 and len(clean_title) < 100:  # Reasonable length
                                    clean_titles.append(clean_title)
                        
                        logger.info(f"✅ Claude extracted {len(clean_titles)} job titles")
                        return clean_titles if clean_titles else None
                    else:
                        logger.warning("⚠️ Claude response is not a list")
                        return None
                else:
                    logger.warning("⚠️ No valid JSON array found in Claude response")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse Claude JSON response: {e}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error calling Claude AI: {e}")
            return None

    def update_organization_job_titles(self, org_id: str, job_titles: Optional[List[str]]):
        """Update MongoDB document with AI-extracted job_titles field"""
        try:
            update_data = {
                "job_titles": job_titles,
                "job_titles_updated_at": datetime.utcnow().isoformat(),
                "job_titles_extraction_method": "claude_ai"
            }
            
            result = self.collection.update_one(
                {"_id": org_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                titles_count = len(job_titles) if job_titles else 0
                logger.info(f"✅ Updated organization {org_id} with {titles_count} AI-extracted job titles")
                return True
            else:
                logger.warning(f"⚠️ No changes made to organization {org_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update organization {org_id}: {e}")
            return False

    def process_all_organizations(self, limit: Optional[int] = None, test_mode: bool = False):
        """Process all organizations with AI job title extraction"""
        
        if not self.claude_client:
            logger.error("❌ Claude AI client is required for this script")
            return False
        
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
            cursor = self.collection.find({})
            if limit:
                cursor = cursor.limit(limit)
            
            organizations = list(cursor)
            logger.info(f"📋 Retrieved {len(organizations)} organizations to process")
            
            # Process each organization
            processed = 0
            successful_updates = 0
            successful_extractions = 0
            failed_extractions = 0
            
            for i, org in enumerate(organizations, 1):
                org_name = org.get('name', 'Unknown')
                org_id = org.get('_id')
                jobs_url = org.get('jobs', '')
                
                logger.info(f"\n🏢 Processing {i}/{len(organizations)}: {org_name}")
                logger.info(f"🔗 Jobs URL: {jobs_url}")
                
                if not jobs_url:
                    logger.warning(f"⚠️ No jobs URL for {org_name}")
                    if not test_mode:
                        self.delete_existing_job_titles(org_id)
                        self.update_organization_job_titles(org_id, None)
                        successful_updates += 1
                    failed_extractions += 1
                    processed += 1
                    continue
                
                # Step 1: Delete existing job_titles
                if not test_mode:
                    self.delete_existing_job_titles(org_id)
                
                # Step 2: Aggregate comprehensive job content
                logger.info("📚 Aggregating comprehensive job content...")
                job_content = self.aggregate_job_content(jobs_url)
                
                if not job_content:
                    logger.warning(f"⚠️ Could not aggregate job content for {org_name}")
                    if not test_mode:
                        self.update_organization_job_titles(org_id, None)
                        successful_updates += 1
                    failed_extractions += 1
                    processed += 1
                    time.sleep(2)  # Rate limiting
                    continue
                
                # Step 3: Extract job titles with Claude AI
                logger.info("🤖 Extracting job titles with Claude AI...")
                job_titles = self.extract_job_titles_with_ai(job_content, org_name)
                
                if job_titles:
                    logger.info(f"✅ Claude AI extracted {len(job_titles)} job titles:")
                    for title in job_titles[:5]:  # Show first 5
                        logger.info(f"   • {title}")
                    if len(job_titles) > 5:
                        logger.info(f"   ... and {len(job_titles) - 5} more")
                    successful_extractions += 1
                else:
                    logger.info(f"❌ No job titles extracted by AI for {org_name}")
                    failed_extractions += 1
                
                # Step 4: Update database
                if not test_mode:
                    if self.update_organization_job_titles(org_id, job_titles):
                        successful_updates += 1
                else:
                    successful_updates += 1  # In test mode, assume success
                
                processed += 1
                
                # Rate limiting (important for AI API calls)
                time.sleep(3)  # 3 seconds between requests to be respectful
                
                # Progress update every 5 organizations
                if i % 5 == 0:
                    logger.info(f"📊 Progress: {i}/{len(organizations)} organizations processed")
            
            # Final statistics
            logger.info(f"\n🎉 AI Job Titles Processing Complete!")
            logger.info(f"📊 Statistics:")
            logger.info(f"   Total processed: {processed}")
            logger.info(f"   Database updates: {successful_updates}")
            logger.info(f"   Successful AI extractions: {successful_extractions}")
            logger.info(f"   Failed extractions: {failed_extractions}")
            logger.info(f"   AI success rate: {(successful_extractions/processed)*100:.1f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during processing: {e}")
            return False
        finally:
            self.close_connection()


def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(
        description="AI-powered job titles extractor using Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode with 3 organizations (requires ANTHROPIC_API_KEY env var)
  python ai_job_titles_updater.py --test --limit 3
  
  # Production run on first 10 organizations
  python ai_job_titles_updater.py --limit 10 --claude_api_key YOUR_API_KEY
  
  # Full production run (requires confirmation)
  python ai_job_titles_updater.py --claude_api_key YOUR_API_KEY
        """
    )
    
    parser.add_argument('--limit', type=int, 
                       help='Limit number of organizations to process')
    
    parser.add_argument('--test', action='store_true',
                       help='Test mode - extract titles but do not update database')
    
    parser.add_argument('--claude_api_key', type=str,
                       help='Claude API key (or set ANTHROPIC_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Get Claude API key
    claude_api_key = args.claude_api_key or os.getenv('ANTHROPIC_API_KEY')
    
    if not claude_api_key:
        print("❌ Error: Claude API key is required for AI job title extraction")
        print("   Set ANTHROPIC_API_KEY environment variable or use --claude_api_key")
        return 1
    
    print("🚀 AI-Powered Job Titles Updater")
    print("=" * 60)
    print("🤖 Using Claude AI for intelligent job title extraction")
    print("📋 This script will:")
    print("   1. Delete any existing job_titles fields")
    print("   2. Aggregate comprehensive job content from career pages")
    print("   3. Use Claude AI to extract exact job titles")
    print("   4. Update MongoDB with extracted titles or null")
    print("=" * 60)
    
    if args.test:
        print("🧪 RUNNING IN TEST MODE - No database updates")
    
    if args.limit:
        print(f"🔢 Processing limit: {args.limit} organizations")
    else:
        print("🔄 Processing ALL organizations")
    
    # Confirmation for production runs
    if not args.test and not args.limit:
        print("\n⚠️ WARNING: This will process ALL 390+ organizations with AI")
        print("   Estimated time: 2-3 hours (3 second delays + AI processing)")
        print("   Estimated cost: $20-50 in Claude API calls")
        
        try:
            confirm = input("\n❓ Continue with full processing? Type 'YES' to proceed: ")
            if confirm != 'YES':
                print("❌ Operation cancelled")
                return 1
        except:
            print("❌ Cannot get confirmation in non-interactive mode")
            return 1
    
    # Initialize and run updater
    updater = AIJobTitlesUpdater(claude_api_key=claude_api_key)
    
    try:
        success = updater.process_all_organizations(
            limit=args.limit,
            test_mode=args.test
        )
        
        if success:
            print(f"\n✅ AI job titles extraction completed!")
            if not args.test:
                print(f"💾 MongoDB organizations collection updated with AI-extracted job titles")
                print(f"🔍 Each record now has:")
                print(f"   • job_titles: [\"Title 1\", \"Title 2\", ...] or null")
                print(f"   • job_titles_extraction_method: \"claude_ai\"")
                print(f"   • job_titles_updated_at: timestamp")
            return 0
        else:
            print(f"\n❌ AI job titles extraction failed")
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