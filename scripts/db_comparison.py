#!/usr/bin/env python3
"""
Database comparison script for cloud alternatives
"""

# MongoDB Atlas (current)
MONGODB_ATLAS = {
    "connection": "mongodb+srv://user:pass@cluster.mongodb.net/nonprofit_jobs",
    "pricing": "$9-30/month",
    "pros": ["JSON native", "Full-text search", "Vector search", "Familiar"],
    "cons": ["NoSQL learning curve"]
}

# FerretDB (MongoDB-compatible with PostgreSQL backend)
FERRETDB = {
    "connection": "mongodb://localhost:27017/",
    "pricing": "$5-15/month (self-hosted)",
    "pros": ["100% MongoDB compatible", "Same queries/drivers", "PostgreSQL reliability", "Much cheaper"],
    "cons": ["Requires PostgreSQL backend", "Self-hosted setup"]
}

# Neon + FerretDB (Serverless PostgreSQL backend)
NEON_FERRET = {
    "connection": "mongodb://ferret:ferret@localhost:27017/",
    "pricing": "$5-19/month", 
    "pros": ["MongoDB API", "Serverless backend", "Best of both worlds"],
    "cons": ["More complex setup", "Two-layer architecture"]
}

def mongodb_example():
    """Current MongoDB approach"""
    return {
        "organizations": [
            {
                "_id": "org1",
                "name": "Idealist",
                "root": "https://idealist.org",
                "jobs": "https://idealist.org/jobs",
                "extracted_text": "job descriptions here...",
                "scraped_at": "2024-01-01"
            }
        ]
    }

def ferretdb_example():
    """How same data works with FerretDB (identical MongoDB syntax)"""
    return {
        "description": "FerretDB provides 100% MongoDB-compatible API",
        "queries": {
            "insert": """
            // Exact same MongoDB syntax
            db.organizations.insertMany([
                {
                    name: "Idealist",
                    root: "https://idealist.org", 
                    jobs: "https://idealist.org/jobs",
                    extracted_data: { text: "job descriptions here..." },
                    scraped_at: new Date()
                }
            ])
            """,
            "search": """
            // Full-text search (same as MongoDB)
            db.organizations.find({$text: {$search: "climate"}})
            
            // Regex search (same as MongoDB)  
            db.organizations.find({name: {$regex: "environment", $options: "i"}})
            """,
            "benefits": [
                "Same MongoDB drivers and tools",
                "Zero code changes from existing MongoDB",
                "PostgreSQL reliability and ACID transactions",
                "Much lower hosting costs than Atlas"
            ]
        }
    }

if __name__ == "__main__":
    print("Database Comparison for AnaJobs")
    print("=" * 40)
    
    for name, config in [
        ("MongoDB Atlas", MONGODB_ATLAS),
        ("FerretDB", FERRETDB), 
        ("Neon + FerretDB", NEON_FERRET)
    ]:
        print(f"\n{name}:")
        print(f"  Pricing: {config['pricing']}")
        print(f"  Pros: {', '.join(config['pros'])}")
        print(f"  Cons: {', '.join(config['cons'])}")