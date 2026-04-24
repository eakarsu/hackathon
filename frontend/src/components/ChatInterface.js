import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';

const ChatInterface = ({ onSubmit, actionableItems, loading }) => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    const userMessage = {
      type: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };

    setChatHistory(prev => [...prev, userMessage]);
    setMessage('');
    setIsTyping(true);

    try {
      const response = await onSubmit(message);
      
      const aiMessage = {
        type: 'ai',
        content: response.summary,
        actionableItems: response.actionable_items,
        timestamp: response.timestamp
      };

      setChatHistory(prev => [...prev, aiMessage]);
    } catch (error) {
      const errorMessage = {
        type: 'error',
        content: 'Failed to get response. Please try again.',
        timestamp: new Date().toISOString()
      };
      setChatHistory(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const quickPrompts = [
    "What are the top priority tasks for today?",
    "Show me sales improvement strategies",
    "Employee training recommendations",
    "Customer service improvements needed",
    "Inventory optimization suggestions"
  ];

  const handleQuickPrompt = (prompt) => {
    setMessage(prompt);
  };

  return (
    <div className="chat-interface">
      <div className="chat-container">
        <div className="chat-messages">
          {chatHistory.length === 0 && (
            <div className="welcome-message">
              <h3>Welcome to Store Intelligence Assistant</h3>
              <p>Ask me about store operations, employee tasks, or sales strategies.</p>
            </div>
          )}

          {chatHistory.map((msg, index) => (
            <div key={index} className={`message ${msg.type}`}>
              <div className="message-header">
                <span className="message-sender">
                  {msg.type === 'user' ? 'You' : 'AI Assistant'}
                </span>
                <span className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="message-content">
                {msg.content}
              </div>
              {msg.actionableItems && msg.actionableItems.length > 0 && (
                <div className="message-items">
                  <h4>Generated Actionable Items:</h4>
                  <div className="items-grid">
                    {msg.actionableItems.map((item) => (
                      <div key={item.id} className="chat-item-card">
                        <div className="item-header">
                          <span className={`priority-badge ${item.priority}`}>
                            {item.priority}
                          </span>
                          <span className="category-tag">{item.category}</span>
                        </div>
                        <h5>{item.title}</h5>
                        <p>{item.description}</p>
                        <div className="item-meta">
                          <span>⏱ {item.estimated_time}</span>
                          <span>📈 {item.impact}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="message ai typing">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        <div className="quick-prompts">
          <span className="quick-prompts-label">Quick prompts:</span>
          {quickPrompts.map((prompt, index) => (
            <button
              key={index}
              className="quick-prompt-btn"
              onClick={() => handleQuickPrompt(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="chat-input-form">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask about store operations, tasks, or strategies..."
            className="chat-input"
            disabled={loading}
          />
          <button type="submit" className="send-button" disabled={loading || !message.trim()}>
            {loading ? '...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;