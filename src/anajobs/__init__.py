"""
AnaJobs - Non-Profit Job Site Data Management System
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .database import NonProfitJobSiteDB
from .extractor import WebExtractor, extract_organization_text

__all__ = ["NonProfitJobSiteDB", "WebExtractor", "extract_organization_text"]