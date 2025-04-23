import React, { useState } from 'react';
import { useAppContext } from '../context/AppContext';
import './UsageStats.css';

function UsageStats() {
  const [activeTab, setActiveTab] = useState('standard');
  const { tasks, wallets, selectedWallets, isLoadingTasks } = useAppContext();
  
  // Calculate stats
  const activeTasks = tasks.filter(task => ['pending', 'running'].includes(task.status));
  const completedTasks = tasks.filter(task => task.status === 'completed');
  
  // Calculate transaction totals - in a real app this would come from the backend
  const maxTransactions = 1000;
  const usedTransactions = completedTasks.length * 2; // Assuming 2 txs per completed task
  const remainingTransactions = maxTransactions - usedTransactions;
  const txPercentage = (usedTransactions / maxTransactions) * 100;
  
  // Calculate active workflows
  const maxWorkflows = 10;
  const activeWorkflowsCount = activeTasks.length;
  const workflowPercentage = (activeWorkflowsCount / maxWorkflows) * 100;
  
  // Get the first selected wallet for display
  const firstWallet = selectedWallets.length > 0 ? selectedWallets[0].address : '';
  
  return (
    <div className="usage-stats">
      <div className="usage-tabs">
        <button 
          className={`tab-btn ${activeTab === 'standard' ? 'active' : ''}`}
          onClick={() => setActiveTab('standard')}
        >
          Standard
        </button>
        <button 
          className={`tab-btn ${activeTab === 'usage' ? 'active' : ''}`}
          onClick={() => setActiveTab('usage')}
        >
          Today usage
        </button>
      </div>
      
      {isLoadingTasks && <div className="loading-indicator">Loading stats...</div>}
      
      <div className="stats-cards">
        <div className="stat-card">
          <div className="stat-title">Remaining Transactions Build</div>
          <div className="stat-subtitle">Sum from all wallets</div>
          <div className="stat-number">{remainingTransactions}</div>
          <div className="stat-details">/{maxTransactions} txs</div>
          <div className="stat-progress">
            <div className="progress-bar" style={{ width: `${txPercentage}%` }}></div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-title">Active Workflows</div>
          <div className="stat-subtitle">{firstWallet || 'No wallet selected'}</div>
          <div className="stat-number">{activeWorkflowsCount}</div>
          <div className="stat-details">/{maxWorkflows}</div>
          <div className="stat-progress">
            <div className="progress-bar" style={{ width: `${workflowPercentage}%` }}></div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UsageStats; 