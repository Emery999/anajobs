#!/usr/bin/env python3
"""
Command Line Interface for AnaJobs
"""

import argparse
import sys
import os
from pathlib import Path

from .database import NonProfitJobSiteDB
from .config import get_config
from .extractor import extract_organization_text

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="AnaJobs - Non-Profit Job Site Data Management",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup database and load data')
    setup_parser.add_argument('--data-file', '-f', 
                            help='Path to data file (default: data/publicserviceopenings.jsonl)')
    setup_parser.add_argument('--connection-string', '-c',
                            help='MongoDB connection string (default: from config)')
    setup_parser.add_argument('--database-name', '-d',
                            help='Database name (default: from config)')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test database connection and data')
    test_parser.add_argument('--org-name', '-o', 
                           default='American Red Cross',
                           help='Organization name to test query')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search organizations')
    search_parser.add_argument('term', help='Search term')
    search_parser.add_argument('--limit', '-l', type=int, default=10,
                             help='Maximum results to return')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract text content from job pages')
    extract_parser.add_argument('--org-name', '-o', 
                               help='Organization name to extract content from')
    extract_parser.add_argument('--max-pages', '-m', type=int, default=5,
                               help='Maximum pages to crawl per organization (default: 5)')
    extract_parser.add_argument('--delay', '-d', type=float, default=1.0,
                               help='Delay between requests in seconds (default: 1.0)')
    extract_parser.add_argument('--output-file', '-f',
                               help='Save extracted content to file')
    extract_parser.add_argument('--sample', '-s', action='store_true',
                               help='Extract from sample organization (American Red Cross)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    config = get_config()
    
    try:
        if args.command == 'setup':
            return setup_command(args, config)
        elif args.command == 'test':
            return test_command(args, config)
        elif args.command == 'search':
            return search_command(args, config)
        elif args.command == 'stats':
            return stats_command(args, config)
        elif args.command == 'extract':
            return extract_command(args, config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0

def setup_command(args, config):
    """Handle setup command"""
    data_file = args.data_file or config.get('data_file', 'data/publicserviceopenings.jsonl')
    connection_string = args.connection_string or config.get('mongodb_uri', 'mongodb://localhost:27017/')
    database_name = args.database_name or config.get('database_name', 'nonprofit_jobs')
    
    # Check if data file exists
    if not os.path.exists(data_file):
        print(f"Error: Data file not found: {data_file}", file=sys.stderr)
        return 1
    
    db_manager = NonProfitJobSiteDB(connection_string, database_name)
    
    print("Setting up AnaJobs database...")
    
    # Connect
    if not db_manager.connect():
        print("Failed to connect to MongoDB", file=sys.stderr)
        return 1
    
    # Setup collection
    if not db_manager.setup_collection():
        print("Failed to setup collection", file=sys.stderr)
        return 1
    
    # Parse and load data
    print(f"Loading data from: {data_file}")
    organizations = db_manager.parse_corrupted_file(data_file)
    
    if not organizations:
        print("No organizations found in data file", file=sys.stderr)
        return 1
    
    if not db_manager.populate_database(organizations):
        print("Failed to populate database", file=sys.stderr)
        return 1
    
    # Test
    results = db_manager.test_database()
    if results["connection_test"]:
        print(f"✅ Setup completed successfully!")
        print(f"✅ Loaded {results['count_test']} organizations")
    else:
        print("❌ Setup completed but tests failed", file=sys.stderr)
        return 1
    
    db_manager.close_connection()
    return 0

def test_command(args, config):
    """Handle test command"""
    connection_string = config.get('mongodb_uri', 'mongodb://localhost:27017/')
    database_name = config.get('database_name', 'nonprofit_jobs')
    
    db_manager = NonProfitJobSiteDB(connection_string, database_name)
    
    if not db_manager.connect():
        print("Failed to connect to MongoDB", file=sys.stderr)
        return 1
    
    results = db_manager.test_database(args.org_name)
    
    print(f"Database Connection: {'✅' if results['connection_test'] else '❌'}")
    print(f"Total Organizations: {results['count_test']}")
    
    if results['query_test']:
        org = results['query_test']
        print(f"\nTest Query Result:")
        print(f"  Name: {org['name']}")
        print(f"  Root URL: {org['root']}")
        print(f"  Jobs URL: {org['jobs']}")
    else:
        print(f"\nTest organization '{args.org_name}' not found")
    
    print(f"\nSample Organizations:")
    for i, org in enumerate(results['sample_organizations'], 1):
        print(f"  {i}. {org['name']}")
    
    db_manager.close_connection()
    return 0

def search_command(args, config):
    """Handle search command"""
    connection_string = config.get('mongodb_uri', 'mongodb://localhost:27017/')
    database_name = config.get('database_name', 'nonprofit_jobs')
    
    db_manager = NonProfitJobSiteDB(connection_string, database_name)
    
    if not db_manager.connect():
        print("Failed to connect to MongoDB", file=sys.stderr)
        return 1
    
    results = db_manager.search_organizations(args.term, args.limit)
    
    print(f"Found {len(results)} organizations matching '{args.term}':")
    for i, org in enumerate(results, 1):
        print(f"  {i}. {org['name']}")
        print(f"     Jobs: {org['jobs']}")
    
    db_manager.close_connection()
    return 0

def stats_command(args, config):
    """Handle stats command"""
    connection_string = config.get('mongodb_uri', 'mongodb://localhost:27017/')
    database_name = config.get('database_name', 'nonprofit_jobs')
    
    db_manager = NonProfitJobSiteDB(connection_string, database_name)
    
    if not db_manager.connect():
        print("Failed to connect to MongoDB", file=sys.stderr)
        return 1
    
    collection = db_manager.db[db_manager.collection_name]
    
    total = collection.count_documents({})
    scraped = collection.count_documents({"scraped": True})
    org_domains = len(db_manager.get_organizations_by_domain(".org"))
    
    print(f"Database Statistics:")
    print(f"  Total Organizations: {total}")
    print(f"  Scraped: {scraped}")
    print(f"  Not Scraped: {total - scraped}")
    print(f"  .org Domains: {org_domains}")
    print(f"  Other Domains: {total - org_domains}")
    
    db_manager.close_connection()
    return 0

def extract_command(args, config):
    """Handle extract command"""
    import json
    from datetime import datetime
    
    connection_string = config.get('mongodb_uri', 'mongodb://localhost:27017/')
    database_name = config.get('database_name', 'nonprofit_jobs')
    
    db_manager = NonProfitJobSiteDB(connection_string, database_name)
    
    if not db_manager.connect():
        print("Failed to connect to MongoDB", file=sys.stderr)
        return 1
    
    # Determine which organization(s) to extract from
    if args.sample:
        # Use sample organization for testing
        org_data = {
            'name': 'American Red Cross',
            'root': 'https://www.redcross.org',
            'jobs': 'https://www.redcross.org/about-us/careers'
        }
        orgs_to_extract = [org_data]
        print("Extracting from sample organization: American Red Cross")
    elif args.org_name:
        # Find specific organization in database
        collection = db_manager.db[db_manager.collection_name]
        org = collection.find_one({"name": {"$regex": args.org_name, "$options": "i"}})
        
        if not org:
            print(f"Organization '{args.org_name}' not found in database", file=sys.stderr)
            db_manager.close_connection()
            return 1
            
        orgs_to_extract = [org]
        print(f"Extracting from: {org['name']}")
    else:
        print("Please specify --org-name or use --sample for testing", file=sys.stderr)
        db_manager.close_connection()
        return 1
    
    # Extract content from organization(s)
    extraction_results = []
    
    for org in orgs_to_extract:
        print(f"\n=== Extracting content from {org['name']} ===")
        print(f"Jobs URL: {org.get('jobs', 'N/A')}")
        
        try:
            result = extract_organization_text(
                org, 
                max_pages=args.max_pages, 
                delay=args.delay
            )
            
            extraction_results.append(result)
            
            # Display summary
            if result['extraction_successful']:
                print(f"✅ Successfully extracted content")
                print(f"   Pages crawled: {result['total_pages']}")
                print(f"   Text length: {len(result['extracted_text'])} characters")
                if result['pages_crawled']:
                    print(f"   URLs crawled:")
                    for url in result['pages_crawled']:
                        print(f"     - {url}")
            else:
                print("❌ Extraction failed")
                
            if result['errors']:
                print(f"   Errors: {len(result['errors'])}")
                for error in result['errors'][:3]:  # Show first 3 errors
                    print(f"     - {error}")
                    
        except Exception as e:
            print(f"❌ Error extracting from {org['name']}: {e}")
            extraction_results.append({
                'organization': org['name'],
                'extraction_successful': False,
                'errors': [str(e)]
            })
    
    # Save results to file if requested
    if args.output_file:
        output_data = {
            'extraction_timestamp': datetime.now().isoformat(),
            'extraction_config': {
                'max_pages': args.max_pages,
                'delay': args.delay
            },
            'results': extraction_results
        }
        
        try:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"\n✅ Results saved to: {args.output_file}")
        except Exception as e:
            print(f"❌ Error saving results: {e}", file=sys.stderr)
    
    # Display sample text if successful
    for result in extraction_results:
        if result['extraction_successful'] and result['extracted_text']:
            print(f"\n=== Sample extracted text from {result['organization']} ===")
            sample_text = result['extracted_text'][:500]  # First 500 characters
            print(f"{sample_text}...")
            if len(result['extracted_text']) > 500:
                print(f"(showing first 500 of {len(result['extracted_text'])} total characters)")
    
    db_manager.close_connection()
    
    # Return success if any extraction was successful
    return 0 if any(r['extraction_successful'] for r in extraction_results) else 1

if __name__ == '__main__':
    sys.exit(main())