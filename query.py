#!/usr/bin/env python3

import argparse
import logging
import os
import ssl
import json
from typing import List

# SSL disabling (EXACT same as your working version)
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['ANONYMIZED_TELEMETRY'] = 'FALSE'

import requests
requests.packages.urllib3.disable_warnings()

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("search_ai_app")


def get_access_token(client_id, client_secret, token_url):
    """Get OAuth access token"""
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(token_url, headers=headers, data=payload, verify=False)
    response.raise_for_status()
    return response.json()["access_token"]


def call_ai_api(messages, token, chat_url, model):
    """Make API call to AI"""
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    
    response = requests.post(chat_url, headers=headers, json=payload, verify=False)
    response.raise_for_status()
    return response.json()


def read_and_rephrase_rules(rules_file, token, chat_url, model):
    """Read rules file and get AI to rephrase it"""
    
    # STEP 1: Read entire rules file
    logger.info(f"📖 Reading rules file: {rules_file}")
    try:
        with open(rules_file, 'r', encoding='utf-8', errors='ignore') as f:
            original_rules = f.read()
        logger.info(f"✅ Read {len(original_rules)} characters from rules file")
    except Exception as e:
        logger.error(f"❌ Failed to read rules file: {e}")
        return "No business rules available."
    
    # STEP 2: Send to AI for rephrasing
    logger.info("🔄 Sending rules to AI for rephrasing...")
    
    rephrase_messages = [
    {
        "role": "system",
        "content": "You are a business rules expert. Summarize the business rules into clear instructions. Remove any specific file names or data source references since the actual data source may be different."
    },
    {
        "role": "user",
        "content": f"""Please create a clear, actionable summary of these business rules, removing specific file references:

    {original_rules}

    Focus on the business logic and actions, not the data source details."""
        }
    ]
    # Debug: Show what we're sending to AI for rephrasing
    print("\n" + "="*80)
    print("🔍 DEBUG: REPHRASING RULES WITH AI")
    print("="*80)
    print(f"Original rules length: {len(original_rules)} characters")
    print("Sending to AI for rephrasing...")
    print("="*80)
    
    try:
        response = call_ai_api(rephrase_messages, token, chat_url, model)
        
        if 'choices' in response and response['choices']:
            rephrased_rules = response['choices'][0]['message']['content']
            logger.info(f"✅ Rules rephrased: {len(rephrased_rules)} characters")
            
            print(f"Rephrased rules length: {len(rephrased_rules)} characters")
            print("="*80)
            
            return rephrased_rules
        else:
            logger.warning("⚠️ Rule rephrasing failed, using original")
            return original_rules
    
    except Exception as e:
        logger.error(f"❌ Rule rephrasing error: {e}")
        return original_rules


def search_chromadb(query: str, persist_dir: str, collection_name: str, top_k: int = 3) -> List[str]:
    """Search ChromaDB and return relevant documents"""
    
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Use YOUR local model
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="./model_cache/all-MiniLM-L6-v2"
    )
    
    # Get your existing collection
    collection = client.get_collection(name=collection_name)
    
    # Search ChromaDB
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    result = results['documents'][0] if results['documents'] else []
    logger.info(f"🔎 Found {result} relevant documents for query: {query}")
    return result 


def call_ai_with_context_and_rules(question: str, context_docs: List[str], rephrased_rules: str, token: str, chat_url: str, model: str):
    """Send ChromaDB context + rephrased rules to AI"""
    
    # Build context from ChromaDB results
    context = "\n\n".join([f"Data {i+1}:\n{doc}" for i, doc in enumerate(context_docs)]) if context_docs else "No relevant data found."
    
    # Create messages with rephrased rules + ChromaDB context
    messages = [
        {
            "role": "system", 
            "content": f"""You are a lead intelligence assistant. Follow these business guidelines:

{rephrased_rules}

Use the provided data context to answer questions according to these guidelines."""
        },
        {
            "role": "user", 
            "content": f"""Data Context:
{context}

Question: {question}

Please answer based on the data context above, following the business guidelines."""
        }
    ]
    
    # Debug: Print what we're sending to AI
    print("\n" + "="*80)
    print("🔍 DEBUG: FINAL AI CALL WITH CHROMADB + REPHRASED RULES")
    print("="*80)
    print("SYSTEM MESSAGE (Rephrased Rules):")
    print("-" * 40)
    print(messages[0]['content'][:500] + "...")
    print("\nUSER MESSAGE (ChromaDB Context):")
    print("-" * 40)
    print(messages[1]['content'][:500] + "...")
    print("="*80)
    
    # Call AI API
    return call_ai_api(messages, token, chat_url, model)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--query', required=True, help='Search query')
    parser.add_argument('--rules', required=True, help='Rules file path')
    parser.add_argument('--persist-dir', default='./chromadb_store', help='ChromaDB directory')
    parser.add_argument('--collection-name', default='json_data_store', help='Collection name')
    parser.add_argument('--token-url', required=True, help='OAuth token URL')
    parser.add_argument('--chat-url', required=True, help='Chat API URL')
    parser.add_argument('--client-id', required=True, help='OAuth client ID')
    parser.add_argument('--client-secret', required=True, help='OAuth client secret')
    parser.add_argument('--model', default='gpt-4o', help='AI model')
    parser.add_argument('--top-k', type=int, default=300, help='Number of ChromaDB results')
    
    args = parser.parse_args()
    
    try:
        logger.info(f"🚀 Starting complete workflow: Rules Rephrasing → ChromaDB Search → AI Answer")
        
        # STEP 1: Get AI access token
        logger.info("🔑 Getting access token...")
        token = get_access_token(args.client_id, args.client_secret, args.token_url)
        
        # STEP 2: Read rules file and get AI to rephrase it
        rephrased_rules = read_and_rephrase_rules(args.rules, token, args.chat_url, args.model)
        
        # STEP 3: Search ChromaDB for relevant documents
        logger.info(f"🔍 Searching ChromaDB: '{args.query}'")
        context_docs = search_chromadb(args.query, args.persist_dir, args.collection_name, args.top_k)
        logger.info(f"📊 Found {len(context_docs)} relevant documents")
        
        # STEP 4: Send ChromaDB results + rephrased rules to AI for final answer
        logger.info("🤖 Calling AI with ChromaDB context + rephrased rules...")
        ai_response = call_ai_with_context_and_rules(
            args.query, 
            context_docs, 
            rephrased_rules, 
            token, 
            args.chat_url, 
            args.model
        )
        
        # STEP 5: Display results
        if 'choices' in ai_response and ai_response['choices']:
            answer = ai_response['choices'][0]['message']['content']
            
            print("\n" + "="*60)
            print("🎯 COMPLETE RAG WORKFLOW RESULTS")
            print("="*60)
            print(f"❓ Question: {args.query}")
            print(f"📋 Rules File: {args.rules}")
            print(f"📊 ChromaDB Context Used:")
            for i, doc in enumerate(context_docs, 1):
                print(f"  {i}. {doc[:100]}...")
            print(f"🔄 Used AI-rephrased rules: {len(rephrased_rules)} characters")
            print(f"\n🤖 AI Answer:\n{answer}")
            print("="*60)
        else:
            print("❌ No valid AI response received")
        
        logger.info("🎉 Complete RAG workflow completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
