import React from 'react';
import WorkflowList from './WorkflowList';
import './Sidebar.css';

function Sidebar() {
  return (
    <div className="sidebar">
      <div className="app-title">
        <h1>PinkShark Bot</h1>
      </div>
      
      <WorkflowList />
    </div>
  );
}

export default Sidebar; 