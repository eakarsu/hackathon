# Store Intelligence Platform

AI-powered RAG (Retrieval Augmented Generation) web application for generating and managing actionable insights for store operations. The system uses ChromaDB vector search combined with AI to provide dynamic, context-aware recommendations for store employees based on lead data and business rules.

## Architecture

- **Backend**: Python Flask REST API with RAG system integration
- **Vector Store**: ChromaDB with SentenceTransformers embeddings
- **AI Client**: OAuth-based AI API integration with SSL bypass for development
- **Frontend**: React.js with modern UI components
- **Features**: 
  - RAG-powered chat interface with lead data context
  - Vector search and similarity matching
  - Dynamic actionable item generation
  - Real-time data indexing
  - Analytics dashboard with RAG status monitoring

## Setup Instructions

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your AI API credentials:
# AI_CLIENT_ID=your_client_id_here
# AI_CLIENT_SECRET=your_client_secret_here  
# AI_TOKEN_URL=https://your-token-url
# AI_CHAT_URL=https://your-chat-url
# AI_MODEL=gpt-4o
```

5. Prepare data files:
```bash
# Make sure you have these files in the project root:
# - lead_data.json (your lead data)
# - lead_intelligence.txt (your business rules)
```

6. Create model cache directory:
```bash
mkdir -p model_cache
cd model_cache
# The sentence-transformers model will be downloaded automatically
```

7. Run Flask server:
```bash
python app.py
# OR use the convenience script:
./start-backend.sh
```

Backend will run on http://localhost:5001 (port 5001 to avoid conflicts with macOS AirPlay)

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm start
```

Frontend will run on http://localhost:3000

## Usage

### Initial Setup
1. Start both backend and frontend servers
2. Open http://localhost:3000 in your browser
3. In the dashboard header, click **"📊 Index Lead Data"** to initialize the RAG system
4. Wait for indexing to complete (may take a few minutes for large datasets)

### Using the Application
- **Chat Interface**: Ask questions about leads and store operations
- **Actionable Items**: View and manage generated recommendations  
- **Analytics**: Monitor performance and RAG system status

### Sample Queries
```
"I am employee of store number 6338. Give me actionable tasks for store number 6338. Which lead items shall I work first?"

"What are the top priority leads for painting work?"

"Show me overdue customer leads that need immediate attention"

"What training recommendations do you have for new employees?"
```

## API Endpoints

### RAG System Management
- **POST** `/api/initialize`
  - Initialize RAG system components
  
- **POST** `/api/index`
  - Index JSON data and rules into vector store
  - Request: `{ "json_path": "lead_data.json", "rules_path": "lead_intelligence.txt", "json_limit": 4000 }`

- **POST** `/api/search`
  - Search vector store and get AI response
  - Request: `{ "query": "your search query", "top_k": 300 }`

### Chat & Items
- **POST** `/api/chat`
  - RAG-powered chat interface
  - Request: `{ "message": "your question here" }`
  - Returns: Context-aware AI response with actionable items

- **GET** `/api/actionable-items`
  - Retrieve actionable items with filters
  - Query params: `category`, `priority`

### System Status
- **GET** `/api/health`
  - Check API and RAG system status
  
- **GET** `/api/analytics`
  - Get performance metrics and RAG status

## Features

### Chat Interface
- Natural language interaction with AI
- Quick prompt suggestions
- Real-time response generation
- Visual display of generated actionable items

### Actionable Items Management
- Dynamic item generation based on queries
- Priority levels (High, Medium, Low)
- Categories (Customer Service, Operations, Sales, Training, Marketing, HR)
- Estimated time and impact metrics
- Expandable details view
- Mark items as complete

### Analytics Dashboard
- Completion rate visualization
- Priority distribution charts
- Category breakdown
- Real-time performance metrics
- Key insights generation

## Project Structure

```
hackathon/
├── backend/
│   ├── app.py              # Flask application and API endpoints
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment variables template
│
└── frontend/
    ├── src/
    │   ├── App.js           # Main application component
    │   ├── App.css          # Application styles
    │   └── components/
    │       ├── ChatInterface.js       # Chat UI component
    │       ├── ActionableItemsList.js # Items display component
    │       └── Analytics.js          # Analytics dashboard
    ├── public/
    │   └── index.html       # HTML template
    └── package.json         # Node dependencies
```

## Technologies Used

### Backend
- Flask 3.0.0 - Web framework
- Flask-CORS - Cross-origin resource sharing
- Python-dotenv - Environment management
- OpenAI - AI integration (placeholder for actual implementation)

### Frontend
- React 18.2.0 - UI framework
- Axios - HTTP client
- CSS3 - Styling with modern features

## Development Notes

The current implementation includes a mock AI service that returns example actionable items. To integrate with an actual AI service:

1. Replace the `AIService.get_actionable_items()` method in `backend/app.py`
2. Add your AI API credentials to the `.env` file
3. Implement the actual AI API calls based on your service provider

## Future Enhancements

- User authentication and authorization
- Persistent storage with database integration
- Real-time updates with WebSocket
- Export functionality for actionable items
- Team collaboration features
- Mobile-responsive design improvements
- Advanced filtering and search capabilities