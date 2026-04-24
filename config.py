"""Configuration management for RAG application"""

import os
import ssl
from dataclasses import dataclass
from typing import Optional

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning


@dataclass
class Config:
    """Application configuration"""
    csv_path: str
    rules_path: str
    question: str
    token_url: str
    chat_url: str
    client_id: str
    client_secret: str
    model: str = 'gpt-4o'
    persist_dir: str = './chromadb_store'
    csv_limit: int = 8
    output_path: Optional[str] = None
    
    @classmethod
    def from_args(cls, args):
        """Create config from command line arguments"""
        # Setup SSL disabling
        cls._setup_ssl_disabling()
        
        return cls(
            csv_path=args.csv,
            rules_path=args.rules,
            question=args.question,
            token_url=args.token_url,
            chat_url=args.chat_url,
            client_id=args.client_id,
            client_secret=args.client_secret,
            model=args.model,
            persist_dir=args.persist_dir,
            csv_limit=args.csv_limit,
            output_path=args.output
        )
    
    @staticmethod
    def _setup_ssl_disabling():
        """Configure SSL disabling for development"""
        ssl._create_default_https_context = ssl._create_unverified_context
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        os.environ['ANONYMIZED_TELEMETRY'] = 'FALSE'
        print("SSL certificate verification disabled")


