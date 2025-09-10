#!/usr/bin/env python3
"""
Sector Enhancement Utility for AnaJobs

This script reads organizations from complete_enhanced_jsonl.txt, scrapes their websites
to extract mission/vision statements, infers the appropriate GICS sector category,
and outputs an enhanced JSONL file with corrected sectors and descriptions.

GICS Sectors:
- Communication Services
- Consumer Discretionary  
- Consumer Staples
- Energy
- Financials
- Health Care
- Industrials
- Information Technology
- Materials
- Real Estate
- Utilities
- Professional Consulting Services (custom for law/accounting)
"""

import json
import requests
import time
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SectorEnhancer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # GICS sectors plus custom Professional Consulting Services
        self.gics_sectors = [
            "Communication Services",
            "Consumer Discretionary",
            "Consumer Staples", 
            "Energy",
            "Financials",
            "Health Care",
            "Industrials",
            "Information Technology",
            "Materials",
            "Real Estate",
            "Utilities",
            "Professional Consulting Services"  # Custom for law/accounting
        ]
        
        # Sector classification keywords
        self.sector_keywords = {
            "Communication Services": [
                "media", "telecommunications", "broadcast", "publishing", "advertising",
                "marketing", "communications", "entertainment", "streaming", "social media",
                "content", "digital media", "news", "journalism", "public relations"
            ],
            "Consumer Discretionary": [
                "retail", "restaurants", "hotels", "travel", "tourism", "leisure",
                "automotive", "apparel", "luxury", "consumer goods", "e-commerce",
                "hospitality", "recreation", "consumer services", "fashion"
            ],
            "Consumer Staples": [
                "food", "beverage", "grocery", "household products", "personal care",
                "tobacco", "consumer staples", "packaged foods", "cleaning products",
                "cosmetics", "pharmacy"
            ],
            "Energy": [
                "oil", "gas", "petroleum", "energy", "renewable energy", "solar",
                "wind", "coal", "nuclear", "electricity generation", "power",
                "biofuels", "hydroelectric", "geothermal"
            ],
            "Financials": [
                "bank", "insurance", "investment", "finance", "financial services",
                "credit", "lending", "mortgage", "securities", "asset management",
                "wealth management", "private equity", "venture capital", "trading"
            ],
            "Health Care": [
                "healthcare", "medical", "pharmaceutical", "biotechnology", "hospital",
                "clinic", "health services", "medical devices", "diagnostics",
                "therapeutics", "wellness", "telemedicine", "mental health"
            ],
            "Industrials": [
                "manufacturing", "construction", "aerospace", "defense", "transportation",
                "logistics", "industrial equipment", "machinery", "engineering",
                "infrastructure", "shipping", "aviation", "railroad", "trucking"
            ],
            "Information Technology": [
                "software", "technology", "IT", "computer", "internet", "cloud",
                "cybersecurity", "artificial intelligence", "data", "analytics",
                "hardware", "semiconductor", "telecommunications equipment", "fintech"
            ],
            "Materials": [
                "chemicals", "metals", "mining", "paper", "packaging", "construction materials",
                "steel", "aluminum", "forestry", "commodity chemicals", "plastics"
            ],
            "Real Estate": [
                "real estate", "property", "REIT", "development", "commercial property",
                "residential property", "property management", "construction",
                "real estate investment", "land development"
            ],
            "Utilities": [
                "utility", "electric", "water", "gas utility", "waste management",
                "renewable utilities", "power distribution", "municipal services",
                "environmental services", "recycling"
            ],
            "Professional Consulting Services": [
                "law", "legal", "attorney", "accounting", "audit", "consulting",
                "advisory", "professional services", "tax", "compliance",
                "business consulting", "management consulting"
            ]
        }
        
        # Mission/vision statement indicators
        self.mission_indicators = [
            "mission", "vision", "purpose", "about us", "who we are", "what we do",
            "our story", "why we exist", "our mission", "our vision", "our purpose"
        ]
        
    def extract_text_content(self, url: str, max_retries: int = 2) -> Optional[str]:
        """Extract text content from a webpage"""
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Attempting to fetch {url} (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=15, allow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text[:10000]  # Limit text length
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed for {url}: {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return None
            except Exception as e:
                logger.error(f"Unexpected error extracting content from {url}: {e}")
                return None
        
        return None

    def find_mission_statement(self, text: str, org_name: str) -> Optional[str]:
        """Extract mission/vision statement from text"""
        if not text:
            return None
            
        text_lower = text.lower()
        
        # Look for common mission/vision patterns
        patterns = [
            r'(?:our\s+)?(?:mission|vision|purpose)[\s\w]*?(?:is|:)\s*([^.!?]*[.!?])',
            r'(?:we\s+(?:believe|are|exist|work|strive|aim|help|provide|serve|support|fight|advocate))\s+([^.!?]*[.!?])',
            r'(?:' + re.escape(org_name.lower()) + r')\s+(?:is|works|helps|provides|serves|supports|fights|advocates)\s+([^.!?]*[.!?])',
            r'(?:founded|established|created)\s+(?:to|for)\s+([^.!?]*[.!?])',
            r'(?:dedicated|committed)\s+to\s+([^.!?]*[.!?])'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                statement = match.group(1).strip()
                if len(statement) > 20 and len(statement) < 300:  # Reasonable length
                    # Clean up the statement
                    statement = re.sub(r'\s+', ' ', statement)
                    statement = statement.strip(' .,;:')
                    return statement.capitalize()
        
        # Fallback: look for first meaningful sentence about the organization
        sentences = re.split(r'[.!?]', text)
        for sentence in sentences[:20]:  # Check first 20 sentences
            sentence = sentence.strip()
            if (len(sentence) > 30 and len(sentence) < 200 and
                any(keyword in sentence.lower() for keyword in ['help', 'provide', 'serve', 'support', 'work', 'mission', 'dedicated'])):
                return sentence.capitalize()
        
        return None

    def classify_sector(self, text: str, org_name: str, current_sector: str) -> str:
        """Classify organization into appropriate GICS sector based on text content"""
        if not text:
            return current_sector
            
        text_lower = text.lower()
        sector_scores = {}
        
        # Score each sector based on keyword matches
        for sector, keywords in self.sector_keywords.items():
            score = 0
            for keyword in keywords:
                # Count occurrences of each keyword
                occurrences = len(re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower))
                score += occurrences
                
                # Bonus points if keyword appears in organization name
                if keyword.lower() in org_name.lower():
                    score += 5
            
            if score > 0:
                sector_scores[sector] = score
        
        # Special logic for law and accounting organizations
        law_keywords = ['law', 'legal', 'attorney', 'lawyer', 'court', 'litigation']
        accounting_keywords = ['accounting', 'audit', 'tax', 'cpa', 'financial advisory']
        
        if any(keyword in text_lower or keyword in org_name.lower() for keyword in law_keywords + accounting_keywords):
            return "Professional Consulting Services"
        
        # Return the sector with highest score, or current sector if no clear match
        if sector_scores:
            best_sector = max(sector_scores, key=sector_scores.get)
            # Only change sector if we have strong confidence (score > 2)
            if sector_scores[best_sector] > 2:
                return best_sector
        
        return current_sector

    def process_organization(self, org: Dict) -> Dict:
        """Process a single organization entry"""
        logger.info(f"Processing: {org['name']}")
        
        # Start with original data
        enhanced_org = org.copy()
        
        # Extract content from website
        text_content = self.extract_text_content(org['root'])
        
        if text_content:
            # Extract mission/vision statement
            description = self.find_mission_statement(text_content, org['name'])
            if description:
                enhanced_org['description'] = description
                logger.info(f"Found description for {org['name']}: {description[:50]}...")
            
            # Classify sector
            new_sector = self.classify_sector(text_content, org['name'], org.get('sector', 'Unknown'))
            if new_sector != org.get('sector'):
                logger.info(f"Sector changed for {org['name']}: {org.get('sector')} -> {new_sector}")
                enhanced_org['sector'] = new_sector
            else:
                enhanced_org['sector'] = org.get('sector', 'Unknown')
        else:
            logger.warning(f"Could not extract content for {org['name']}")
            enhanced_org['sector'] = org.get('sector', 'Unknown')
        
        # Add processing timestamp
        enhanced_org['processed_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        return enhanced_org

    def process_file(self, input_file: str, output_file: str, max_orgs: Optional[int] = None):
        """Process the input JSONL file and create enhanced output"""
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        if not input_path.exists():
            logger.error(f"Input file not found: {input_file}")
            return
        
        logger.info(f"Processing {input_file} -> {output_file}")
        
        processed_count = 0
        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:
            
            for line_num, line in enumerate(infile, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    org = json.loads(line)
                    enhanced_org = self.process_organization(org)
                    
                    # Write enhanced organization to output file
                    outfile.write(json.dumps(enhanced_org, ensure_ascii=False) + '\n')
                    processed_count += 1
                    
                    if max_orgs and processed_count >= max_orgs:
                        logger.info(f"Reached maximum organizations limit: {max_orgs}")
                        break
                    
                    # Rate limiting
                    time.sleep(1)  # 1 second between requests
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON on line {line_num}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        logger.info(f"Processing complete. Enhanced {processed_count} organizations.")


def main():
    """Main function"""
    enhancer = SectorEnhancer()
    
    # File paths
    input_file = "data/complete_enhanced_jsonl.txt"
    output_file = "data/complete_enhanced_with_sectors_and_descriptions.jsonl"
    
    # Process first 10 organizations for testing
    # Remove max_orgs parameter to process all organizations
    enhancer.process_file(input_file, output_file, max_orgs=10)
    
    print(f"\n✅ Enhancement complete!")
    print(f"📥 Input: {input_file}")
    print(f"📤 Output: {output_file}")
    print(f"🔍 Check the output file for enhanced sector classifications and descriptions")


if __name__ == "__main__":
    main()