# FerretDB Setup Guide for AnaJobs

This guide will help you set up FerretDB as a MongoDB-compatible alternative with PostgreSQL backend for lower-cost cloud database storage.

## 🚀 Quick Start

### What is FerretDB?

FerretDB is a **100% MongoDB-compatible** database that uses PostgreSQL as its backend. This gives you:
- **Exact same MongoDB API** - no code changes needed
- **PostgreSQL reliability** and ACID transactions  
- **Much lower hosting costs** compared to MongoDB Atlas
- **Same drivers, tools, and ecosystem** as MongoDB

### Step 1: Choose Your Setup

#### Option A: Local Development
```bash
# Start FerretDB with Docker Compose
docker-compose up -d ferretdb postgres
```

#### Option B: Cloud Hosting (Recommended)
1. **Backend**: Set up PostgreSQL on any cloud provider:
   - **DigitalOcean**: $5-20/month
   - **Hetzner**: €4-15/month  
   - **Neon**: $0-19/month (serverless)
   - **Supabase**: $0-25/month (managed PostgreSQL)

2. **FerretDB**: Run FerretDB container connecting to your PostgreSQL

### Step 2: Install Dependencies
```bash
# FerretDB uses standard MongoDB drivers
pip install pymongo

# No additional dependencies needed!
```

### Step 3: Connection Setup

#### Local Connection
```python
# Connect to local FerretDB (same as MongoDB)
ferret_uri = "mongodb://username:password@localhost:27017/"
```

#### Cloud Connection  
```python
# Connect to hosted FerretDB instance
ferret_uri = "mongodb://username:password@your-ferretdb-host:27017/"
```

### Step 4: Test Connection
```bash
anajobs test-ferretdb \
  --ferret-uri "mongodb://user:pass@host:27017/" \
  --setup
```

## 🐳 Docker Setup

### docker-compose.yml
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ferretdb
      POSTGRES_USER: ferretdb
      POSTGRES_PASSWORD: ferretdb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  ferretdb:
    image: ghcr.io/ferretdb/ferretdb:latest
    environment:
      FERRETDB_POSTGRESQL_URL: postgres://ferretdb:ferretdb@postgres:5432/ferretdb
    ports:
      - "27017:27017"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

### Start Services
```bash
# Start both PostgreSQL and FerretDB
docker-compose up -d

# Check FerretDB is running
docker-compose logs ferretdb
```

## 📊 Database Comparison

Compare MongoDB Atlas vs FerretDB performance:

```bash
anajobs compare-db \
  --ferret-uri "mongodb://user:pass@host:27017/"
```

## 💻 Python API Usage

### Identical MongoDB Syntax
```python
from anajobs import FerretJobSiteDB

# Initialize connection (same interface as MongoDB)
db = FerretJobSiteDB(
    ferret_uri="mongodb://ferretdb:ferretdb@localhost:27017/",
    database_name="nonprofit_jobs"
)

# Connect and setup
if db.connect():
    db.setup_collection()
    
    # Load organizations (same as MongoDB)
    organizations = [
        {
            'name': 'Idealist',
            'root': 'https://idealist.org',
            'jobs': 'https://idealist.org/jobs',
            'status': 'active',
            'scraped': False
        }
    ]
    
    db.populate_database(organizations)
    
    # Search organizations (identical MongoDB queries)
    results = db.search_organizations("climate", limit=10)
    
    # Test database
    test_results = db.test_database()
    
    db.close_connection()
```

### Advanced MongoDB Features
```python
# All MongoDB operations work identically:

# Text search
results = db.search_organizations("environmental sustainability")

# Regex queries  
collection.find({"name": {"$regex": "climate", "$options": "i"}})

# Complex aggregations
pipeline = [
    {"$match": {"status": "active"}},
    {"$group": {"_id": "$domain", "count": {"$sum": 1}}}
]
collection.aggregate(pipeline)

# Update operations
collection.update_one(
    {"name": "Idealist"},
    {"$set": {"scraped": True, "last_scraped": datetime.utcnow()}}
)
```

## 🏗️ Production Setup

### Cloud Hosting Options

#### Option 1: DigitalOcean ($10-25/month total)
```bash
# 1. Create PostgreSQL managed database ($15/month)
# 2. Deploy FerretDB on App Platform ($5/month)
# 3. Connect FerretDB to PostgreSQL
```

#### Option 2: Hetzner (€8-20/month total) 
```bash
# 1. VPS with PostgreSQL (€4/month)
# 2. Docker container running FerretDB (€4/month)
# 3. Very cost-effective for European users
```

#### Option 3: Neon + FerretDB ($5-19/month)
```bash
# 1. Neon serverless PostgreSQL (scales to zero)
# 2. FerretDB container on any platform
# 3. Pay only for actual usage
```

### Environment Configuration
```bash
# Set environment variables
export FERRET_URI="mongodb://user:pass@ferretdb-host:27017/"
export POSTGRES_URL="postgresql://user:pass@postgres-host:5432/ferretdb"
```

## 🔍 Monitoring & Maintenance

### Health Checks
```python
# Test FerretDB connectivity
def health_check():
    db = FerretJobSiteDB(ferret_uri)
    if db.connect():
        result = db.test_database()
        return result["connection_test"]
    return False
```

### Backup Strategy
```bash
# Backup PostgreSQL (standard pg_dump)
pg_dump ferretdb > backup.sql

# Restore 
psql ferretdb < backup.sql
```

### Monitoring
- **FerretDB**: Monitor via MongoDB drivers/tools
- **PostgreSQL**: Use standard PostgreSQL monitoring
- **Performance**: Same MongoDB profiling tools work

## 📈 Performance Benefits

| Feature | MongoDB Atlas | FerretDB |
|---------|---------------|----------|
| API Compatibility | ✅ Native | ✅ 100% Compatible |
| Query Syntax | ✅ MongoDB | ✅ Identical MongoDB |
| Full-text Search | ✅ | ✅ |
| ACID Transactions | ✅ | ✅ (PostgreSQL) |
| Cost (small apps) | $9-30/month | $5-15/month |
| Hosting Flexibility | ❌ Atlas only | ✅ Any provider |
| Ecosystem | ✅ Mature | ✅ Same tools work |

## 💰 Cost Comparison

### MongoDB Atlas Pricing
- **Free Tier**: 512MB
- **Paid**: $9-30/month minimum
- **Scaling**: Expensive for larger datasets

### FerretDB + PostgreSQL Hosting
- **DigitalOcean**: $10-25/month total
- **Hetzner**: €8-20/month total  
- **Neon**: $5-19/month (serverless)
- **Self-hosted**: $5-10/month

**Savings: 50-70% cost reduction**

## 🔄 Migration from MongoDB

### Zero Code Changes Required
```python
# Your existing MongoDB code works unchanged:

# Before (MongoDB Atlas)
mongo_db = MongoClient("mongodb+srv://user:pass@cluster.mongodb.net/")

# After (FerretDB) - identical API
ferret_db = MongoClient("mongodb://user:pass@ferretdb-host:27017/")

# All queries, aggregations, updates work identically
```

### Migration Steps
1. **Set up FerretDB** with PostgreSQL backend
2. **Export** data from MongoDB: `mongoexport`
3. **Import** to FerretDB: `mongoimport` (same tools!)
4. **Update connection string** only
5. **Test** - everything should work identically

## ⚠️ Limitations

### Current FerretDB Limitations (v1.x)
- **Transactions**: Single-document only (PostgreSQL limitation)
- **GridFS**: Not yet supported
- **Some aggregation operators**: Limited set available
- **Change streams**: Not supported

### When to Use MongoDB Atlas Instead
- **Heavy aggregation pipelines** with complex operators
- **GridFS** file storage requirements
- **Multi-document transactions** critical
- **Managed scaling** without ops overhead preferred

## 🎯 Recommendation

**For AnaJobs Use Case**: FerretDB is perfect because:
- ✅ **Simple document storage** (job board data)
- ✅ **Text search** queries work great  
- ✅ **Cost-sensitive** project benefits from savings
- ✅ **Same MongoDB ecosystem** tools and drivers
- ✅ **PostgreSQL reliability** for production data

**Setup Priority**: Start with FerretDB for 50-70% cost savings while keeping identical MongoDB development experience.

## 📚 Additional Resources

- [FerretDB Documentation](https://docs.ferretdb.io/)
- [MongoDB to FerretDB Migration Guide](https://docs.ferretdb.io/migration/)
- [PostgreSQL Hosting Comparison](https://www.postgresql.org/support/professional_hosting/)
- [FerretDB Performance Benchmarks](https://www.ferretdb.io/blog/ferretdb-performance-benchmark/)