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

if __name__ == '__main__':
    sys.exit(main())