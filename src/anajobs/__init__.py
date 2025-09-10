"""
AnaJobs - Non-Profit Job Site Data Management System
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .database import NonProfitJobSiteDB
from .extractor import WebExtractor, extract_organization_text

# Optional Supabase support
try:
    from .supabase_db import SupabaseJobSiteDB, load_organizations_to_supabase, compare_databases
    __all__ = ["NonProfitJobSiteDB", "WebExtractor", "extract_organization_text", 
               "SupabaseJobSiteDB", "load_organizations_to_supabase", "compare_databases"]
except ImportError:
    # Supabase dependencies not installed
    __all__ = ["NonProfitJobSiteDB", "WebExtractor", "extract_organization_text"]