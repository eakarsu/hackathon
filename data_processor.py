"""Data processing utilities for CSV and text files"""

import gc
import logging
from typing import List

import pandas as pd
import json 

logger = logging.getLogger(__name__)


class DataProcessor:
    """Handles CSV and text file processing"""
    
    def __init__(self, config):
        self.config = config
    
    def process_csv(self, csv_path: str, limit: int) -> List[str]:
        """Process CSV file and return document strings"""
        logger.info(f"Processing CSV: {csv_path} (limit: {limit})")
        
        documents = []
        count = 0
        
        try:
            for chunk in pd.read_csv(csv_path, chunksize=3):
                for _, row in chunk.iterrows():
                    if count >= limit:
                        break
                    
                    # Create document from row
                    doc_parts = []
                    for col, val in row.items():
                        if pd.notna(val):
                            part = f"{col}: {str(val)[:80]}"
                            doc_parts.append(part)
                    
                    if doc_parts:
                        document = " | ".join(doc_parts)
                        documents.append(document)
                        count += 1
                
                if count >= limit:
                    break
                
                # Clean up memory
                del chunk
                gc.collect()
        
        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            raise
        
        logger.info(f"Processed {len(documents)} CSV documents")
        return documents
    
    

    def process_json(self, json_path: str, limit: int) -> List[str]:
        """Process JSON with enhanced detail extraction"""
        logger.info(f"Processing JSON: {json_path} (limit: {limit})")
        
        documents = []
        count = 0
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            if isinstance(json_data, list):
                json_records = json_data[:limit]
            else:
                json_records = [json_data]
            
            for record in json_records:
                if count >= limit:
                    break
                    
                # Extract comprehensive document with key details
                doc_content = self._build_comprehensive_document(record)
                
                if doc_content:
                    documents.append(doc_content)
                    count += 1
            
        except Exception as e:
            logger.error(f"Error processing JSON: {e}")
            return []
    
        logger.info(f"Processed {len(documents)} JSON documents")
        return documents 

    def _build_comprehensive_document(self, record):
        """Build comprehensive document with all important details preserved"""
        
        parts = []
        
        # === CORE IDENTIFIERS ===
        if '_id' in record:
            parts.append(f"LEAD_ID: {record['_id']}")
        
        if 'externalSource' in record:
            parts.append(f"SOURCE: {record['externalSource']}")
        
        if 'externalLeadId' in record:
            parts.append(f"EXTERNAL_ID: {record['externalLeadId']}")
        
        # === STORE INFORMATION (CRITICAL) ===
        if 'store' in record:
            store = record['store']
            if 'storeNumber' in store:
                parts.append(f"STORE_NUMBER: {store['storeNumber']}")
            if 'storeName' in store:
                parts.append(f"STORE_NAME: {store['storeName']}")
            if 'address' in store:
                parts.append(f"STORE_ADDRESS: {store['address']}")
            if 'city' in store and 'state' in store:
                parts.append(f"STORE_LOCATION: {store['city']}, {store['state']}")
            if 'division' in store:
                parts.append(f"DIVISION: {store['division']}")
            if 'region' in store:
                parts.append(f"REGION: {store['region']}")
            if 'district' in store:
                parts.append(f"DISTRICT: {store['district']}")
        
        # === LEAD STATUS & PRIORITY ===
        if 'leadStatus' in record:
            parts.append(f"STATUS: {record['leadStatus']}")
        
        if 'sellingChannel' in record:
            parts.append(f"CHANNEL: {record['sellingChannel']}")
        
        if 'sourceType' in record:
            parts.append(f"SOURCE_TYPE: {record['sourceType']}")
        
        # === CUSTOMER INFORMATION ===
        if 'customer' in record:
            customer = record['customer']
            if 'firstName' in customer and 'lastName' in customer:
                parts.append(f"CUSTOMER: {customer['firstName']} {customer['lastName']}")
            
            # Customer contact info (encoded but useful for AI context)
            if 'contactInformation' in customer:
                contact = customer['contactInformation']
                if 'emailAddress' in contact:
                    parts.append(f"EMAIL_PROVIDED: Yes")
                if 'mobilePhoneNumber' in contact:
                    parts.append(f"PHONE_PROVIDED: Yes")
                if 'timeZone' in contact:
                    parts.append(f"CUSTOMER_TIMEZONE: {contact['timeZone']}")
            
            # Customer address
            if 'address' in customer:
                addr = customer['address']
                if 'city' in addr and 'state' in addr:
                    parts.append(f"CUSTOMER_LOCATION: {addr.get('city', 'Unknown')}, {addr.get('state', 'Unknown')}")
        
        # === PROJECT DETAILS ===
        if 'categoryDetails' in record:
            cat = record['categoryDetails']
            if 'department' in cat:
                parts.append(f"DEPARTMENT: {cat['department']}")
            if 'category' in cat:
                parts.append(f"CATEGORY: {cat['category']}")
            if 'categoryType' in cat:
                parts.append(f"CATEGORY_TYPE: {cat['categoryType']}")
            if 'description' in cat:
                parts.append(f"PROJECT_DESCRIPTION: {cat['description']}")
            if 'subCategories' in cat and cat['subCategories']:
                parts.append(f"SUBCATEGORIES: {', '.join(cat['subCategories'])}")
        
        if 'leadDetails' in record:
            lead = record['leadDetails']
            if 'timeFrame' in lead:
                parts.append(f"TIMEFRAME: {lead['timeFrame']}")
            if 'budgetRange' in lead:
                parts.append(f"BUDGET: {lead['budgetRange']}")
            if 'propertyType' in lead:
                parts.append(f"PROPERTY_TYPE: {lead['propertyType']}")
            if 'leadType' in lead:
                parts.append(f"LEAD_TYPE: {lead['leadType']}")
            if 'projectDetails' in lead:
                parts.append(f"PROJECT_DETAILS: {lead['projectDetails']}")
            if 'upgrades' in lead and lead['upgrades']:
                parts.append(f"UPGRADES: {', '.join(lead['upgrades'])}")
        
        # === APPOINTMENT & SCHEDULING ===
        if 'leadAppointmentType' in record:
            parts.append(f"APPOINTMENT_TYPE: {record['leadAppointmentType']}")
        
        if 'followUpDate' in record:
            parts.append(f"FOLLOW_UP_DATE: {record['followUpDate']}")
        
        if 'schedule' in record and 'appointmentDate' in record['schedule']:
            parts.append(f"APPOINTMENT_DATE: {record['schedule']['appointmentDate']}")
        
        # === DATES (FOR URGENCY CALCULATION) ===
        if 'createdDateTime' in record:
            created = record['createdDateTime']
            if isinstance(created, dict) and '$date' in created:
                parts.append(f"CREATED: {created['$date']}")
            else:
                parts.append(f"CREATED: {created}")
        
        if 'lastModifiedDateTime' in record:
            modified = record['lastModifiedDateTime']
            if isinstance(modified, dict) and '$date' in modified:
                parts.append(f"LAST_MODIFIED: {modified['$date']}")
            else:
                parts.append(f"LAST_MODIFIED: {modified}")
        
        # === ASSOCIATE INFORMATION ===
        if 'associate' in record:
            assoc = record['associate']
            if 'assignedTo' in assoc:
                assigned = assoc['assignedTo']
                if 'firstName' in assigned and 'lastName' in assigned:
                    parts.append(f"ASSIGNED_TO: {assigned['firstName']} {assigned['lastName']}")
            
            if 'createdBy' in assoc:
                created_by = assoc['createdBy']
                if 'firstName' in created_by and 'lastName' in created_by:
                    parts.append(f"CREATED_BY: {created_by['firstName']} {created_by['lastName']}")
        
        # === ADDITIONAL CONTEXT ===
        if 'custType' in record:
            parts.append(f"CUSTOMER_TYPE: {record['custType']}")
        
        if 'referralId' in record and record['referralId']:
            parts.append(f"REFERRAL_ID: {record['referralId']}")
        
        return " | ".join(parts)


