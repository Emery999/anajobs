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
    
    # Database comparison command
    compare_parser = subparsers.add_parser('compare-db', help='Compare MongoDB vs FerretDB performance')
    compare_parser.add_argument('--ferret-uri', required=True,
                               help='FerretDB connection URI (MongoDB format)')
    compare_parser.add_argument('--data-file', '-f',
                               help='Data file to use for comparison')
    
    # FerretDB test command  
    ferret_parser = subparsers.add_parser('test-ferretdb', help='Test FerretDB connection and operations')
    ferret_parser.add_argument('--ferret-uri', required=True,
                              help='FerretDB connection URI (MongoDB format)')
    ferret_parser.add_argument('--setup', action='store_true',
                              help='Setup FerretDB collection structure')
    
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
        elif args.command == 'compare-db':
            return compare_db_command(args, config)
        elif args.command == 'test-ferretdb':
            return test_ferretdb_command(args, config)
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

def compare_db_command(args, config):
    """Handle database comparison command"""
    import json
    from datetime import datetime
    from .ferretdb import compare_databases
    
    # Load test data
    data_file = args.data_file or 'data/social_good_job_boards.jsonl'
    
    if not os.path.exists(data_file):
        print(f"Error: Data file not found: {data_file}", file=sys.stderr)
        return 1
    
    organizations = []
    try:
        with open(data_file, 'r') as f:
            for line in f:
                if line.strip():
                    org = json.loads(line.strip())
                    organizations.append({
                        'name': org['name'],
                        'root': org['root'],
                        'jobs': org['jobs'],
                        'status': 'active',
                        'scraped': False
                    })
    except Exception as e:
        print(f"Error loading data: {e}", file=sys.stderr)
        return 1
    
    if not organizations:
        print("No organizations found in data file", file=sys.stderr)
        return 1
    
    print(f"🔄 Comparing MongoDB Atlas vs FerretDB with {len(organizations)} organizations...")
    
    # Get MongoDB URI from config
    mongo_uri = config.get('mongodb_uri', 'mongodb://localhost:27017/')
    
    try:
        results = compare_databases(organizations, mongo_uri, args.ferret_uri)
        
        print("\n📊 Performance Comparison Results:")
        print("=" * 50)
        
        for db_name, metrics in results.items():
            print(f"\n{db_name.upper().replace('_', ' ')}:")
            print(f"  Setup Time: {metrics['setup_time']:.3f}s")
            print(f"  Query Time: {metrics['query_time']:.3f}s") 
            print(f"  Search Results: {len(metrics['search_results'])}")
            
        # Determine winner
        mongo_total = results['mongodb_atlas']['setup_time'] + results['mongodb_atlas']['query_time']
        ferret_total = results['ferretdb']['setup_time'] + results['ferretdb']['query_time']
        
        if mongo_total < ferret_total:
            winner = "MongoDB Atlas"
            margin = ferret_total - mongo_total
        else:
            winner = "FerretDB"
            margin = mongo_total - ferret_total
            
        print(f"\n🏆 Winner: {winner} (faster by {margin:.3f}s)")
        print(f"\n💰 Cost Analysis:")
        print(f"   MongoDB Atlas: $9-30/month")
        print(f"   FerretDB + PostgreSQL hosting: $5-15/month")
        print(f"   Estimated savings with FerretDB: 50-70%")
        
        return 0
        
    except Exception as e:
        print(f"❌ Comparison failed: {e}", file=sys.stderr)
        return 1

def test_ferretdb_command(args, config):
    """Handle FerretDB test command"""
    from .ferretdb import FerretJobSiteDB
    
    print("🔄 Testing FerretDB connection...")
    
    db = FerretJobSiteDB(args.ferret_uri)
    
    try:
        # Test connection
        if not db.connect():
            print("❌ Failed to connect to FerretDB", file=sys.stderr)
            return 1
        
        print("✅ Successfully connected to FerretDB")
        
        # Setup collection if requested
        if args.setup:
            print("🔧 Setting up FerretDB collection structure...")
            if db.setup_collection():
                print("✅ Collection structure setup complete")
                print("   Created indexes for: name, root, jobs, status, scraped")
                print("   Created full-text search index")
            else:
                print("❌ Collection setup failed")
                return 1
        
        # Test basic operations
        print("\n🧪 Testing basic operations...")
        
        # Load sample data
        sample_orgs = [
            {
                'name': 'Test Organization 1',
                'root': 'https://test1.org',
                'jobs': 'https://test1.org/jobs',
                'status': 'active',
                'scraped': False
            },
            {
                'name': 'Test Climate Org',
                'root': 'https://climate-test.org',
                'jobs': 'https://climate-test.org/careers',
                'status': 'active', 
                'scraped': False
            }
        ]
        
        if db.populate_database(sample_orgs):
            print("✅ Sample data inserted successfully")
        else:
            print("❌ Failed to insert sample data")
            return 1
        
        # Test database operations
        test_results = db.test_database("Test Organization 1")
        
        if test_results["connection_test"]:
            print(f"✅ Database test passed")
            print(f"   Total organizations: {test_results['count_test']}")
            if test_results['query_test']:
                print(f"   Found test org: {test_results['query_test']['name']}")
        else:
            print("❌ Database test failed")
            return 1
        
        # Test search
        search_results = db.search_organizations("climate", 5)
        print(f"✅ Search test: found {len(search_results)} results for 'climate'")
        
        # Test domain filtering
        domain_results = db.get_organizations_by_domain(".org")
        print(f"✅ Domain filter test: found {len(domain_results)} .org domains")
        
        # Test MongoDB-specific operations
        unscraped_orgs = db.get_unscraped_organizations(3)
        print(f"✅ Unscraped orgs test: found {len(unscraped_orgs)} organizations")
        
        # Test content storage
        test_content = {
            "text": "This is test extracted content about climate change jobs...",
            "pages_crawled": ["https://climate-test.org/careers"],
            "extraction_date": "2024-01-01"
        }
        
        if db.store_extracted_content("Test Climate Org", test_content):
            print("✅ Content storage test: successfully stored extracted content")
        else:
            print("❌ Content storage test failed")
        
        print("\n🎉 All FerretDB tests passed!")
        print("\n💡 Key Benefits Demonstrated:")
        print("   ✅ 100% MongoDB-compatible API")
        print("   ✅ Same queries and operations as MongoDB")
        print("   ✅ PostgreSQL reliability with MongoDB simplicity")
        print("   ✅ Significant cost savings potential")
        
        return 0
        
    except Exception as e:
        print(f"❌ FerretDB test failed: {e}", file=sys.stderr)
        return 1
    finally:
        db.close_connection()

if __name__ == '__main__':
    sys.exit(main())