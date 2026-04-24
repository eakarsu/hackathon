#!/usr/bin/env python3
"""
Enhanced RAG Application with Rule Rephrasing
Clean architecture with separated concerns
"""

import argparse
import logging
from pathlib import Path

from config import Config
from data_processor import DataProcessor
from vector_store import VectorStore
from rule_processor import RuleProcessor
from ai_client import AIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Main application entry point"""
    args = parse_arguments()
    
    try:
        # Initialize components
        config = Config.from_args(args)
        data_processor = DataProcessor(config)
        vector_store = VectorStore(config)
        rule_processor = RuleProcessor(config)
        ai_client = AIClient(config)
        
        logger.info("🚀 Starting Enhanced RAG Application")
        
        # Process data
        #csv_documents = data_processor.process_csv(args.csv, args.csv_limit)
        #logger.info(f"📄 Processed {len(csv_documents)} CSV documents")
        
        json_documents = data_processor.process_json(args.json, args.json_limit)
        logger.info(f"📄 Processed {len(json_documents)} json documents")
        

        # Process and rephrase rules
        rephrased_rules = rule_processor.process_rules(args.rules, ai_client)
        logger.info(f"📋 Rules processed and rephrased")
        
        # Setup vector store and index documents
        vector_store.index_documents(json_documents)
        logger.info("📚 Documents indexed in vector store")
        
        # Retrieve relevant context
        context_docs = vector_store.query(args.question, n_results=3)
        logger.info(f"🔍 Found {len(context_docs)} relevant documents")
        
        # Generate final answer
        answer = ai_client.generate_answer(
            question=args.question,
            context=context_docs,
            rules=rephrased_rules
        )
        
        # Display results
        display_results(args.question, context_docs, rephrased_rules, answer)
        
        # Save output if requested
        if args.output:
            save_output(args.output, args.question, context_docs, rephrased_rules, answer)
        
        logger.info("🎉 RAG application completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Application error: {e}")
        raise


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Enhanced RAG Application")
    parser.add_argument('--csv', default="a.bar", help='CSV file path')
    parser.add_argument('--rules', required=True, help='Rules file path')
    parser.add_argument('--question', required=True, help='Question to ask')
    parser.add_argument('--token-url', required=True, help='OAuth token URL')
    parser.add_argument('--chat-url', required=True, help='Chat API URL')
    parser.add_argument('--client-id', required=True, help='OAuth client ID')
    parser.add_argument('--client-secret', required=True, help='OAuth client secret')
    parser.add_argument('--model', default='gpt-4o', help='AI model to use')
    parser.add_argument('--persist-dir', default='./chromadb_store', help='Vector store directory')
    parser.add_argument('--csv-limit', type=int, default=8, help='Max CSV documents to process')
    parser.add_argument('--output', help='Output JSON file path')
    parser.add_argument('--json', required=True, help='JSON file path')
    parser.add_argument('--json-limit', type=int, default=8, help='Max JSON documents')

    return parser.parse_args()


def display_results(question, context_docs, rules, answer):
    """Display formatted results"""
    print("\n" + "="*60)
    print("🎯 RAG RESULTS")
    print("="*60)
    print(f"❓ Question: {question}")
    print(f"\n📋 Rules Applied: {len(rules)} characters")
    print(f"\n📊 Context Used:")
    for i, doc in enumerate(context_docs, 1):
        print(f"  {i}. {doc[:100]}...")
    print(f"\n🤖 AI Answer:\n{answer}")
    print("="*60)


def save_output(output_path, question, context, rules, answer):
    """Save results to JSON file"""
    import json
    import time
    
    output_data = {
        "question": question,
        "context": context,
        "rephrased_rules": rules,
        "answer": answer,
        "timestamp": time.time()
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    logger.info(f"💾 Results saved to: {output_path}")


if __name__ == "__main__":
    main()


