# TLS verification uses the Python/requests defaults. For an internal CA,
# configure REQUESTS_CA_BUNDLE or SSL_CERT_FILE instead of disabling checks.

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import json
from datetime import datetime
import re
import logging
from pathlib import Path

# Add parent directory to path to import RAG modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import RAG modules, but handle gracefully if they fail
try:
    from config import Config
    from data_processor import DataProcessor
    from vector_store import VectorStore
    from rule_processor import RuleProcessor
    from ai_client import AIClient
    RAG_AVAILABLE = True
    print("✅ RAG modules loaded successfully")
except ImportError as e:
    print(f"⚠️ RAG modules not available: {e}")
    RAG_AVAILABLE = False

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
    print("✅ ChromaDB available")
except ImportError as e:
    print(f"⚠️ ChromaDB not available: {e}")
    CHROMADB_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024
allowed_origins = [
    origin.strip()
    for origin in os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    if origin.strip()
]
CORS(
    app,
    origins=allowed_origins,
    methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
    supports_credentials=False,
)

DATA_ROOT = Path(
    os.getenv('DATA_ROOT', Path(__file__).resolve().parent.parent)
).expanduser().resolve()


def resolve_data_file(value: str, expected_suffix: str) -> Path:
    """Resolve a request-supplied data file within the configured data root."""
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = DATA_ROOT / candidate
    candidate = candidate.expanduser().resolve()
    try:
        candidate.relative_to(DATA_ROOT)
    except ValueError as exc:
        raise ValueError('Data path must stay inside DATA_ROOT') from exc
    if candidate.suffix.lower() != expected_suffix:
        raise ValueError(f'Data file must use the {expected_suffix} extension')
    return candidate

class RAGService:
    def __init__(self):
        self.vector_store = None
        self.ai_client = None
        self.rule_processor = None
        self.data_processor = None
        self.rephrased_rules = None
        self.is_initialized = False
        self.rag_available = RAG_AVAILABLE and CHROMADB_AVAILABLE
        
        # Storage for actionable items and their status
        self.actionable_items = []
        self.completed_items = set()
        self.item_creation_timestamps = {}
        self.executed_items = set()
        self.execution_times = {}  # Track time spent on tasks
        self.task_progression = []  # Track order of task execution
        
        if self.rag_available:
            # Check if AI credentials are configured
            self.client_id = os.getenv('AI_CLIENT_ID')
            self.client_secret = os.getenv('AI_CLIENT_SECRET')
            self.token_url = os.getenv('AI_TOKEN_URL')
            self.chat_url = os.getenv('AI_CHAT_URL')
            self.model = os.getenv('AI_MODEL', 'gpt-4o')
            # Use absolute path for ChromaDB to avoid permission issues
            # Check if data exists in project root first (where indexing might have occurred)
            project_root_persist = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'chromadb_store'))
            backend_persist = os.path.abspath('./chromadb_store')
            
            # Use project root directory if it has data, otherwise use backend directory
            if os.path.exists(project_root_persist) and any(f.endswith('.sqlite3') for f in os.listdir(project_root_persist) if os.path.isfile(os.path.join(project_root_persist, f))):
                self.persist_dir = project_root_persist
                logger.info(f"Using existing ChromaDB data from project root: {self.persist_dir}")
            else:
                persist_dir = os.getenv('PERSIST_DIR', './chromadb_store')
                self.persist_dir = os.path.abspath(persist_dir)
                logger.info(f"Using ChromaDB directory: {self.persist_dir}")
            
            # Ensure the directory exists with proper permissions
            os.makedirs(self.persist_dir, mode=0o755, exist_ok=True)
            
            # Fix permissions for any existing files
            try:
                for root, dirs, files in os.walk(self.persist_dir):
                    for directory in dirs:
                        os.chmod(os.path.join(root, directory), 0o755)
                    for file in files:
                        os.chmod(os.path.join(root, file), 0o644)
            except Exception as e:
                logger.warning(f"Could not fix permissions: {e}")
            
            # Restore persisted state only when the external client is configured.
            if all([self.client_id, self.client_secret, self.token_url, self.chat_url]):
                self._check_existing_initialization()
        
    def _check_existing_initialization(self):
        """Check if RAG system was previously initialized by looking for ChromaDB data"""
        try:
            if os.path.exists(self.persist_dir):
                # Look for ChromaDB collection files
                chroma_files = []
                for root, dirs, files in os.walk(self.persist_dir):
                    chroma_files.extend([f for f in files if f.endswith('.sqlite3') or f.endswith('.json')])
                
                if chroma_files:
                    logger.info("Found existing ChromaDB data, attempting to restore RAG system")
                    # Try to initialize components to restore state
                    try:
                        # Create config
                        class SimpleConfig:
                            def __init__(self, client_id, client_secret, token_url, chat_url, model, persist_dir):
                                self.client_id = client_id
                                self.client_secret = client_secret
                                self.token_url = token_url
                                self.chat_url = chat_url
                                self.model = model
                                self.persist_dir = persist_dir
                        
                        config = SimpleConfig(
                            self.client_id, self.client_secret,
                            self.token_url, self.chat_url,
                            self.model, self.persist_dir
                        )
                        
                        # Initialize components
                        self.ai_client = AIClient(config)
                        self.vector_store = VectorStore(config)
                        self.rule_processor = RuleProcessor(config)
                        self.data_processor = DataProcessor(config)
                        
                        # Check if vector store has data by trying to count documents
                        try:
                            # Try to access the collection and count documents
                            collection = self.vector_store.get_collection()
                            if collection and collection.count() > 0:
                                self.is_initialized = True
                                logger.info(f"✅ RAG system restored from existing data ({collection.count()} documents)")
                            else:
                                logger.info("ChromaDB files exist but collection is empty")
                        except Exception as collection_error:
                            logger.warning(f"Could not access ChromaDB collection: {collection_error}")
                            # Try alternative approach - just check if components are loaded
                            if self.vector_store and self.ai_client:
                                self.is_initialized = True
                                logger.info("✅ RAG system components restored (cannot verify data count)")
                        
                    except Exception as e:
                        logger.warning(f"Could not restore RAG system: {e}")
        except Exception as e:
            logger.warning(f"Error checking existing initialization: {e}")
    
    def initialize(self):
        """Initialize RAG components"""
        if not self.rag_available:
            return {"status": "rag_not_available", "error": "RAG dependencies not installed"}

        if not all([self.client_id, self.client_secret, self.token_url, self.chat_url]):
            return {
                "status": "configuration_error",
                "error": "AI client credentials and endpoints must be configured",
            }
            
        if self.is_initialized:
            return {"status": "already_initialized"}
            
        try:
            # Create config
            class SimpleConfig:
                def __init__(self, client_id, client_secret, token_url, chat_url, model, persist_dir):
                    self.client_id = client_id
                    self.client_secret = client_secret
                    self.token_url = token_url
                    self.chat_url = chat_url
                    self.model = model
                    self.persist_dir = persist_dir
            
            config = SimpleConfig(
                self.client_id, self.client_secret, 
                self.token_url, self.chat_url,
                self.model, self.persist_dir
            )
            
            # Initialize components
            self.ai_client = AIClient(config)
            self.vector_store = VectorStore(config)
            self.rule_processor = RuleProcessor(config)
            self.data_processor = DataProcessor(config)
            
            self.is_initialized = True
            logger.info("RAG Service initialized successfully")
            return {"status": "initialized"}
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            return {"status": "error", "error": str(e)}
    
    def index_data(self, json_path: str, rules_path: str, json_limit: int = 4000):
        """Index JSON data into vector store"""
        if not self.rag_available:
            return {"status": "error", "error": "RAG system not available"}
            
        if not self.is_initialized:
            init_result = self.initialize()
            if init_result.get("status") != "initialized" and init_result.get("status") != "already_initialized":
                return init_result
        
        try:
            # Process JSON documents
            json_documents = self.data_processor.process_json(json_path, json_limit)
            logger.info(f"Processed {len(json_documents)} JSON documents")
            
            # Process and rephrase rules
            self.rephrased_rules = self.rule_processor.process_rules(rules_path, self.ai_client)
            logger.info("Rules processed and rephrased")
            
            # Index documents in vector store
            self.vector_store.index_documents(json_documents)
            logger.info("Documents indexed in vector store")
            
            return {
                "status": "success",
                "documents_indexed": len(json_documents),
                "rules_processed": len(self.rephrased_rules) if self.rephrased_rules else 0
            }
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def search(self, query: str, rules_path: str = None, top_k: int = 300):
        """Search vector store and get AI response"""
        if not self.rag_available:
            return {"status": "error", "error": "RAG system not available"}
            
        if not self.is_initialized:
            init_result = self.initialize()
            if init_result.get("status") != "initialized" and init_result.get("status") != "already_initialized":
                return init_result
        
        try:
            # If rules_path provided and no rephrased rules, process them
            if rules_path and not self.rephrased_rules:
                self.rephrased_rules = self.rule_processor.process_rules(rules_path, self.ai_client)
            
            # Query vector store for relevant documents
            context_docs = self.vector_store.query(query, n_results=top_k)
            logger.info(f"Found {len(context_docs)} relevant documents")
            
            # Generate AI answer with context
            answer = self.ai_client.generate_answer(
                question=query,
                context=context_docs,
                rules=self.rephrased_rules or "Provide helpful recommendations based on the context."
            )
            
            return {
                "answer": answer,
                "context_docs_count": len(context_docs),
                "context_preview": context_docs[:3] if context_docs else []
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def parse_ai_response_to_actionable_items(self, ai_response: str, query: str) -> List[Dict[str, Any]]:
        """Parse AI response text into structured actionable items"""
        lines = ai_response.split('\n')
        actionable_items = []
        current_item = None
        item_id = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for numbered items or bullet points
            if re.match(r'^(\d+\.|\-|\•|\*)', line):
                if current_item:
                    actionable_items.append(current_item)
                
                # Extract title and description
                title_text = re.sub(r'^(\d+\.|\-|\•|\*)\s*', '', line)
                title = title_text[:60] if len(title_text) > 60 else title_text
                
                current_item = {
                    "id": str(item_id),
                    "title": title,
                    "description": line,
                    "priority": self.determine_priority(line),
                    "category": self.determine_category(line),
                    "estimated_time": self.estimate_time(line),
                    "impact": self.determine_impact(line)
                }
                item_id += 1
            elif current_item and not line.startswith(('STATUS:', 'STORE:', 'LEAD_ID:', 'CUSTOMER:')):
                # Add to description if we're building an item
                current_item["description"] += " " + line
        
        if current_item:
            actionable_items.append(current_item)
        
        # If no structured items found, create items from paragraphs
        if not actionable_items and ai_response:
            paragraphs = [p.strip() for p in ai_response.split('\n\n') if p.strip()]
            for i, para in enumerate(paragraphs[:5], 1):  # Limit to 5 items
                if len(para) > 50:  # Skip very short paragraphs
                    title = para[:60] + "..." if len(para) > 60 else para
                    actionable_items.append({
                        "id": str(i),
                        "title": title,
                        "description": para,
                        "priority": self.determine_priority(para),
                        "category": self.determine_category(para),
                        "estimated_time": self.estimate_time(para),
                        "impact": self.determine_impact(para)
                    })
        
        return actionable_items
    
    def determine_priority(self, text: str) -> str:
        """Determine priority based on keywords in text"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['urgent', 'critical', 'immediately', 'overdue', 'asap', 'priority']):
            return 'high'
        elif any(word in text_lower for word in ['soon', 'moderate', 'regular', 'scheduled']):
            return 'medium'
        else:
            return 'low'
    
    def determine_category(self, text: str) -> str:
        """Determine category based on keywords in text"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['customer', 'client', 'service', 'satisfaction']):
            return 'Customer Service'
        elif any(word in text_lower for word in ['sale', 'revenue', 'product', 'pricing']):
            return 'Sales'
        elif any(word in text_lower for word in ['train', 'learn', 'skill', 'education']):
            return 'Training'
        elif any(word in text_lower for word in ['paint', 'plumb', 'electric', 'hvac', 'install']):
            return 'Operations'
        elif any(word in text_lower for word in ['lead', 'opportunity', 'prospect']):
            return 'Lead Management'
        elif any(word in text_lower for word in ['staff', 'employee', 'hr', 'team']):
            return 'HR'
        elif any(word in text_lower for word in ['market', 'campaign', 'promotion']):
            return 'Marketing'
        else:
            return 'Operations'
    
    def estimate_time(self, text: str) -> str:
        """Estimate time based on task complexity"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['quick', 'simple', 'easy', 'minor']):
            return '30 minutes'
        elif any(word in text_lower for word in ['complex', 'detailed', 'comprehensive', 'major']):
            return '4 hours'
        elif any(word in text_lower for word in ['urgent', 'immediate']):
            return '1 hour'
        else:
            return '2 hours'
    
    def determine_impact(self, text: str) -> str:
        """Determine business impact"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['revenue', 'sales', 'profit']):
            return 'Increase revenue potential'
        elif any(word in text_lower for word in ['customer', 'satisfaction', 'service']):
            return 'Improve customer satisfaction'
        elif any(word in text_lower for word in ['efficiency', 'productivity', 'time']):
            return 'Increase operational efficiency'
        elif any(word in text_lower for word in ['compliance', 'safety', 'risk']):
            return 'Ensure compliance and safety'
        else:
            return 'Operational improvement'
    
    def add_actionable_items(self, items: List[Dict[str, Any]], query: str = ""):
        """Add actionable items to storage and track them"""
        timestamp = datetime.now().isoformat()
        
        for item in items:
            item['created_at'] = timestamp
            item['completed'] = False
            item['query_context'] = query
            
            # Store in actionable items list
            self.actionable_items.append(item)
            self.item_creation_timestamps[item['id']] = timestamp
    
    def complete_item(self, item_id: str) -> bool:
        """Mark an item as completed"""
        for item in self.actionable_items:
            if item['id'] == item_id:
                item['completed'] = True
                self.completed_items.add(item_id)
                return True
        return False
    
    def execute_task(self, item_id: str) -> Dict[str, Any]:
        """Execute/implement a task (mock implementation)"""
        item = None
        for i in self.actionable_items:
            if i['id'] == item_id:
                item = i
                break
        
        if not item:
            return {"success": False, "error": "Task not found"}
        
        # Mark as executed
        item['executed'] = True
        item['execution_started'] = datetime.now().isoformat()
        self.executed_items.add(item_id)
        
        # Generate mock execution time based on estimated time
        estimated_time = item.get('estimated_time', '2 hours')
        mock_execution_time = self._generate_mock_execution_time(estimated_time)
        
        # Simulate task execution
        execution_result = self._simulate_task_execution(item)
        
        # Store execution data
        item['execution_completed'] = datetime.now().isoformat()
        item['actual_time_spent'] = mock_execution_time
        item['execution_result'] = execution_result
        item['status'] = 'in_progress'
        
        self.execution_times[item_id] = mock_execution_time
        self.task_progression.append({
            'item_id': item_id,
            'title': item['title'],
            'executed_at': item['execution_started'],
            'time_spent': mock_execution_time
        })
        
        return {
            "success": True,
            "execution_result": execution_result,
            "time_spent": mock_execution_time,
            "status": "in_progress"
        }
    
    def _generate_mock_execution_time(self, estimated_time: str) -> str:
        """Generate realistic mock execution time"""
        import random
        
        # Parse estimated time and generate realistic execution time
        if 'minute' in estimated_time.lower():
            base_minutes = int(''.join(filter(str.isdigit, estimated_time))) or 30
            actual_minutes = random.randint(int(base_minutes * 0.8), int(base_minutes * 1.3))
            return f"{actual_minutes} minutes"
        elif 'hour' in estimated_time.lower():
            base_hours = int(''.join(filter(str.isdigit, estimated_time))) or 2
            actual_minutes = random.randint(int(base_hours * 45), int(base_hours * 75))
            if actual_minutes >= 60:
                hours = actual_minutes // 60
                minutes = actual_minutes % 60
                return f"{hours}h {minutes}m" if minutes > 0 else f"{hours} hours"
            else:
                return f"{actual_minutes} minutes"
        else:
            return f"{random.randint(15, 90)} minutes"
    
    def _simulate_task_execution(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate task execution with realistic results"""
        import random
        
        category = item.get('category', 'Operations')
        title = item.get('title', 'Task')
        
        # Generate mock execution results based on category
        results = {
            'Customer Service': [
                "Reviewed 15 customer feedback entries and identified 3 key improvement areas",
                "Updated customer service protocols based on recent feedback trends",
                "Implemented new response templates for common customer inquiries"
            ],
            'Lead Management': [
                "Contacted 12 leads and scheduled 5 follow-up appointments",
                "Updated lead status for 18 prospects in the system",
                "Prioritized leads based on urgency and conversion potential"
            ],
            'Operations': [
                "Optimized workflow processes and identified 2 bottlenecks",
                "Updated inventory levels and synchronized across locations",
                "Implemented new operational procedure and trained team"
            ],
            'Sales': [
                "Analyzed sales data and identified top-performing products",
                "Created promotional strategy for underperforming items",
                "Updated product positioning and pricing recommendations"
            ],
            'Training': [
                "Conducted training session for 8 team members",
                "Developed new training materials for product knowledge",
                "Assessed team skills and identified additional training needs"
            ]
        }
        
        category_results = results.get(category, results['Operations'])
        selected_result = random.choice(category_results)
        
        # Generate performance metrics
        efficiency_score = random.randint(75, 98)
        impact_rating = random.choice(['High', 'Medium', 'High', 'High'])  # Bias toward positive
        
        return {
            "description": selected_result,
            "efficiency_score": efficiency_score,
            "impact_rating": impact_rating,
            "status": "completed_successfully",
            "next_steps": self._generate_next_steps(category)
        }
    
    def _generate_next_steps(self, category: str) -> List[str]:
        """Generate relevant next steps based on category"""
        next_steps_map = {
            'Customer Service': [
                "Monitor customer satisfaction scores over the next week",
                "Schedule follow-up with team to review implementation",
                "Document lessons learned for future reference"
            ],
            'Lead Management': [
                "Schedule follow-up calls with interested prospects",
                "Update CRM with latest lead interaction data",
                "Review conversion rates next week"
            ],
            'Operations': [
                "Monitor process efficiency for the next few days",
                "Gather feedback from team on new procedures",
                "Schedule review meeting to assess impact"
            ],
            'Sales': [
                "Track sales performance of promoted items",
                "Analyze customer response to new positioning",
                "Review and adjust strategy based on results"
            ],
            'Training': [
                "Schedule assessment of training effectiveness",
                "Gather feedback from trainees",
                "Plan advanced training modules if needed"
            ]
        }
        
        return next_steps_map.get(category, next_steps_map['Operations'])
    
    def get_analytics(self) -> Dict[str, Any]:
        """Calculate real-time analytics from actionable items"""
        if not self.actionable_items:
            return self._get_default_analytics()
        
        total_items = len(self.actionable_items)
        completed_items = len([item for item in self.actionable_items if item.get('completed', False)])
        executed_items = len([item for item in self.actionable_items if item.get('executed', False)])
        pending_items = total_items - completed_items - executed_items
        completion_rate = (completed_items / total_items * 100) if total_items > 0 else 0
        execution_rate = (executed_items / total_items * 100) if total_items > 0 else 0
        
        # Calculate category distribution
        categories = {}
        for item in self.actionable_items:
            category = item.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
        
        # Calculate priority distribution
        priority_breakdown = {}
        for item in self.actionable_items:
            priority = item.get('priority', 'medium')
            priority_breakdown[priority] = priority_breakdown.get(priority, 0) + 1
        
        # Calculate execution metrics
        total_time_spent = 0
        high_impact_tasks = 0
        avg_efficiency = 0
        
        executed_tasks = [item for item in self.actionable_items if item.get('executed', False)]
        if executed_tasks:
            for task in executed_tasks:
                # Parse time spent for calculation
                time_str = task.get('actual_time_spent', '0 minutes')
                minutes = self._parse_time_to_minutes(time_str)
                total_time_spent += minutes
                
                # Count high impact tasks
                if task.get('execution_result', {}).get('impact_rating') == 'High':
                    high_impact_tasks += 1
                
                # Sum efficiency scores
                efficiency = task.get('execution_result', {}).get('efficiency_score', 0)
                avg_efficiency += efficiency
            
            avg_efficiency = round(avg_efficiency / len(executed_tasks), 1) if executed_tasks else 0
        
        return {
            "total_actions": total_items,
            "completed_actions": completed_items,
            "executed_actions": executed_items,
            "pending_actions": pending_items,
            "completion_rate": round(completion_rate, 2),
            "execution_rate": round(execution_rate, 2),
            "categories": categories,
            "priority_breakdown": priority_breakdown,
            "execution_metrics": {
                "total_time_spent_minutes": total_time_spent,
                "total_time_spent_display": self._format_minutes_to_display(total_time_spent),
                "average_efficiency_score": avg_efficiency,
                "high_impact_tasks": high_impact_tasks,
                "tasks_executed": len(executed_tasks),
                "productivity_score": round((executed_items / total_items * 100) if total_items > 0 else 0, 1)
            },
            "task_progression": self.task_progression[-5:],  # Last 5 executed tasks
            "rag_status": {
                "initialized": self.is_initialized,
                "indexed_documents": getattr(self.vector_store, 'collection', None) is not None if self.vector_store else False,
                "total_items_generated": total_items,
                "last_generation": max(self.item_creation_timestamps.values()) if self.item_creation_timestamps else None
            }
        }
    
    def _parse_time_to_minutes(self, time_str: str) -> int:
        """Parse time string to minutes for calculations"""
        import re
        
        # Handle formats like "2h 30m", "45 minutes", "1 hours"
        hours = re.findall(r'(\d+)h', time_str)
        minutes = re.findall(r'(\d+)m', time_str)
        
        if 'hour' in time_str.lower():
            hours_num = int(''.join(filter(str.isdigit, time_str))) or 0
            return hours_num * 60
        elif 'minute' in time_str.lower():
            minutes_num = int(''.join(filter(str.isdigit, time_str))) or 0
            return minutes_num
        else:
            total_minutes = 0
            if hours:
                total_minutes += int(hours[0]) * 60
            if minutes:
                total_minutes += int(minutes[0])
            return total_minutes
    
    def _format_minutes_to_display(self, total_minutes: int) -> str:
        """Format minutes to human-readable display"""
        if total_minutes < 60:
            return f"{total_minutes} minutes"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if minutes > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{hours} hours"
    
    def _get_default_analytics(self) -> Dict[str, Any]:
        """Return default analytics when no items exist"""
        return {
            "total_actions": 0,
            "completed_actions": 0,
            "pending_actions": 0,
            "completion_rate": 0.0,
            "categories": {},
            "priority_breakdown": {},
            "rag_status": {
                "initialized": self.is_initialized,
                "indexed_documents": getattr(self.vector_store, 'collection', None) is not None if self.vector_store else False,
                "total_items_generated": 0,
                "last_generation": None
            }
        }
    
    def get_all_actionable_items(self, category_filter=None, priority_filter=None) -> List[Dict[str, Any]]:
        """Get all actionable items with optional filtering"""
        items = self.actionable_items.copy()
        
        if category_filter and category_filter != 'all':
            items = [item for item in items if item.get('category', '').lower() == category_filter.lower()]
        
        if priority_filter and priority_filter != 'all':
            items = [item for item in items if item.get('priority', '').lower() == priority_filter.lower()]
        
        return items

# Initialize global RAG service
rag_service = RAGService()

@app.route('/api/test', methods=['GET'])
def test():
    """Simple test endpoint"""
    return jsonify({"status": "OK", "message": "Backend is working!"})

@app.route('/api/reset-db', methods=['POST'])
def reset_database():
    """Destructive resets are intentionally unavailable over HTTP."""
    return jsonify({
        "success": False,
        "error": "Database reset is disabled; use an owner-approved offline maintenance procedure",
    }), 403

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "rag_available": rag_service.rag_available,
        "rag_initialized": rag_service.is_initialized,
        "dependencies": {
            "chromadb": CHROMADB_AVAILABLE,
            "rag_modules": RAG_AVAILABLE
        }
    })

@app.route('/api/initialize', methods=['POST'])
def initialize_rag():
    """Initialize the RAG system"""
    try:
        result = rag_service.initialize()
        success = result.get("status") in ["initialized", "already_initialized"]
        return jsonify({
            "success": success,
            "data": result
        }), 200 if success else 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/index', methods=['POST'])
def index_data():
    """Index data into vector store"""
    try:
        data = request.json or {}
        json_path = resolve_data_file(data.get('json_path', 'lead_data.json'), '.json')
        rules_path = resolve_data_file(data.get('rules_path', 'lead_intelligence.txt'), '.txt')
        json_limit = max(1, min(int(data.get('json_limit', 4000)), 10000))
        
        # Check if files exist
        if not json_path.is_file():
            return jsonify({
                "success": False,
                "error": f"JSON file not found: {json_path}"
            }), 404
        
        if not rules_path.is_file():
            return jsonify({
                "success": False,
                "error": f"Rules file not found: {rules_path}"
            }), 404
        
        result = rag_service.index_data(json_path, rules_path, json_limit)
        success = result.get("status") == "success"
        
        return jsonify({
            "success": success,
            "data": result
        }), 200 if success else 400
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/search', methods=['POST'])
def search():
    """Search indexed data and get AI response"""
    try:
        data = request.json or {}
        query = data.get('query')
        rules_path = resolve_data_file(data.get('rules_path', 'lead_intelligence.txt'), '.txt')
        top_k = max(1, min(int(data.get('top_k', 50)), 100))
        
        if not isinstance(query, str) or not query.strip() or len(query) > 4000:
            return jsonify({
                "success": False,
            "error": "Query must be a non-empty string of at most 4000 characters"
            }), 400
        
        # Perform search
        search_result = rag_service.search(query, rules_path, top_k)
        
        # Parse AI response into actionable items
        actionable_items = rag_service.parse_ai_response_to_actionable_items(
            search_result['answer'], 
            query
        )
        
        return jsonify({
            "success": True,
            "data": {
                "answer": search_result['answer'],
                "actionable_items": actionable_items,
                "context_docs_count": search_result['context_docs_count'],
                "summary": search_result['answer'][:200] + "..." if len(search_result['answer']) > 200 else search_result['answer'],
                "timestamp": datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint that uses RAG search"""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({
                "error": "Message is required"
            }), 400
        
        message = data['message']
        if not isinstance(message, str) or not message.strip() or len(message) > 4000:
            return jsonify({"error": "Message must be a non-empty string of at most 4000 characters"}), 400
        rules_path = resolve_data_file(data.get('rules_path', 'lead_intelligence.txt'), '.txt')
        
        # Check if system is initialized
        if not rag_service.is_initialized:
            # Try to auto-initialize with default data
            try:
                rag_service.initialize()
                default_json = resolve_data_file('lead_data.json', '.json')
                default_rules = resolve_data_file('lead_intelligence.txt', '.txt')
                if default_json.is_file() and default_rules.is_file():
                    rag_service.index_data(default_json, default_rules)
            except Exception as error:
                logger.warning('RAG auto-initialization failed: %s', error)
        
        # Perform RAG search
        if rag_service.is_initialized:
            search_result = rag_service.search(message, rules_path)
            actionable_items = rag_service.parse_ai_response_to_actionable_items(
                search_result['answer'], 
                message
            )
            
            # Store the generated actionable items for analytics
            rag_service.add_actionable_items(actionable_items, message)
            
            return jsonify({
                "success": True,
                "data": {
                    "actionable_items": actionable_items,
                    "summary": search_result['answer'],
                    "timestamp": datetime.now().isoformat()
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": "RAG service is not initialized"
            }), 503
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({
            "success": False,
            "error": "Chat request failed"
        }), 502

@app.route('/api/actionable-items', methods=['GET'])
def get_actionable_items():
    """Get actionable items with optional filters"""
    try:
        category = request.args.get('category', 'all')
        priority = request.args.get('priority', 'all')
        
        # Get real stored actionable items
        items = rag_service.get_all_actionable_items(category, priority)
        
        # If no items exist, provide helpful empty state
        if not items:
            return jsonify({
                "success": True,
                "data": {
                    "actionable_items": [],
                    "total_count": 0,
                    "filters_applied": {
                        "category": category,
                        "priority": priority
                    },
                    "message": "No actionable items found. Try using the chat interface to generate some!"
                }
            })
        
        return jsonify({
            "success": True,
            "data": {
                "actionable_items": items,
                "total_count": len(items),
                "filters_applied": {
                    "category": category,
                    "priority": priority
                }
            }
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/actionable-items/<item_id>/complete', methods=['POST'])
def complete_actionable_item(item_id):
    """Mark an actionable item as completed"""
    try:
        success = rag_service.complete_item(item_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Item {item_id} marked as completed",
                "data": {
                    "item_id": item_id,
                    "completed_at": datetime.now().isoformat()
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Item {item_id} not found"
            }), 404
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/actionable-items/<item_id>/execute', methods=['POST'])
def execute_actionable_item(item_id):
    """This prototype does not execute external work."""
    return jsonify({
        "success": False,
        "error": "Task execution is simulation-only and is disabled",
        "item_id": item_id,
    }), 409

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics data based on real actionable items"""
    try:
        analytics_data = rag_service.get_analytics()
        
        return jsonify({
            "success": True,
            "data": analytics_data
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(
        debug=os.getenv('FLASK_DEBUG', '').lower() == 'true',
        host=os.getenv('FLASK_HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', '5001')),
    )
