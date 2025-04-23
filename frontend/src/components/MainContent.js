import React, { useState } from 'react';
import UsageStats from './UsageStats';
import WorkflowDetail from './WorkflowDetail';
import LogsPage from './LogsPage';
import WalletList from './WalletList';
import './MainContent.css';

function MainContent() {
  const [activeTab, setActiveTab] = useState('workflow'); // default tab: workflow

  return (
    <div className="main-content">
      <UsageStats />
      
      {/* Tab Navigation */}
      <div style={{
        display: 'flex',
        marginBottom: '20px',
        borderBottom: '1px solid #ddd'
      }}>
        <button 
          style={{
            padding: '10px 20px',
            border: 'none',
            background: activeTab === 'workflow' ? '#ffb6c1' : 'transparent',
            color: activeTab === 'workflow' ? 'white' : '#333',
            borderRadius: '5px 5px 0 0',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
          onClick={() => setActiveTab('workflow')}
        >
          Workflow
        </button>
        <button 
          style={{
            padding: '10px 20px',
            border: 'none',
            background: activeTab === 'wallet' ? '#ffb6c1' : 'transparent',
            color: activeTab === 'wallet' ? 'white' : '#333',
            borderRadius: '5px 5px 0 0',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
          onClick={() => setActiveTab('wallet')}
        >
          Wallets
        </button>
        <button 
          style={{
            padding: '10px 20px',
            border: 'none',
            background: activeTab === 'logs' ? '#ffb6c1' : 'transparent',
            color: activeTab === 'logs' ? 'white' : '#333',
            borderRadius: '5px 5px 0 0',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
          onClick={() => setActiveTab('logs')}
        >
          Logs
        </button>
      </div>

      {/* Tab Content */}
      <div style={{ display: activeTab === 'workflow' ? 'block' : 'none' }}>
        <WorkflowDetail />
      </div>
      <div style={{ display: activeTab === 'wallet' ? 'block' : 'none' }}>
        <WalletList />
      </div>
      <div style={{ display: activeTab === 'logs' ? 'block' : 'none' }}>
        <LogsPage />
      </div>
    </div>
  );
}

export default MainContent; 