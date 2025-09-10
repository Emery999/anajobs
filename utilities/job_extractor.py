#!/usr/bin/env python3
"""
Job Extractor with Claude AI Integration

This script fetches organizations from MongoDB, scrapes job listings from their career pages,
and uses Claude AI to parse job information into structured data according to the job schema.

Usage:
    python job_extractor.py --site_limit 5 --output sample_jobs_extraction_5.jsonl
"""

import json
import requests
import time
import re
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import logging
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import anthropic

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JobExtractor:
    def __init__(self, claude_api_key: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # MongoDB connection
        self.uri = "mongodb+srv://seeotter_db_user:n8tfO3zzASvoxllr@cluster0.hxabnjn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.db_name = "social_impact_jobs"
        self.collection_name = "organizations"
        
        # Claude AI client
        self.claude_client = None
        if claude_api_key:
            self.claude_client = anthropic.Anthropic(api_key=claude_api_key)
        
        # Job schema fields for parsing
        self.job_schema_fields = [
            "job_id", "organization", "position", "location", "responsibilities", 
            "requirements", "preferred_qualifications", "compensation", "benefits",
            "application_process", "posting_metadata"
        ]

    def connect_to_mongodb(self):
        """Connect to MongoDB and get organizations"""
        try:
            client = MongoClient(self.uri, server_api=ServerApi('1'))
            client.admin.command('ping')
            db = client[self.db_name]
            collection = db[self.collection_name]
            logger.info("✅ Connected to MongoDB Atlas")
            return collection
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return None

    def extract_page_content(self, url: str) -> Optional[Dict]:
        """Extract content from a job page with category detection"""
        try:
            logger.info(f"📄 Fetching: {url}")
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            
            # Extract text content
            text_content = soup.get_text(separator='\n', strip=True)
            
            # Try to detect job categories/departments
            categories = self.detect_job_categories(soup, text_content)
            
            # Extract job listings
            job_elements = self.find_job_elements(soup)
            
            return {
                'url': url,
                'text_content': text_content[:20000],  # Limit content
                'categories': categories,
                'job_elements': len(job_elements),
                'raw_html_snippet': str(soup)[:10000] if job_elements else None
            }
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error extracting content from {url}: {e}")
            return None

    def detect_job_categories(self, soup: BeautifulSoup, text: str) -> List[str]:
        """Detect job categories/departments from page structure"""
        categories = []
        
        # Look for common department/category patterns
        category_patterns = [
            r'(?i)(engineering|finance|marketing|operations|programs|communications|hr|human resources|development|fundraising|admin|executive|medical|clinical|field|logistics)',
            r'(?i)(technology|it|data|research|policy|advocacy|partnerships|education|training)'
        ]
        
        # Search in headings first
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
        for heading in headings:
            heading_text = heading.get_text(strip=True)
            for pattern in category_patterns:
                matches = re.findall(pattern, heading_text)
                categories.extend(matches)
        
        # Search in navigation/menu items
        nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'menu|nav|category|department|filter', re.I))
        for nav in nav_elements:
            nav_text = nav.get_text(strip=True)
            for pattern in category_patterns:
                matches = re.findall(pattern, nav_text)
                categories.extend(matches)
        
        # Remove duplicates and return
        return list(set([cat.lower().capitalize() for cat in categories]))

    def find_job_elements(self, soup: BeautifulSoup) -> List:
        """Find potential job listing elements on the page"""
        job_elements = []
        
        # Common selectors for job listings
        job_selectors = [
            'div[class*="job"]',
            'div[class*="position"]',
            'div[class*="opening"]',
            'div[class*="career"]',
            'li[class*="job"]',
            'tr[class*="job"]',
            'a[href*="job"]',
            'a[href*="position"]',
            'a[href*="career"]'
        ]
        
        for selector in job_selectors:
            elements = soup.select(selector)
            job_elements.extend(elements)
        
        return job_elements[:50]  # Limit to prevent overload

    def parse_jobs_with_claude(self, page_content: Dict, organization: Dict) -> List[Dict]:
        """Use Claude AI to parse job information from page content"""
        if not self.claude_client:
            logger.warning("⚠️ Claude AI client not configured - using fallback parsing")
            return self.fallback_job_parsing(page_content, organization)
        
        try:
            # Prepare the prompt for Claude
            prompt = self.create_claude_prompt(page_content, organization)
            
            logger.info(f"🤖 Calling Claude AI to parse jobs from {page_content['url']}")
            
            # Call Claude API
            response = self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.1,
                messages=[{
                    "role": "user", 
                    "content": prompt
                }]
            )
            
            # Parse Claude's response
            claude_response = response.content[0].text
            jobs = self.parse_claude_response(claude_response, organization, page_content['categories'])
            
            logger.info(f"✅ Claude parsed {len(jobs)} jobs from {page_content['url']}")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ Error calling Claude AI: {e}")
            return self.fallback_job_parsing(page_content, organization)

    def create_claude_prompt(self, page_content: Dict, organization: Dict) -> str:
        """Create a detailed prompt for Claude to parse job listings"""
        
        prompt = f"""
You are an expert at extracting structured job listing data from career page content. 

ORGANIZATION INFO:
Name: {organization['name']}
Sector: {organization.get('sector', 'Unknown')}
Website: {organization.get('root', '')}
Job Categories Found: {', '.join(page_content['categories']) if page_content['categories'] else 'None detected'}

TASK: Extract all individual job listings from the following career page content and structure each job according to this schema:

REQUIRED FIELDS for each job:
- job_id: Create unique ID (format: ORG-YYYY-001, ORG-YYYY-002, etc.)
- position.title: Job title
- position.department: Department/team (use detected categories when possible)
- position.level: entry/mid/senior/director/executive/intern/volunteer
- position.employment_type: full_time/part_time/contract/temporary/intern/volunteer/consultant
- location.type: remote/on_site/hybrid/field_based/multi_location
- location.primary_location: {{city, state_province, country}} if mentioned
- responsibilities: Array of key responsibilities (3-5 items)
- requirements.experience.minimum_years: Estimated years needed
- application_process.application_url: Direct apply link if found

OPTIONAL FIELDS (include if clearly mentioned):
- requirements.education.minimum_degree: bachelor/master/phd/professional/none
- requirements.technical_skills: Array of technical skills
- requirements.languages: Array with language and required/preferred
- compensation.salary_range: If mentioned
- posting_metadata.date_posted: If date is visible

OUTPUT FORMAT: Return ONLY a valid JSON array of job objects. Do not include explanatory text.

CAREER PAGE CONTENT:
{page_content['text_content']}

Extract jobs now:
"""
        return prompt

    def parse_claude_response(self, claude_response: str, organization: Dict, categories: List[str]) -> List[Dict]:
        """Parse Claude's JSON response into structured job data"""
        try:
            # Try to extract JSON from Claude's response
            json_start = claude_response.find('[')
            json_end = claude_response.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = claude_response[json_start:json_end]
                jobs_data = json.loads(json_str)
                
                # Enhance each job with organization data and parent categories
                enhanced_jobs = []
                for job in jobs_data:
                    enhanced_job = self.enhance_job_data(job, organization, categories)
                    enhanced_jobs.append(enhanced_job)
                
                return enhanced_jobs
            else:
                logger.warning("⚠️ No valid JSON found in Claude response")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing Claude JSON response: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error processing Claude response: {e}")
            return []

    def enhance_job_data(self, job: Dict, organization: Dict, categories: List[str]) -> Dict:
        """Enhance job data with organization info and parent categories"""
        
        # Add organization information
        enhanced_job = {
            "job_id": job.get("job_id", f"{organization['name'].upper()}-2024-001"),
            "organization": {
                "name": organization['name'],
                "type": self.map_sector_to_org_type(organization.get('sector', 'Unknown')),
                "sector": [self.map_to_schema_sector(organization.get('sector', 'Unknown'))],
                "website": organization.get('root', '')
            },
            "position": job.get("position", {}),
            "location": job.get("location", {"type": "on_site"}),
            "responsibilities": job.get("responsibilities", []),
            "requirements": job.get("requirements", {}),
            "application_process": job.get("application_process", {}),
            "posting_metadata": {
                "date_posted": datetime.now().strftime('%Y-%m-%d'),
                "extraction_date": datetime.now().isoformat(),
                "source_url": organization.get('jobs', ''),
                **job.get("posting_metadata", {})
            }
        }
        
        # Add parent category if department matches detected categories
        if categories and enhanced_job["position"].get("department"):
            dept = enhanced_job["position"]["department"].lower()
            matching_categories = [cat for cat in categories if cat.lower() in dept or dept in cat.lower()]
            if matching_categories:
                enhanced_job["parent_category"] = matching_categories[0]
        elif categories:
            enhanced_job["parent_category"] = categories[0]  # Use first detected category
        
        return enhanced_job

    def map_sector_to_org_type(self, sector: str) -> str:
        """Map organization sector to schema org type"""
        sector_mapping = {
            'Healthcare': 'nonprofit',
            'Social Services': 'nonprofit', 
            'Environmental Services': 'nonprofit',
            'Education': 'nonprofit',
            'Professional Consulting Services': 'social_enterprise',
            'Information Technology Services': 'startup',
            'Financial Services': 'social_enterprise'
        }
        return sector_mapping.get(sector, 'nonprofit')

    def map_to_schema_sector(self, sector: str) -> str:
        """Map organization sector to job schema sector"""
        mapping = {
            'Healthcare': 'health',
            'Environmental Services': 'environment',
            'Social Services': 'humanitarian',
            'Education': 'education',
            'Information Technology Services': 'technology'
        }
        return mapping.get(sector, 'humanitarian')

    def fallback_job_parsing(self, page_content: Dict, organization: Dict) -> List[Dict]:
        """Fallback job parsing without Claude AI"""
        logger.info("🔧 Using fallback job parsing")
        
        # Simple regex-based job extraction
        text = page_content['text_content']
        job_patterns = [
            r'(?i)(software engineer|program manager|director|coordinator|analyst|specialist|associate|intern)',
            r'(?i)(remote|full.?time|part.?time)',
            r'(?i)(apply now|view job|see details)'
        ]
        
        jobs = []
        job_titles = re.findall(r'(?i)([\w\s]+(?:engineer|manager|director|coordinator|analyst|specialist|associate|intern))', text)
        
        for i, title in enumerate(job_titles[:3]):  # Limit to 3 jobs
            job = {
                "job_id": f"{organization['name'].upper()}-2024-{i+1:03d}",
                "organization": {
                    "name": organization['name'],
                    "type": self.map_sector_to_org_type(organization.get('sector', 'Unknown')),
                    "sector": [self.map_to_schema_sector(organization.get('sector', 'Unknown'))],
                    "website": organization.get('root', '')
                },
                "position": {
                    "title": title.strip(),
                    "employment_type": "full_time"
                },
                "location": {"type": "on_site"},
                "responsibilities": ["Responsibilities to be determined"],
                "requirements": {"experience": {"minimum_years": 2}},
                "posting_metadata": {
                    "date_posted": datetime.now().strftime('%Y-%m-%d'),
                    "extraction_date": datetime.now().isoformat(),
                    "source_url": organization.get('jobs', ''),
                    "extraction_method": "fallback"
                }
            }
            
            if page_content['categories']:
                job["parent_category"] = page_content['categories'][0]
                
            jobs.append(job)
        
        return jobs

    def process_organizations(self, site_limit: int = 5, output_file: str = "sample_jobs_extraction_5.jsonl"):
        """Main processing function"""
        
        logger.info(f"🚀 Starting job extraction for up to {site_limit} organizations")
        
        # Connect to MongoDB
        collection = self.connect_to_mongodb()
        if collection is None:
            return False
        
        # Get organizations from MongoDB
        organizations = list(collection.find().limit(site_limit))
        logger.info(f"📊 Retrieved {len(organizations)} organizations from MongoDB")
        
        extracted_data = []
        
        for i, org in enumerate(organizations, 1):
            logger.info(f"\n🏢 Processing organization {i}/{len(organizations)}: {org['name']}")
            
            jobs_url = org.get('jobs', '')
            if not jobs_url:
                logger.warning(f"⚠️ No jobs URL for {org['name']}")
                continue
            
            # Extract job page content
            page_content = self.extract_page_content(jobs_url)
            if not page_content:
                logger.warning(f"⚠️ Could not extract content from {jobs_url}")
                continue
            
            # Parse jobs using Claude AI
            jobs = self.parse_jobs_with_claude(page_content, org)
            
            # Create augmented organization entry
            augmented_org = {
                **org,  # Include all original fields
                "extraction_metadata": {
                    "extraction_date": datetime.now().isoformat(),
                    "jobs_url": jobs_url,
                    "jobs_found": len(jobs),
                    "categories_detected": page_content['categories']
                },
                "extracted_jobs": jobs
            }
            
            extracted_data.append(augmented_org)
            
            logger.info(f"✅ Extracted {len(jobs)} jobs from {org['name']}")
            
            # Rate limiting
            time.sleep(2)
        
        # Write output file
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in extracted_data:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + '\n')
        
        logger.info(f"\n🎉 Job extraction complete!")
        logger.info(f"📤 Output saved to: {output_file}")
        logger.info(f"📊 Processed {len(extracted_data)} organizations")
        
        total_jobs = sum(len(entry.get('extracted_jobs', [])) for entry in extracted_data)
        logger.info(f"📋 Total jobs extracted: {total_jobs}")
        
        return True


def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(
        description="Extract job listings from organization career pages using Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--site_limit', type=int, default=5,
                       help='Maximum number of organizations to process (default: 5)')
    
    parser.add_argument('--output', type=str, default="sample_jobs_extraction_5.jsonl",
                       help='Output file path (default: sample_jobs_extraction_5.jsonl)')
    
    parser.add_argument('--claude_api_key', type=str,
                       help='Claude API key (or set ANTHROPIC_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Get Claude API key from args or environment
    claude_api_key = args.claude_api_key or os.getenv('ANTHROPIC_API_KEY')
    
    if not claude_api_key:
        logger.warning("⚠️ No Claude API key provided. Using fallback parsing.")
        logger.warning("   Set ANTHROPIC_API_KEY env var or use --claude_api_key argument")
    
    # Initialize and run extractor
    extractor = JobExtractor(claude_api_key=claude_api_key)
    
    try:
        success = extractor.process_organizations(
            site_limit=args.site_limit,
            output_file=args.output
        )
        
        if success:
            print(f"\n✅ Job extraction completed successfully!")
            print(f"📁 Output file: {args.output}")
            return 0
        else:
            print(f"\n❌ Job extraction failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n❌ Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    import os
    sys.exit(main())