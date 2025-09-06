# AnaJobs - Non-Profit Job Site Data Management System

A Python application for managing and processing job site data from non-profit organizations. This system parses corrupted JSONL files, cleans the data, and stores it in MongoDB for efficient querying and management.

## Features

- 🔧 **Data Processing**: Parses corrupted JSONL files and extracts organization data
- 🗄️ **MongoDB Integration**: Stores and manages organization data with proper indexing
- 🔍 **Search & Query**: Advanced search capabilities for organizations
- 🖥️ **CLI Interface**: Command-line tools for easy data management
- 🧪 **Testing**: Comprehensive test suite with pytest
- 📊 **Statistics**: Database statistics and reporting
- ⚙️ **Configuration**: Flexible configuration management

## Quick Start

### Prerequisites

- Python 3.8+
- MongoDB (local or remote)
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Emery999/anajobs.git
   cd anajobs
   ```

2. **Quick setup (recommended):**
   ```bash
   ./scripts/setup_dev.sh    # On Unix/macOS
   # or
   scripts\setup_dev.bat     # On Windows
   ```

3. **Manual setup (alternative):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```

4. **Activate environment:**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   # or use the convenience script:
   source activate.sh
   ```

5. **Set up MongoDB:**
   - Install MongoDB locally or use a cloud service
   - Ensure MongoDB is running on `mongodb://localhost:27017/` (default)

### Basic Usage

There are three ways to run anajobs commands:

#### Option 1: Using the convenience script (recommended)
```bash
# No activation needed - script handles it automatically
./scripts/run.sh setup
./scripts/run.sh test
./scripts/run.sh search "environmental"
./scripts/run.sh stats
```

#### Option 2: Activate environment first, then use anajobs command
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
# or: source activate.sh

anajobs setup
anajobs test
anajobs search "environmental"
anajobs stats
```

#### Option 3: Direct Python execution (if venv is activated)
```bash
source venv/bin/activate
python -m anajobs.cli setup
python -m anajobs.cli test
```

### Commands

1. **Set up database and load data:**
   ```bash
   ./scripts/run.sh setup
   # or with custom data file:
   ./scripts/run.sh setup --data-file path/to/your/data.jsonl
   ```

2. **Test database connection:**
   ```bash
   ./scripts/run.sh test
   ```

3. **Search organizations:**
   ```bash
   ./scripts/run.sh search "environmental"
   ./scripts/run.sh search "red cross" --limit 5
   ```

4. **View statistics:**
   ```bash
   ./scripts/run.sh stats
   ```

## Project Structure

```
anajobs/
├── src/anajobs/           # Main package
│   ├── __init__.py        # Package initialization
│   ├── cli.py            # Command-line interface
│   ├── config.py         # Configuration management
│   └── database.py       # MongoDB operations
├── tests/                # Test suite
│   ├── __init__.py
│   ├── test_database.py
│   └── test_config.py
├── data/                 # Data files
│   └── publicserviceopenings.jsonl
├── config/              # Configuration files
│   └── config.json
├── scripts/             # Utility scripts
├── logs/               # Log files (created at runtime)
├── requirements.txt    # Dependencies
├── pyproject.toml     # Project configuration
├── .gitignore        # Git ignore rules
└── README.md         # This file
```

## Configuration

### Environment Variables

Set these environment variables to override default configuration:

```bash
export ANAJOBS_MONGODB_URI="mongodb://localhost:27017/"
export ANAJOBS_DATABASE_NAME="nonprofit_jobs"
export ANAJOBS_DATA_FILE="data/publicserviceopenings.jsonl"
export ANAJOBS_LOG_LEVEL="INFO"
```

### Configuration File

Edit `config/config.json`:

```json
{
  "mongodb_uri": "mongodb://localhost:27017/",
  "database_name": "nonprofit_jobs",
  "collection_name": "organizations",
  "data_file": "data/publicserviceopenings.jsonl",
  "log_level": "INFO",
  "log_file": "logs/anajobs.log"
}
```

## API Usage

### Python API

```python
from anajobs import NonProfitJobSiteDB

# Initialize database connection
db = NonProfitJobSiteDB("mongodb://localhost:27017/", "nonprofit_jobs")

# Connect
if db.connect():
    # Search for organizations
    results = db.search_organizations("environmental", limit=5)
    
    # Get organizations by domain
    org_domains = db.get_organizations_by_domain(".org")
    
    # Test database
    test_results = db.test_database()
    
    # Close connection
    db.close_connection()
```

### Direct MongoDB Access

```python
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['nonprofit_jobs']
collection = db['organizations']

# Find specific organization
org = collection.find_one({"name": "American Red Cross"})
print(f"Jobs URL: {org['jobs']}")

# Find all environmental organizations
env_orgs = collection.find({"name": {"$regex": "environment", "$options": "i"}})
for org in env_orgs:
    print(f"{org['name']}: {org['jobs']}")

# Update scraped status
collection.update_one(
    {"name": "American Red Cross"}, 
    {"$set": {"scraped": True, "last_scraped": "2024-03-20"}}
)
```

## Development

### Setting up for Development

1. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Set up pre-commit hooks:**
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/anajobs --cov-report=html

# Run specific test file
pytest tests/test_database.py

# Run with verbose output
pytest -v
```

### Code Formatting

```bash
# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Check code style with flake8
flake8 src/ tests/
```

## Data Format

The system processes JSONL files containing organization data. Each line should contain:

```json
{"name":"Organization Name","root":"https://example.org","jobs":"https://example.org/jobs"}
```

The parser can handle corrupted files with malformed JSON and extracts:
- Organization name
- Root website URL
- Jobs page URL

## Database Schema

### Organizations Collection

```javascript
{
  "_id": ObjectId("..."),
  "name": "Organization Name",        // Unique index
  "root": "https://example.org",      // Root website URL
  "jobs": "https://example.org/jobs", // Jobs page URL  
  "status": "active",                 // Organization status
  "scraped": false,                   // Whether jobs have been scraped
  "last_scraped": "2024-03-20",      // Last scrape date (optional)
  "created_at": "2024-03-20T10:00:00Z" // Creation timestamp (optional)
}
```

## Logging

Logs are written to both console and file (`logs/anajobs.log`). Configure log level via:

- Environment variable: `ANAJOBS_LOG_LEVEL`
- Config file: `"log_level": "INFO"`

Available levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run tests: `pytest`
5. Format code: `black src/ tests/`
6. Commit changes: `git commit -am 'Add new feature'`
7. Push to branch: `git push origin feature-name`
8. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   ```bash
   # Check if MongoDB is running
   sudo systemctl status mongod
   # Or start MongoDB
   sudo systemctl start mongod
   ```

2. **Import Errors**
   ```bash
   # Install in development mode
   pip install -e .
   ```

3. **Permission Errors on macOS/Linux**
   ```bash
   # Ensure proper permissions
   chmod +x scripts/*.sh
   ```

4. **PyMongo Not Found**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   ```

### Getting Help

- Check the [Issues](https://github.com/Emery999/anajobs/issues) page
- Review the logs in `logs/anajobs.log`
- Run with debug logging: `ANAJOBS_LOG_LEVEL=DEBUG python -m anajobs.cli test`