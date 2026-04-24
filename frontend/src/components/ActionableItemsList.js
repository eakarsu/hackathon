import React, { useState } from 'react';
import './ActionableItemsList.css';

const ActionableItemsList = ({ items, loading, onComplete, onFilterChange, onExecute }) => {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedPriority, setSelectedPriority] = useState('all');
  const [expandedItems, setExpandedItems] = useState(new Set());

  // Get next recommended task
  const getNextRecommendedTask = () => {
    const pendingTasks = items.filter(item => !item.completed && !item.executed);
    if (pendingTasks.length === 0) return null;
    
    // Prioritize by: 1) High priority, 2) Category variety, 3) High impact
    const highPriorityTasks = pendingTasks.filter(t => t.priority === 'high');
    if (highPriorityTasks.length > 0) return highPriorityTasks[0];
    
    const mediumPriorityTasks = pendingTasks.filter(t => t.priority === 'medium');
    if (mediumPriorityTasks.length > 0) return mediumPriorityTasks[0];
    
    return pendingTasks[0];
  };

  const categories = ['all', 'Customer Service', 'Operations', 'Sales', 'Training', 'Marketing', 'HR'];
  const priorities = ['all', 'high', 'medium', 'low'];

  const handleCategoryChange = (category) => {
    setSelectedCategory(category);
    onFilterChange({ category: category === 'all' ? null : category, priority: selectedPriority === 'all' ? null : selectedPriority });
  };

  const handlePriorityChange = (priority) => {
    setSelectedPriority(priority);
    onFilterChange({ category: selectedCategory === 'all' ? null : selectedCategory, priority: priority === 'all' ? null : priority });
  };

  const toggleItemExpansion = (itemId) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  if (loading) {
    return (
      <div className="loading-spinner">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="actionable-items-list">
      <div className="filters-section">
        <div className="filter-group">
          <label>Category:</label>
          <div className="filter-buttons">
            {categories.map(cat => (
              <button
                key={cat}
                className={`filter-btn ${selectedCategory === cat ? 'active' : ''}`}
                onClick={() => handleCategoryChange(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <label>Priority:</label>
          <div className="filter-buttons">
            {priorities.map(priority => (
              <button
                key={priority}
                className={`filter-btn ${selectedPriority === priority ? 'active' : ''}`}
                onClick={() => handlePriorityChange(priority)}
              >
                {priority}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="items-stats">
        <div className="stat-card">
          <span className="stat-number">{items.length}</span>
          <span className="stat-label">Total Items</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{items.filter(i => i.priority === 'high').length}</span>
          <span className="stat-label">High Priority</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{items.filter(i => !i.completed && !i.executed).length}</span>
          <span className="stat-label">Pending</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{items.filter(i => i.executed).length}</span>
          <span className="stat-label">Executed</span>
        </div>
      </div>

      {getNextRecommendedTask() && (
        <div className="next-task-section">
          <h3>🎯 Next Recommended Task</h3>
          <div className="next-task-card">
            <div className="next-task-header">
              <h4>{getNextRecommendedTask().title}</h4>
              <div className="next-task-badges">
                <span className={`priority-badge ${getNextRecommendedTask().priority}`}>
                  {getNextRecommendedTask().priority}
                </span>
                <span className="category-badge">
                  {getNextRecommendedTask().category}
                </span>
              </div>
            </div>
            <p className="next-task-description">{getNextRecommendedTask().description}</p>
            <div className="next-task-actions">
              <button
                className="execute-btn"
                onClick={() => {
                  onExecute(getNextRecommendedTask().id);
                  toggleItemExpansion(getNextRecommendedTask().id);
                }}
              >
                🚀 Start This Task
              </button>
              <span className="next-task-impact">
                Impact: {getNextRecommendedTask().impact} | Time: {getNextRecommendedTask().estimated_time}
              </span>
            </div>
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <div className="no-items">
          <p>No actionable items found. Try adjusting your filters or ask the AI assistant for recommendations.</p>
        </div>
      ) : (
        <div className="items-container">
          {items.map((item) => (
            <div 
              key={item.id} 
              className={`item-card ${item.completed ? 'completed' : ''} ${expandedItems.has(item.id) ? 'expanded' : ''}`}
            >
              <div className="item-main" onClick={() => toggleItemExpansion(item.id)}>
                <div className="item-header">
                  <h3>{item.title}</h3>
                  <div className="item-badges">
                    <span className={`priority-badge ${item.priority}`}>
                      {item.priority}
                    </span>
                    <span className="category-badge">
                      {item.category}
                    </span>
                  </div>
                </div>

                <p className="item-description">{item.description}</p>

                <div className="item-footer">
                  <div className="item-metrics">
                    <span className="metric">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z"/>
                        <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z"/>
                      </svg>
                      {item.estimated_time}
                    </span>
                    <span className="metric">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8zm7.5-6.923c-.67.204-1.335.82-1.887 1.855A7.97 7.97 0 0 0 5.145 4H7.5V1.077zM4.09 4a9.267 9.267 0 0 1 .64-1.539 6.7 6.7 0 0 1 .597-.933A7.025 7.025 0 0 0 2.255 4H4.09zm-.582 3.5c.03-.877.138-1.718.312-2.5H1.674a6.958 6.958 0 0 0-.656 2.5h2.49zM4.847 5a12.5 12.5 0 0 0-.338 2.5H7.5V5H4.847zM8.5 5v2.5h2.99a12.495 12.495 0 0 0-.337-2.5H8.5zM4.51 8.5a12.5 12.5 0 0 0 .337 2.5H7.5V8.5H4.51zm3.99 0V11h2.653c.187-.765.306-1.608.338-2.5H8.5zM5.145 12c.138.386.295.744.468 1.068.552 1.035 1.218 1.65 1.887 1.855V12H5.145zm.182 2.472a6.696 6.696 0 0 1-.597-.933A9.268 9.268 0 0 1 4.09 12H2.255a7.024 7.024 0 0 0 3.072 2.472zM3.82 11a13.652 13.652 0 0 1-.312-2.5h-2.49c.062.89.291 1.733.656 2.5H3.82zm6.853 3.472A7.024 7.024 0 0 0 13.745 12H11.91a9.27 9.27 0 0 1-.64 1.539 6.688 6.688 0 0 1-.597.933zM8.5 12v2.923c.67-.204 1.335-.82 1.887-1.855.173-.324.33-.682.468-1.068H8.5zm3.68-1h2.146c.365-.767.594-1.61.656-2.5h-2.49a13.65 13.65 0 0 1-.312 2.5zm2.802-3.5a6.959 6.959 0 0 0-.656-2.5H12.18c.174.782.282 1.623.312 2.5h2.49zM11.27 2.461c.247.464.462.98.64 1.539h1.835a7.024 7.024 0 0 0-3.072-2.472c.218.284.418.598.597.933zM10.855 4a7.966 7.966 0 0 0-.468-1.068C9.835 1.897 9.17 1.282 8.5 1.077V4h2.355z"/>
                      </svg>
                      {item.impact}
                    </span>
                  </div>
                </div>
              </div>

              {expandedItems.has(item.id) && (
                <div className="item-expanded">
                  <div className="expanded-content">
                    <h4>Implementation Details</h4>
                    <p>This action requires coordination with relevant team members and should be completed within the estimated timeframe.</p>
                    
                    <h4>Expected Outcomes</h4>
                    <ul>
                      <li>Improved operational efficiency</li>
                      <li>Enhanced customer satisfaction</li>
                      <li>Measurable business impact: {item.impact}</li>
                    </ul>

                    {!item.completed && !item.executed && (
                      <div className="action-buttons">
                        <button
                          className="execute-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            onExecute(item.id);
                          }}
                        >
                          🚀 Implement This Task
                        </button>
                        <button
                          className="complete-btn secondary"
                          onClick={(e) => {
                            e.stopPropagation();
                            onComplete(item.id);
                          }}
                        >
                          Mark as Complete
                        </button>
                      </div>
                    )}

                    {item.executed && !item.completed && (
                      <div className="execution-results">
                        <h4>✅ Task Executed</h4>
                        <div className="execution-summary">
                          <p><strong>Result:</strong> {item.execution_result?.description}</p>
                          <div className="execution-metrics">
                            <span className="metric">⏱️ Time: {item.actual_time_spent}</span>
                            <span className="metric">📊 Efficiency: {item.execution_result?.efficiency_score}%</span>
                            <span className="metric">🎯 Impact: {item.execution_result?.impact_rating}</span>
                          </div>
                          {item.execution_result?.next_steps && (
                            <div className="next-steps">
                              <h5>Next Steps:</h5>
                              <ul>
                                {item.execution_result.next_steps.map((step, index) => (
                                  <li key={index}>{step}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                        <button
                          className="complete-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            onComplete(item.id);
                          }}
                        >
                          ✅ Mark as Complete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {item.completed && (
                <div className="completed-overlay">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                  </svg>
                  Completed
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ActionableItemsList;