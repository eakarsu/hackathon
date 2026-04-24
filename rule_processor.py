"""Business rules processing and rephrasing"""

import logging

logger = logging.getLogger(__name__)


class RuleProcessor:
    """Handles business rules processing and AI rephrasing"""
    
    def __init__(self, config):
        self.config = config
    
    def process_rules(self, rules_path: str, ai_client) -> str:
        """Read and rephrase business rules"""
        logger.info("Processing business rules...")
        
        # Read entire rules file
        original_rules = self._read_rules_file(rules_path)
        
        # Rephrase rules using AI
        rephrased_rules = self._rephrase_rules(original_rules, ai_client)
        
        return rephrased_rules
    
    def _read_rules_file(self, rules_path: str) -> str:
        """Read the entire rules file"""
        try:
            with open(rules_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            logger.info(f"Read {len(content)} characters from rules file")
            return content
        
        except Exception as e:
            logger.error(f"Failed to read rules file: {e}")
            return "No business rules available."
    
    def _rephrase_rules(self, original_rules: str, ai_client) -> str:
        """Use AI to rephrase and summarize rules"""
        logger.info("Rephrasing rules with AI...")
        
        rephrase_prompt = [
            {
                "role": "system",
                "content": "You are a business rules expert. Summarize and rephrase the following business rules into clear, concise instructions."
            },
            {
                "role": "user",
                "content": f"Please create a clear, actionable summary of these business rules:\n\n{original_rules}"
            }
        ]
        
        try:
            response = ai_client.make_api_call(rephrase_prompt)
            if response and 'choices' in response and response['choices']:
                rephrased = response['choices'][0]['message']['content']
                logger.info(f"Rules rephrased: {len(rephrased)} characters")
                return rephrased
            else:
                logger.warning("Rule rephrasing failed, using original")
                return original_rules
        
        except Exception as e:
            logger.error(f"Rule rephrasing error: {e}")
            return original_rules


