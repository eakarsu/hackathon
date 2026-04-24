import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import ChatInterface from './components/ChatInterface';
import ActionableItemsList from './components/ActionableItemsList';
import Analytics from './components/Analytics';

const API_BASE_URL = 'http://localhost:5001/api';

function App() {
  const [actionableItems, setActionableItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');
  const [analytics, setAnalytics] = useState(null);
  const [indexingStatus, setIndexingStatus] = useState(null);
  const [ragInitialized, setRagInitialized] = useState(false);

  useEffect(() => {
    fetchInitialItems();
    fetchAnalytics();
    checkRAGStatus();
  }, []);

  const fetchInitialItems = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // First test basic connectivity
      await axios.get(`${API_BASE_URL}/test`);
      
      const response = await axios.get(`${API_BASE_URL}/actionable-items`);
      if (response.data.success) {
        setActionableItems(response.data.data.actionable_items);
      }
    } catch (err) {
      console.error('Error fetching items:', err);
      if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
        setError('Cannot connect to backend server. Please make sure the backend is running on port 5000.');
      } else {
        setError('Failed to fetch actionable items: ' + (err.response?.data?.error || err.message));
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/analytics`);
      if (response.data.success) {
        setAnalytics(response.data.data);
        if (response.data.data.rag_status) {
          setRagInitialized(response.data.data.rag_status.initialized);
        }
      }
    } catch (err) {
      console.error('Error fetching analytics:', err);
    }
  };

  const checkRAGStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setRagInitialized(response.data.rag_initialized);
    } catch (err) {
      console.error('Error checking RAG status:', err);
    }
  };

  const handleInitializeRAG = async () => {
    try {
      setLoading(true);
      setIndexingStatus('Initializing RAG system...');
      const response = await axios.post(`${API_BASE_URL}/initialize`);
      if (response.data.success) {
        setRagInitialized(true);
        setIndexingStatus('RAG system initialized successfully!');
        setTimeout(() => setIndexingStatus(null), 3000);
      }
    } catch (err) {
      setError('Failed to initialize RAG system');
      setIndexingStatus(null);
    } finally {
      setLoading(false);
    }
  };

  const handleIndexData = async () => {
    try {
      setLoading(true);
      setIndexingStatus('Indexing data... This may take a few minutes.');
      
      // First initialize if needed
      if (!ragInitialized) {
        await handleInitializeRAG();
      }
      
      const response = await axios.post(`${API_BASE_URL}/index`, {
        json_path: 'lead_data.json',
        rules_path: 'lead_intelligence.txt',
        json_limit: 4000
      });
      
      if (response.data.success) {
        setIndexingStatus(`Successfully indexed ${response.data.data.documents_indexed} documents!`);
        setTimeout(() => setIndexingStatus(null), 5000);
      }
    } catch (err) {
      setError('Failed to index data: ' + (err.response?.data?.error || err.message));
      setIndexingStatus(null);
    } finally {
      setLoading(false);
    }
  };

  const handleChatSubmit = async (message) => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.post(`${API_BASE_URL}/chat`, { message });
      if (response.data.success) {
        setActionableItems(response.data.data.actionable_items);
        return response.data.data;
      }
    } catch (err) {
      setError('Failed to get AI response');
      console.error('Error:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteItem = async (itemId) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/actionable-items/${itemId}/complete`);
      if (response.data.success) {
        // Refresh the actionable items and analytics to reflect the change
        fetchInitialItems();
        fetchAnalytics();
      }
    } catch (err) {
      console.error('Error completing item:', err);
      setError('Failed to mark item as complete: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleExecuteItem = async (itemId) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/actionable-items/${itemId}/execute`);
      if (response.data.success) {
        // Refresh the actionable items and analytics to reflect the execution
        fetchInitialItems();
        fetchAnalytics();
        
        // Show success message
        const result = response.data.data;
        alert(`✅ Task executed successfully!\n\nResult: ${result.execution_result?.description}\nTime spent: ${result.time_spent}\nEfficiency: ${result.execution_result?.efficiency_score}%`);
      }
    } catch (err) {
      console.error('Error executing item:', err);
      setError('Failed to execute task: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = async (filters) => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filters.category) params.append('category', filters.category);
      if (filters.priority) params.append('priority', filters.priority);
      
      const response = await axios.get(`${API_BASE_URL}/actionable-items?${params}`);
      if (response.data.success) {
        setActionableItems(response.data.data.actionable_items);
      }
    } catch (err) {
      setError('Failed to filter items');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>Store Intelligence Platform</h1>
        <p>AI-Powered Actionable Insights for Store Operations</p>
        <div className="rag-controls">
          <div className="rag-status">
            <span className={`status-indicator ${ragInitialized ? 'active' : 'inactive'}`}></span>
            <span>RAG System: {ragInitialized ? 'Active' : 'Not Initialized'}</span>
          </div>
          <button 
            className="index-button"
            onClick={handleIndexData}
            disabled={loading}
          >
            {loading ? 'Processing...' : '📊 Index Lead Data'}
          </button>
        </div>
        {indexingStatus && (
          <div className="indexing-status">
            {indexingStatus}
          </div>
        )}
      </header>

      <nav className="tab-navigation">
        <button 
          className={activeTab === 'chat' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('chat')}
        >
          Chat Assistant
        </button>
        <button 
          className={activeTab === 'items' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('items')}
        >
          Actionable Items
        </button>
        <button 
          className={activeTab === 'analytics' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
      </nav>

      <main className="main-content">
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {activeTab === 'chat' && (
          <ChatInterface 
            onSubmit={handleChatSubmit}
            actionableItems={actionableItems}
            loading={loading}
          />
        )}

        {activeTab === 'items' && (
          <ActionableItemsList
            items={actionableItems}
            loading={loading}
            onComplete={handleCompleteItem}
            onExecute={handleExecuteItem}
            onFilterChange={handleFilterChange}
          />
        )}

        {activeTab === 'analytics' && analytics && (
          <Analytics data={analytics} />
        )}
      </main>
    </div>
  );
}

export default App;