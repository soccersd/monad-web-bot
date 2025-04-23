import React from 'react';
import { useAppContext } from '../context/AppContext';
import './WorkflowList.css';

// Mock data for workflows (will be replaced with API data later)
const MOCK_WORKFLOWS = [
  { id: 1, name: 'Workflow Name is Test Ja' },
  { id: 2, name: 'NFT Minter workflow' },
  { id: 3, name: 'Workflow#5' },
  { id: 4, name: 'OOOOOOOOOOOOOOOOOOO' },
];

function WorkflowList() {
  const { workflows, selectedWorkflowId, selectWorkflow } = useAppContext();

  // ฟังก์ชันสำหรับลบคำว่า (Counter) หรือ ข้อความในวงเล็บออกจากชื่อ workflow
  const cleanWorkflowName = (name) => {
    return name.replace(/\s*\([^)]*\)\s*/g, '');
  };

  return (
    <div className="workflows-container">
      <div className="workflows-header">
        <h2>Workflows</h2>
      </div>
      
      <div className="workflow-list">
        {workflows.map(workflow => (
          <div 
            key={workflow.id} 
            className={`workflow-item ${selectedWorkflowId === workflow.id ? 'selected' : ''}`}
            onClick={() => selectWorkflow(workflow.id)}
          >
            <div className="workflow-name">{cleanWorkflowName(workflow.name)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default WorkflowList; 