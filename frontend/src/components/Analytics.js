import React from 'react';
import './Analytics.css';

const Analytics = ({ data }) => {
  if (!data) {
    return <div className="loading">Loading analytics...</div>;
  }

  const completionPercentage = (data.completed_actions / data.total_actions) * 100;

  const getCategoryColor = (category) => {
    const colors = {
      'Customer Service': '#4CAF50',
      'Operations': '#2196F3',
      'Sales': '#FF9800',
      'Training': '#9C27B0',
      'Marketing': '#F44336',
      'HR': '#00BCD4'
    };
    return colors[category] || '#757575';
  };

  const getPriorityColor = (priority) => {
    const colors = {
      'high': '#F44336',
      'medium': '#FF9800',
      'low': '#4CAF50'
    };
    return colors[priority] || '#757575';
  };

  return (
    <div className="analytics-dashboard">
      <div className="analytics-header">
        <h2>Performance Analytics</h2>
        <p>Real-time insights into store operations and task completion</p>
      </div>

      <div className="analytics-grid">
        <div className="analytics-card large">
          <h3>Completion Rate</h3>
          <div className="completion-chart">
            <svg viewBox="0 0 200 200" className="circular-chart">
              <circle
                className="circle-bg"
                cx="100"
                cy="100"
                r="80"
                fill="none"
                stroke="#f0f0f0"
                strokeWidth="20"
              />
              <circle
                className="circle-progress"
                cx="100"
                cy="100"
                r="80"
                fill="none"
                stroke="url(#gradient)"
                strokeWidth="20"
                strokeDasharray={`${completionPercentage * 5.03} 503`}
                strokeDashoffset="0"
                transform="rotate(-90 100 100)"
              />
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#667eea" />
                  <stop offset="100%" stopColor="#764ba2" />
                </linearGradient>
              </defs>
            </svg>
            <div className="chart-center">
              <span className="percentage">{completionPercentage.toFixed(1)}%</span>
              <span className="label">Complete</span>
            </div>
          </div>
          <div className="completion-stats">
            <div className="stat">
              <span className="stat-value">{data.completed_actions}</span>
              <span className="stat-name">Completed</span>
            </div>
            <div className="stat">
              <span className="stat-value">{data.pending_actions}</span>
              <span className="stat-name">Pending</span>
            </div>
            <div className="stat">
              <span className="stat-value">{data.total_actions}</span>
              <span className="stat-name">Total</span>
            </div>
          </div>
        </div>

        <div className="analytics-card">
          <h3>Priority Distribution</h3>
          <div className="priority-chart">
            {Object.entries(data.priority_breakdown).map(([priority, count]) => {
              const percentage = (count / data.total_actions) * 100;
              return (
                <div key={priority} className="priority-bar">
                  <div className="bar-label">
                    <span className="priority-name">{priority}</span>
                    <span className="priority-count">{count}</span>
                  </div>
                  <div className="bar-container">
                    <div
                      className="bar-fill"
                      style={{
                        width: `${percentage}%`,
                        backgroundColor: getPriorityColor(priority)
                      }}
                    />
                  </div>
                  <span className="bar-percentage">{percentage.toFixed(1)}%</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="analytics-card">
          <h3>Category Breakdown</h3>
          <div className="category-grid">
            {Object.entries(data.categories).map(([category, count]) => (
              <div key={category} className="category-item">
                <div
                  className="category-indicator"
                  style={{ backgroundColor: getCategoryColor(category) }}
                />
                <div className="category-info">
                  <span className="category-name">{category}</span>
                  <span className="category-count">{count} tasks</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="analytics-card">
          <h3>Quick Stats</h3>
          <div className="quick-stats">
            <div className="quick-stat">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="#4CAF50">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
              <div>
                <span className="quick-stat-value">{data.completed_actions}</span>
                <span className="quick-stat-label">Tasks Completed</span>
              </div>
            </div>
            <div className="quick-stat">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="#FF9800">
                <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"/>
                <path d="M12.5 7H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
              </svg>
              <div>
                <span className="quick-stat-value">{data.executed_actions || 0}</span>
                <span className="quick-stat-label">Tasks Executed</span>
              </div>
            </div>
            <div className="quick-stat">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="#2196F3">
                <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
              </svg>
              <div>
                <span className="quick-stat-value">{data.execution_rate?.toFixed(0) || 0}%</span>
                <span className="quick-stat-label">Execution Rate</span>
              </div>
            </div>
          </div>
        </div>

        {data.execution_metrics && (
          <div className="analytics-card">
            <h3>Execution Performance</h3>
            <div className="execution-performance">
              <div className="performance-metric">
                <span className="metric-value">{data.execution_metrics.total_time_spent_display}</span>
                <span className="metric-label">Total Time Invested</span>
              </div>
              <div className="performance-metric">
                <span className="metric-value">{data.execution_metrics.average_efficiency_score}%</span>
                <span className="metric-label">Avg Efficiency Score</span>
              </div>
              <div className="performance-metric">
                <span className="metric-value">{data.execution_metrics.high_impact_tasks}</span>
                <span className="metric-label">High Impact Tasks</span>
              </div>
              <div className="performance-metric">
                <span className="metric-value">{data.execution_metrics.productivity_score}%</span>
                <span className="metric-label">Productivity Score</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="insights-section">
        <h3>Key Insights</h3>
        <div className="insights-grid">
          <div className="insight-card">
            <div className="insight-icon" style={{ background: '#E3F2FD' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="#2196F3">
                <path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/>
              </svg>
            </div>
            <div className="insight-content">
              <h4>Peak Performance</h4>
              <p>Task completion rate is highest during morning hours (9 AM - 12 PM)</p>
            </div>
          </div>
          
          <div className="insight-card">
            <div className="insight-icon" style={{ background: '#FCE4EC' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="#E91E63">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
            </div>
            <div className="insight-content">
              <h4>Priority Focus</h4>
              <p>{((data.priority_breakdown.high / data.total_actions) * 100).toFixed(0)}% of tasks are high priority requiring immediate attention</p>
            </div>
          </div>

          <div className="insight-card">
            <div className="insight-icon" style={{ background: '#E8F5E9' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="#4CAF50">
                <path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
              </svg>
            </div>
            <div className="insight-content">
              <h4>Category Leader</h4>
              <p>Operations category has the most tasks requiring attention</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;