#!/usr/bin/env python3
"""
AI-Powered Job Titles Updater with Main Page Career URL Discovery for MongoDB Organizations Collection

This script uses Claude AI to discover correct career URLs from main page links and extract precise job titles. It:
1. Steps through every organization entry
2. Examines all sub-page links from the organization's main/root page
3. Uses Claude AI to identify the most likely careers/jobs URL from main page links
4. If careers URL found: aggregates job content and extracts job titles with AI
5. If no careers URL found: sets jobs and job_titles to null
6. Updates MongoDB with corrected jobs URL and extracted titles (or nulls)
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


class AIJobTitlesUpdaterV2:
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

    def discover_main_page_links(self, main_url: str) -> Set[str]:
        """Discover all sub-page links from the main/root page"""
        try:
            logger.info(f"🔍 Examining main page links: {main_url}")
            
            response = self.session.get(main_url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            base_domain = urlparse(main_url).netloc.lower()
            discovered_links = set()
            
            # Find all internal links on the main page
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').strip()
                if not href:
                    continue
                
                # Convert relative URLs to absolute
                full_url = urljoin(main_url, href)
                link_domain = urlparse(full_url).netloc.lower()
                
                # Only process links from same domain
                if link_domain != base_domain:
                    continue
                
                # Clean up URL
                parsed = urlparse(full_url)
                clean_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path.rstrip('/'),
                    '', '', ''  # Remove params, query, fragment
                ))
                
                # Skip common non-content URLs
                if not any(skip in clean_url.lower() for skip in 
                         ['javascript:', 'mailto:', '#', '.pdf', '.jpg', '.png', '.gif', 
                          'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com']):
                    discovered_links.add(clean_url)
            
            logger.info(f"✅ Discovered {len(discovered_links)} links from main page")
            return discovered_links
            
        except Exception as e:
            logger.error(f"❌ Error discovering main page links: {e}")
            return set()
    
    def identify_careers_url_from_main_page(self, main_page_links: Set[str], organization_name: str) -> Optional[str]:
        """Use Claude AI to identify the careers URL from main page links"""
        if not self.claude_client:
            logger.error("❌ Claude AI client not configured")
            return None
        
        if not main_page_links:
            logger.warning("⚠️ No links found on main page")
            return None
        
        try:
            # Create list of URLs for AI analysis
            url_list = list(main_page_links)[:50]  # Limit to 50 URLs to avoid token limits
            urls_text = "\n".join([f"- {url}" for url in url_list])
            
            prompt = f"""
You are an expert at identifying career/job pages from website navigation links.

ORGANIZATION: {organization_name}

TASK: From the following list of URLs found on this organization's main page, identify the SINGLE URL that is most likely to be the careers/jobs page where job openings would be listed.

Look for URLs that contain terms like:
- careers, jobs, openings, positions, opportunities, employment, hiring, work-with-us, join-us, join-our-team, etc.
- Common patterns: /careers, /jobs, /get-involved/careers, /about/careers, /opportunities, /work-with-us, etc.

MAIN PAGE LINKS:
{urls_text}

INSTRUCTIONS:
1. Return ONLY the single most likely careers/jobs URL
2. If no obvious careers URL exists, return "NONE" 
3. Do not return multiple URLs - pick the best one
4. Return just the URL, nothing else
5. Focus on URLs that would logically contain job listings

EXAMPLES of good responses:
https://example.org/careers
https://example.org/get-involved/our-careers
https://example.org/jobs
NONE

Your response:
"""
            
            logger.info(f"🤖 Asking Claude to identify careers URL from {len(url_list)} main page links")
            
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            claude_response = response.content[0].text.strip()
            logger.debug(f"Claude careers URL response: {claude_response}")
            
            # Parse response
            if claude_response == "NONE" or not claude_response.startswith('http'):
                logger.info(f"🤖 Claude found no clear careers URL on main page")
                return None
            
            # Validate the URL is in our discovered set
            if claude_response in main_page_links:
                logger.info(f"✅ Claude identified careers URL from main page: {claude_response}")
                return claude_response
            else:
                logger.warning(f"⚠️ Claude suggested URL not in main page links: {claude_response}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error calling Claude for careers URL identification: {e}")
            return None
    
    def find_job_related_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Find all job-related links on the careers page"""
        job_links = set()
        
        # Patterns to identify job-related links (more specific now since we're on careers page)
        job_link_patterns = [
            r'(?i)job',
            r'(?i)position',
            r'(?i)opening',
            r'(?i)opportunity',
            r'(?i)role',
            r'(?i)vacancy',
            r'(?i)apply'
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

    def aggregate_job_content(self, careers_root_url: str, max_pages: int = 10) -> Optional[str]:
        """Aggregate comprehensive job content from careers root URL and related pages"""
        try:
            logger.info(f"🔍 Aggregating job content from careers root: {careers_root_url}")
            
            all_content = []
            processed_urls = set()
            
            # Step 1: Get content from careers root page
            root_content = self.get_page_content(careers_root_url)
            if not root_content:
                logger.warning(f"⚠️ Could not get content from careers root URL: {careers_root_url}")
                return None
            
            all_content.append(f"=== CAREERS ROOT PAGE: {careers_root_url} ===\n{root_content}\n")
            processed_urls.add(careers_root_url)
            
            # Step 2: Parse careers root page to find job-related links
            try:
                response = self.session.get(careers_root_url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                job_links = self.find_job_related_links(soup, careers_root_url)
                
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
                logger.warning(f"⚠️ Error finding job links from {careers_root_url}: {e}")
            
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

    def update_organization_with_results(self, org_id: str, corrected_jobs_url: Optional[str], job_titles: Optional[List[str]]):
        """Update MongoDB document with corrected jobs URL and AI-extracted job_titles"""
        try:
            update_data = {
                "job_titles": job_titles,
                "job_titles_updated_at": datetime.utcnow().isoformat(),
                "job_titles_extraction_method": "claude_ai_with_url_discovery"
            }
            
            # Update jobs URL if we found a better one
            if corrected_jobs_url:
                update_data["jobs"] = corrected_jobs_url
                update_data["jobs_corrected_at"] = datetime.utcnow().isoformat()
                update_data["jobs_correction_method"] = "claude_ai_discovery"
            
            result = self.collection.update_one(
                {"_id": org_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                titles_count = len(job_titles) if job_titles else 0
                jobs_msg = f" and corrected jobs URL" if corrected_jobs_url else ""
                logger.info(f"✅ Updated organization {org_id} with {titles_count} job titles{jobs_msg}")
                return True
            else:
                logger.warning(f"⚠️ No changes made to organization {org_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update organization {org_id}: {e}")
            return False

    def process_all_organizations(self, limit: Optional[int] = None, test_mode: bool = False):
        """Process all organizations with AI job title extraction and URL discovery"""
        
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
            successful_url_discoveries = 0
            failed_extractions = 0
            
            for i, org in enumerate(organizations, 1):
                org_name = org.get('name', 'Unknown')
                org_id = org.get('_id')
                main_url = org.get('root', '')
                current_jobs_url = org.get('jobs', '')
                
                logger.info(f"\n🏢 Processing {i}/{len(organizations)}: {org_name}")
                logger.info(f"🌐 Main URL: {main_url}")
                logger.info(f"🔗 Current jobs URL: {current_jobs_url}")
                
                if not main_url:
                    logger.warning(f"⚠️ No main URL for {org_name}")
                    if not test_mode:
                        self.update_organization_with_results(org_id, None, None)
                        successful_updates += 1
                    failed_extractions += 1
                    processed += 1
                    continue
                
                # Step 1: Discover links from main page
                logger.info("🔍 Examining main page for career links...")
                main_page_links = self.discover_main_page_links(main_url)
                
                if not main_page_links:
                    logger.warning(f"⚠️ Could not discover any links from main page for {org_name}")
                    if not test_mode:
                        self.update_organization_with_results(org_id, None, None)
                        successful_updates += 1
                    failed_extractions += 1
                    processed += 1
                    continue
                
                # Step 2: Use AI to identify careers URL from main page links
                logger.info("🤖 Using AI to identify careers URL from main page links...")
                careers_url_from_main = self.identify_careers_url_from_main_page(main_page_links, org_name)
                
                if careers_url_from_main:
                    logger.info(f"✅ AI found careers URL from main page: {careers_url_from_main}")
                    successful_url_discoveries += 1
                    careers_url_to_use = careers_url_from_main
                    corrected_careers_url = careers_url_from_main  # Always update since we found it via AI
                else:
                    logger.warning(f"❌ No careers URL found on main page for {org_name}")
                    logger.info("🔄 Setting jobs and job_titles to null and continuing...")
                    if not test_mode:
                        self.update_organization_with_results(org_id, None, None)
                        successful_updates += 1
                    failed_extractions += 1
                    processed += 1
                    continue
                
                # Step 3: Aggregate comprehensive job content
                logger.info("📚 Aggregating comprehensive job content...")
                job_content = self.aggregate_job_content(careers_url_to_use)
                
                if not job_content:
                    logger.warning(f"⚠️ Could not aggregate job content for {org_name}")
                    if not test_mode:
                        self.update_organization_with_results(org_id, corrected_careers_url, None)
                        successful_updates += 1
                    failed_extractions += 1
                    processed += 1
                    time.sleep(2)  # Rate limiting
                    continue
                
                # Step 4: Extract job titles with Claude AI
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
                
                # Step 5: Update database
                if not test_mode:
                    if self.update_organization_with_results(org_id, corrected_careers_url, job_titles):
                        successful_updates += 1
                else:
                    successful_updates += 1  # In test mode, assume success
                
                processed += 1
                
                # Rate limiting (important for AI API calls)
                time.sleep(5)  # 5 seconds between requests to be respectful
                
                # Progress update every 3 organizations
                if i % 3 == 0:
                    logger.info(f"📊 Progress: {i}/{len(organizations)} organizations processed")
            
            # Final statistics
            logger.info(f"\n🎉 AI Job Titles Processing with URL Discovery Complete!")
            logger.info(f"📊 Statistics:")
            logger.info(f"   Total processed: {processed}")
            logger.info(f"   Database updates: {successful_updates}")
            logger.info(f"   Successful AI job extractions: {successful_extractions}")
            logger.info(f"   Successful URL discoveries: {successful_url_discoveries}")
            logger.info(f"   Failed extractions: {failed_extractions}")
            logger.info(f"   AI success rate: {(successful_extractions/processed)*100:.1f}%")
            logger.info(f"   URL discovery rate: {(successful_url_discoveries/processed)*100:.1f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during processing: {e}")
            return False
        finally:
            self.close_connection()


def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(
        description="AI-powered job titles extractor with career URL discovery using Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode with 2 organizations (requires ANTHROPIC_API_KEY env var)
  python ai_job_titles_updater_v2.py --test --limit 2
  
  # Production run on first 5 organizations
  python ai_job_titles_updater_v2.py --limit 5 --claude_api_key YOUR_API_KEY
  
  # Full production run (requires confirmation)
  python ai_job_titles_updater_v2.py --claude_api_key YOUR_API_KEY
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
    
    print("🚀 AI-Powered Job Titles Updater with Main Page URL Discovery")
    print("=" * 70)
    print("🤖 Using Claude AI for intelligent career URL discovery & job title extraction")
    print("📋 This script will:")
    print("   1. Examine each organization's main page for career links")
    print("   2. Use AI to identify the most likely careers/jobs URL")
    print("   3. If found: aggregate job content and extract job titles with AI")
    print("   4. If not found: set jobs and job_titles to null")
    print("   5. Update MongoDB with corrected URLs and extracted titles")
    print("=" * 70)
    
    if args.test:
        print("🧪 RUNNING IN TEST MODE - No database updates")
    
    if args.limit:
        print(f"🔢 Processing limit: {args.limit} organizations")
    else:
        print("🔄 Processing ALL organizations")
    
    # Confirmation for production runs
    if not args.test and not args.limit:
        print("\n⚠️ WARNING: This will process ALL 390+ organizations with AI")
        print("   Estimated time: 4-6 hours (website crawling + AI processing)")
        print("   Estimated cost: $50-100 in Claude API calls")
        
        try:
            confirm = input("\n❓ Continue with full processing? Type 'YES' to proceed: ")
            if confirm != 'YES':
                print("❌ Operation cancelled")
                return 1
        except:
            print("❌ Cannot get confirmation in non-interactive mode")
            return 1
    
    # Initialize and run updater
    updater = AIJobTitlesUpdaterV2(claude_api_key=claude_api_key)
    
    try:
        success = updater.process_all_organizations(
            limit=args.limit,
            test_mode=args.test
        )
        
        if success:
            print(f"\n✅ AI job titles extraction with URL discovery completed!")
            if not args.test:
                print(f"💾 MongoDB organizations collection updated with:")
                print(f"   • job_titles: [\"Title 1\", \"Title 2\", ...] or null")
                print(f"   • jobs: corrected career URLs where discovered")
                print(f"   • job_titles_extraction_method: \"claude_ai_with_url_discovery\"")
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