import React from 'react';
import { useAppContext } from '../context/AppContext';

function TestRunButton() {
  const { selectedWorkflow, fetchTasks, tasks, runMultiStepWorkflow } = useAppContext();
  
  const activeTaskId = tasks && tasks.length > 0 ? tasks[0].id : null;
  const activeTask = activeTaskId ? tasks?.find(task => task.id === activeTaskId) : null;
  const isTaskStoppable = activeTask && ['running', 'pending', 'stopping'].includes(activeTask.status?.toLowerCase());
  
  console.log('Test Component - Button Visibility Check');
  console.log('selectedWorkflow:', selectedWorkflow);
  console.log('activeTask:', activeTask);
  console.log('isTaskStoppable:', isTaskStoppable);
  console.log('tasks:', tasks);
  
  const handleRunWorkflow = async () => {
    if (!selectedWorkflow) return;
    console.log('Running workflow with ID:', selectedWorkflow.id);
    await runMultiStepWorkflow(selectedWorkflow.id);
    fetchTasks();
  };

  return (
    <div style={{ margin: '20px', padding: '20px', border: '1px solid #ccc' }}>
      <h3>Test Run Button Component</h3>
      <div>Selected Workflow: {selectedWorkflow ? selectedWorkflow.name : 'None'}</div>
      <div>Active Task: {activeTask ? activeTask.id : 'None'}</div>
      <div>Task Stoppable: {isTaskStoppable ? 'Yes' : 'No'}</div>
      <div>Tasks Count: {tasks ? tasks.length : 0}</div>
      
      <div style={{ marginTop: '20px' }}>
        <button 
          className="run-now-btn" 
          onClick={handleRunWorkflow}
          style={{
            background: '#ffb6c1',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            padding: '8px 12px',
            cursor: 'pointer',
            display: 'block',
            margin: '10px 0'
          }}
        >
          Run Test
        </button>
      </div>
    </div>
  );
}

export default TestRunButton; 