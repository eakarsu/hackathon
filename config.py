"""Configuration management for RAG application"""

import os
from dataclasses import dataclass
from typing import Optional

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
        os.environ['ANONYMIZED_TELEMETRY'] = 'FALSE'
        
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
    
