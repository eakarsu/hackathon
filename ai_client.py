"""AI API client for OAuth and chat completions"""

import logging
import os
from typing import List, Dict, Any

import requests

logger = logging.getLogger(__name__)


class AIClient:
    """Handles AI API authentication and chat completions"""
    
    def __init__(self, config):
        self.config = config
        self.token = None
        self.verify = os.getenv("AI_CA_BUNDLE") or True
        self._authenticate()
    
    def _authenticate(self):
        """Get OAuth access token"""
        logger.info("Getting AI access token...")
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(
                self.config.token_url,
                headers=headers,
                data=payload,
                verify=self.verify,
                timeout=20,
            )
            response.raise_for_status()
            self.token = response.json()["access_token"]
            logger.info("Access token obtained")
        
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def make_api_call(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Make API call to chat completion endpoint"""
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False
        }
        logger.info("Calling AI API with %d messages", len(messages))
        try:
            response = requests.post(
                self.config.chat_url,
                headers=headers,
                json=payload,
                verify=self.verify,
                timeout=60,
            )
            response.raise_for_status()
            logger.info("AI API response received")
            return response.json()
        
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            raise
    
    
    def generate_answer(self, question: str, context: List[str], rules: str) -> str:
    
        context_str = "\n\n".join([f"Lead {i+1}:\n{doc}" for i, doc in enumerate(context)])
        
        messages = [
            {
                "role": "system",
                "content": f"""You are a lead intelligence assistant for Lowe's stores. Follow these business guidelines:

    {rules}

    CRITICAL INSTRUCTIONS:
    - Provide specific lead IDs for each recommendation
    - Prioritize by urgency (OVERDUE first, then DUE)
    - Give detailed actionable steps for each lead
    - Focus only on the store data provided below"""
            },
            {
                "role": "user",
                "content": f"""Store Lead Data:
    {context_str}

    Question: {question}

    Provide a detailed response with:
    1. Specific lead IDs to work on
    2. Priority order (most urgent first)
    3. Exact actions to take for each lead
    4. Customer names and project details where available"""
            }
        ]
        
        response = self.make_api_call(messages)
        if 'choices' in response and response['choices']:
            return response['choices'][0]['message']['content']
        else:
            raise Exception("No valid AI response received")

