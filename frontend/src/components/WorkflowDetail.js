import React, { useState, useEffect } from 'react';
import { useAppContext } from '../context/AppContext';
import './WorkflowDetail.css';

// Component for editing a specific step's configuration
function StepConfigEditor({ workflowId, step, onConfigChange, onCancel }) {
    const { updateStepConfig } = useAppContext();
    const [localConfig, setLocalConfig] = useState({ ...step.config }); // Initialize with current config

    useEffect(() => {
        // Reset local config if the step changes
        setLocalConfig({ ...step.config });
    }, [step]);

    const handleInputChange = (event) => {
        const { name, value, type, checked } = event.target;
        setLocalConfig(prevConfig => ({
            ...prevConfig,
            [name]: type === 'checkbox' ? checked : (type === 'number' ? Number(value) || 0 : value) // Handle different input types
        }));
    };

    const handleSave = () => {
        updateStepConfig(workflowId, step.step_id, localConfig);
        onConfigChange(); // Notify parent that config was saved/updated
    };

    // Render form fields based on step type
    const renderConfigFields = () => {
        switch (step.type) {
            case 'delay':
                return (
                    <div className="form-group">
                        <label htmlFor={`duration_${step.step_id}`}>Duration (seconds):</label>
                        <input
                            type="number"
                            id={`duration_${step.step_id}`}
                            name="duration_seconds"
                            value={localConfig.duration_seconds || ''}
                            onChange={handleInputChange}
                            min="1"
                        />
                    </div>
                );
            case 'stake': // Example for stake
                return (
                    <>
                        <div className="form-group">
                            <label htmlFor={`contract_type_${step.step_id}`}>Contract Type:</label>
                            <select
                                id={`contract_type_${step.step_id}`}
                                name="contract_type"
                                value={localConfig.contract_type || 'kitsu'}
                                onChange={handleInputChange}
                            >
                                <option value="kitsu">Kitsu</option>
                                {/* Add other contract types if needed */}
                            </select>
                        </div>
                        <div className="form-group">
                            <label htmlFor={`amount_${step.step_id}`}>Amount:</label>
                            <input
                                type="text" // Use text for potential large numbers or decimals
                                id={`amount_${step.step_id}`}
                                name="amount"
                                value={localConfig.amount || ''}
                                onChange={handleInputChange}
                                placeholder="e.g., 0.1"
                            />
                             <span className="input-suffix">MON</span>
                        </div>
                    </>
                );
            case 'swap': // Example for swap
                 return (
                     <>
                         <div className="form-group">
                             <label htmlFor={`token_from_symbol_${step.step_id}`}>From Token:</label>
                             <input
                                 type="text"
                                 id={`token_from_symbol_${step.step_id}`}
                                 name="token_from_symbol"
                                 value={localConfig.token_from_symbol || ''}
                                 onChange={handleInputChange}
                                 placeholder="e.g., MON"
                             />
                         </div>
                         <div className="form-group">
                             <label htmlFor={`token_to_symbol_${step.step_id}`}>To Token:</label>
                             <input
                                 type="text"
                                 id={`token_to_symbol_${step.step_id}`}
                                 name="token_to_symbol"
                                 value={localConfig.token_to_symbol || ''}
                                 onChange={handleInputChange}
                                 placeholder="e.g., USDC"
                             />
                         </div>
                         <div className="form-group">
                             <label htmlFor={`amount_str_${step.step_id}`}>Amount:</label>
                             <input
                                 type="text"
                                 id={`amount_str_${step.step_id}`}
                                 name="amount_str"
                                 value={localConfig.amount_str || ''}
                                 onChange={handleInputChange}
                                 placeholder="e.g., 0.1"
                             />
                         </div>
                         {/* Add slippage, recipient etc. if needed */}
                     </>
                 );
            // Add cases for other step types (deploy, send, etc.)
            default:
                return <p>No configuration available for step type: {step.type}</p>;
        }
    };

    return (
        <div className="step-config-editor">
            <h4>Configure Step: {step.type}</h4>
            <div className="config-form">
                {renderConfigFields()}
            </div>
            <div className="config-actions">
                <button onClick={handleSave} className="save-config-btn" style={{
                    background: 'linear-gradient(to right, #ff5c8d, #ff8fab)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '8px 16px',
                    cursor: 'pointer',
                    fontSize: '0.9rem',
                    fontWeight: '500',
                    marginRight: '10px'
                }}>Save Config</button>
                <button onClick={onCancel} className="cancel-config-btn" style={{
                    background: 'transparent',
                    color: '#ff5c8d',
                    border: '1px solid #ff5c8d',
                    borderRadius: '6px',
                    padding: '8px 16px',
                    cursor: 'pointer',
                    fontSize: '0.9rem',
                    fontWeight: '500'
                }}>Cancel</button>
            </div>
        </div>
    );
}

function WorkflowDetail() {
  const {
    selectedWorkflow,
    tasks,
    fetchTasks,
    addStepToWorkflow,
    deleteStepFromWorkflow,
    runMultiStepWorkflow,
  } = useAppContext();

  const [skipOnError, setSkipOnError] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);
  const [isStopping, setIsStopping] = useState(false);
  const [stopResult, setStopResult] = useState(null);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [editingStepId, setEditingStepId] = useState(null);
  const [newStepType, setNewStepType] = useState('delay');

  // ฟังก์ชันสำหรับลบคำว่า (Counter) หรือ ข้อความในวงเล็บออกจากชื่อ workflow
  const cleanWorkflowName = (name) => {
    return name.replace(/\s*\([^)]*\)\s*/g, '');
  };

  useEffect(() => {
    setRunResult(null);
    setStopResult(null);
    setIsRunning(false);
    setIsStopping(false);
    setActiveTaskId(null);
    setEditingStepId(null);
  }, [selectedWorkflow]);

  useEffect(() => {
    if (activeTaskId && tasks) {
      const currentActiveTask = tasks.find(task => task.id === activeTaskId);
      if (currentActiveTask) {
        if (!['running', 'pending', 'stopping'].includes(currentActiveTask.status?.toLowerCase())) {
          setActiveTaskId(null);
        }
      } else {
          setActiveTaskId(null);
      }
    } else if (activeTaskId && !tasks) {
         setActiveTaskId(null);
    }
  }, [tasks, activeTaskId]);

  const handleAddStep = () => {
      if (!selectedWorkflow) return;
      console.log('Add Step button clicked');
      console.log('Selected Workflow ID:', selectedWorkflow.id);
      console.log('New Step Type:', newStepType);
      addStepToWorkflow(selectedWorkflow.id, newStepType);
  };

  const handleDeleteStep = (stepId) => {
      if (!selectedWorkflow) return;
      if (window.confirm('Are you sure you want to delete this step?')) {
          deleteStepFromWorkflow(selectedWorkflow.id, stepId);
          if (editingStepId === stepId) {
              setEditingStepId(null);
          }
      }
  };

  const handleEditStep = (stepId) => {
      setEditingStepId(editingStepId === stepId ? null : stepId);
  };

  const handleConfigSaved = () => {
      setEditingStepId(null);
  };

  const handleRunWorkflow = async () => {
    if (!selectedWorkflow) return;
    setIsRunning(true);
    setRunResult(null);
    setStopResult(null);
    setActiveTaskId(null);

    try {
      console.log('Running multi-step workflow with ID:', selectedWorkflow.id);
      const result = await runMultiStepWorkflow(selectedWorkflow.id);
      console.log('runMultiStepWorkflow result:', result);
      setRunResult(result);

      if (result.success && result.taskId) {
        console.log("Multi-step workflow started with task ID:", result.taskId);
        setActiveTaskId(result.taskId);
      } else {
          setActiveTaskId(null);
      }
    } catch (error) {
      setActiveTaskId(null);
      setRunResult({
        success: false,
        message: `Error running workflow: ${error.message}`
      });
       console.error("Error in handleRunWorkflow:", error);
    } finally {
      setIsRunning(false);
    }
  };

  const handleStopTask = async (taskId) => {
    if (!taskId) return;

    setIsStopping(true);
    setStopResult(null);
    console.log("Requesting stop for task:", taskId);

    try {
      const response = await fetch(`/api/v1/stop-task/${taskId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json();

      if (!response.ok) {
        console.error("Stop request failed:", data.detail || 'Failed response from server');
        setStopResult({ success: false, message: `Stop request failed: ${data.detail || 'Unknown error'}` });
      } else {
         setStopResult({ success: true, message: data.message || 'Stop request sent successfully.' });
      }
       setTimeout(() => { 
         if (fetchTasks) fetchTasks(); 
         setTimeout(() => {
           setIsStopping(false);
           setActiveTaskId(null);
         }, 500);
       }, 1500);

    } catch (error) {
      console.error("Error stopping task (network/parse issue):", error);
      setStopResult({ success: false, message: `Error: ${error.message}` });
      setTimeout(() => { 
        if (fetchTasks) fetchTasks(); 
        setTimeout(() => {
      setIsStopping(false);
          setActiveTaskId(null);
        }, 500);
      }, 1500);
    }
  };

  const getLatestRun = () => {
    if (!selectedWorkflow || !tasks || tasks.length === 0) return null;
    const relatedTasks = tasks.filter(task =>
        task.description && task.description.startsWith(`${selectedWorkflow.name} (Multi-Step Run)`)
    );
    if (relatedTasks.length === 0) return null;
    relatedTasks.sort((a, b) => new Date(b.startTime) - new Date(a.startTime));
    return relatedTasks[0];
  };

  const latestRun = getLatestRun();

  const activeTask = activeTaskId ? tasks?.find(task => task.id === activeTaskId) : null;
  const isTaskStoppable = activeTask && ['running', 'pending', 'stopping'].includes(activeTask.status?.toLowerCase());

  // +++ DEBUG LOG +++
  console.log('WorkflowDetail Render - isTaskStoppable:', isTaskStoppable, 'activeTask:', activeTask, 'isRunning:', isRunning, 'selectedWorkflow:', selectedWorkflow);
  console.log('WorkflowDetail DOM Debug - Button rendering conditions check');
  console.log('Button Disabled Logic:', isRunning || !selectedWorkflow || !selectedWorkflow.steps || selectedWorkflow.steps.length === 0);
  if (selectedWorkflow) {
    console.log('Steps Check:', selectedWorkflow.steps ? `${selectedWorkflow.steps.length} steps` : 'No steps array');
  }
  // +++ END DEBUG LOG +++

  // --- Helper Function to generate descriptive text for a step ---
  const getStepDescription = (step) => {
    if (!step) return 'Unknown Step';
    const config = step.config || {};

    switch (step.type) {
      case 'delay':
        return `Delay for ${config.duration_seconds || '?'} seconds`;
      case 'stake':
        return `Stake ${config.amount_mon || '?'} MON (${config.contract_type || 'kitsu'})`;
      case 'swap':
        // Use amount_str for swap as per config
        return `Swap ${config.amount_str || '?'} ${config.token_from_symbol || '?'} to ${config.token_to_symbol || '?'}`;
      case 'deploy':
        return `Deploy Contract: ${config.contract_name || '?'}`;
      case 'send':
        return `Send ${config.amount_mon || '?'} MON ${config.mode === 'single' ? `to ${config.recipient_address || '?'}` : '(Random Recipient)'}`;
      case 'bebop':
        return `Bebop: Wrap/Unwrap ${config.amount_mon || '?'} MON`;
      case 'izumi':
        return `Izumi: Wrap/Unwrap ${config.amount_mon || '?'} MON`;
      case 'lilchogstars':
        return `Mint Lilchogstars (Qty: ${config.quantity || '?'})`;
      case 'mono':
        return `Mono Transaction: Send ${config.value_mon || '?'} MON to ${config.recipient_address || '?'}`;
      case 'rubic':
        return `Rubic: Swap ${config.amount_mon || '?'} MON to USDT`;
      case 'ambient':
        const inToken = config.token_in_symbol || 'Random';
        const outToken = config.token_out_symbol || 'Random';
        return `Ambient: Swap ${config.amount_percent || 100}% ${inToken} to ${outToken}`;
      case 'apriori':
        return `Apriori: Full Stake/Unstake/Claim Cycle`;
      case 'bean':
        const beanDir = config.direction === 'to_token' ? `MON to ${config.token_symbol || '?'}` : `${config.token_symbol || '?'} to MON`;
        // Use amount (float) for bean as per config
        return `Bean: Swap ${config.amount || '?'} (${beanDir})`;
      case 'bima':
        const lendPercent = config.percent_to_lend ? `${config.percent_to_lend[0]}-${config.percent_to_lend[1]}%` : 'Default %';
        return `Bima: Lend Cycle (${lendPercent})`;
      default:
        return `Unknown Step Type: ${step.type}`;
    }
  };

  return (
    <div className="workflow-detail" style={{ maxWidth: '1000px', margin: '0 auto' }}>
      {!selectedWorkflow ? (
        <div style={{
          padding: '60px 30px',
          textAlign: 'center',
          color: '#6c757d',
          backgroundColor: 'white',
          borderRadius: '12px',
          border: '1px solid #e9ecef',
          boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '20px', color: '#d1d5db' }}>📋</div>
          <p style={{ fontSize: '1rem', fontWeight: '500' }}>No workflow selected. Please select a workflow from the list.</p>
        </div>
      ) : (
        <>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
            padding: '18px 24px',
            backgroundColor: 'white',
            borderRadius: '12px',
            border: '1px solid #e9ecef',
            boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
            transition: 'box-shadow 0.3s ease'
          }}>
            <div>
              <h2 style={{ 
                margin: 0, 
                fontSize: '1.4rem', 
                fontWeight: '600', 
                color: '#212529',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}>
                <span style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  backgroundColor: '#ffe5ec',
                  color: '#ff5c8d',
                  fontSize: '1rem'
                }}>
                  📋
                </span>
                {cleanWorkflowName(selectedWorkflow.name)}
              </h2>
              
              {latestRun && (
                <div style={{ 
                  marginTop: '8px',
                  fontSize: '0.85rem',
                  color: '#6c757d',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ fontSize: '0.8rem' }}>⏱️</span>
                    Last run:
                  </span>
                  <span style={{ 
                    padding: '3px 10px',
                    borderRadius: '100px',
                    backgroundColor: latestRun.status?.toLowerCase() === 'completed' ? '#d1e7dd' :
                                      latestRun.status?.toLowerCase() === 'running' ? '#cfe2ff' :
                                      latestRun.status?.toLowerCase() === 'failed' ? '#f8d7da' : '#e9ecef',
                    color: latestRun.status?.toLowerCase() === 'completed' ? '#146c43' :
                           latestRun.status?.toLowerCase() === 'running' ? '#0a58ca' :
                           latestRun.status?.toLowerCase() === 'failed' ? '#dc3545' : '#6c757d',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    letterSpacing: '0.3px'
                  }}>
                    {latestRun.status}
                  </span>
                  <span style={{ color: '#adb5bd' }}>•</span>
                  <span>{new Date(latestRun.startTime).toLocaleTimeString()}</span>
              </div>
              )}
            </div>
            
            <button
              onClick={isTaskStoppable && !isStopping ? handleStopTask.bind(null, activeTaskId) : handleRunWorkflow}
              style={{
                background: isTaskStoppable && !isStopping ? 
                  'linear-gradient(to right, #dc3545, #e35d6a)' : 
                  'linear-gradient(to right, #ffb6c1, #ffc8d0)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                padding: '10px 20px',
                fontWeight: '600',
                cursor: 'pointer',
                fontSize: '0.95rem',
                opacity: (isRunning || isStopping || (activeTask?.status?.toLowerCase() !== 'completed' && activeTask?.status?.toLowerCase() !== 'failed' && activeTaskId !== null) || !selectedWorkflow || !selectedWorkflow.steps || selectedWorkflow.steps.length === 0) && !(isTaskStoppable && !isStopping) ? '0.6' : '1',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 2px 6px rgba(0,0,0,0.1)'
              }}
              disabled={(isRunning || isStopping || (activeTask?.status?.toLowerCase() !== 'completed' && activeTask?.status?.toLowerCase() !== 'failed' && activeTaskId !== null) || !selectedWorkflow || !selectedWorkflow.steps || selectedWorkflow.steps.length === 0) && !(isTaskStoppable && !isStopping)}
            >
              <span style={{ 
                fontSize: '1rem',
                display: 'flex',
                alignItems: 'center'
              }}>
                {isTaskStoppable && !isStopping ? '⏹️' : 
                 isRunning || isStopping ? '⏳' : '▶️'}
              </span>
              {isTaskStoppable && !isStopping ? 'Stop' : 
               isRunning || isStopping ? 'Starting...' : 'Run now'}
            </button>
          </div>
          
          {/* Status Messages */}
          {(runResult || stopResult) && (
            <div style={{
              marginBottom: '20px',
              padding: '14px 20px',
              borderRadius: '12px',
              backgroundColor: runResult?.success || stopResult?.success ? '#e7f3e8' : '#f8d7da',
              border: '1px solid',
              borderColor: runResult?.success || stopResult?.success ? '#c3e6cb' : '#f5c6cb',
              color: runResult?.success || stopResult?.success ? '#155724' : '#721c24',
              fontSize: '0.95rem',
              boxShadow: '0 2px 5px rgba(0,0,0,0.03)',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <span style={{ 
                fontSize: '1.2rem' 
              }}>
                {runResult?.success || stopResult?.success ? '✅' : '❗'}
              </span>
              <div>
                {runResult && runResult.message}
                {stopResult && stopResult.message}
            </div>
            </div>
          )}
          
          {/* Workflow Steps Section */}
          <div style={{ 
            backgroundColor: 'white',
            borderRadius: '12px',
            border: '1px solid #e9ecef',
            padding: '20px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
            transition: 'box-shadow 0.3s ease'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              borderBottom: '1px solid #e9ecef',
              paddingBottom: '14px',
              marginBottom: '20px'
            }}>
              <h3 style={{ 
                margin: 0, 
                fontSize: '1.1rem', 
                fontWeight: '600',
                color: '#212529',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '26px',
                  height: '26px',
                  borderRadius: '6px',
                  backgroundColor: '#ffe5ec',
                  color: '#ff5c8d',
                  fontSize: '0.9rem'
                }}>
                  🔄
                </span>
                Workflow Steps: {cleanWorkflowName(selectedWorkflow.name)}
              </h3>
              
              {selectedWorkflow.steps && (
                <div style={{ 
                  fontSize: '0.9rem', 
                  color: '#6c757d',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 12px',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '100px'
                }}>
                  <span style={{ fontWeight: '600', color: '#495057' }}>
                    {selectedWorkflow.steps.length}
                </span>
                  step{selectedWorkflow.steps.length !== 1 ? 's' : ''}
            </div>
          )}
            </div>
            
            {(!selectedWorkflow.steps || selectedWorkflow.steps.length === 0) ? (
              <div style={{
                padding: '30px 20px',
                backgroundColor: '#f8f9fa',
                borderRadius: '10px',
                textAlign: 'center',
                color: '#6c757d',
                fontSize: '0.95rem',
                marginBottom: '20px',
                border: '1px dashed #dee2e6'
              }}>
                <div style={{ fontSize: '2rem', marginBottom: '15px', color: '#d1d5db' }}>🔍</div>
                <p style={{ margin: 0, fontWeight: '500' }}>No steps defined for this workflow yet.</p>
                <p style={{ margin: '6px 0 0 0', color: '#adb5bd' }}>Add your first step below to get started.</p>
              </div>
            ) : (
              <div style={{ marginBottom: '24px' }}>
                {selectedWorkflow.steps.map((step, index) => (
                  <div 
                    key={step.step_id}
                    style={{
                      backgroundColor: '#f8f9fa',
                      borderRadius: '10px',
                      marginBottom: index < selectedWorkflow.steps.length - 1 ? '12px' : 0,
                      overflow: 'hidden',
                      border: '1px solid #e9ecef',
                      transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '14px 18px',
                      borderBottom: editingStepId === step.step_id ? '1px solid #e9ecef' : 'none'
                    }}>
                      <div style={{
                        fontWeight: '600',
                        marginRight: '14px',
                        color: '#ff5c8d',
                        fontSize: '0.85rem',
                        backgroundColor: 'white',
                        borderRadius: '8px',
                        width: '28px',
                        height: '28px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: '1px solid #e9ecef',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
                      }}>
                        {index + 1}
            </div>
                      <div style={{
                        flex: 1,
                        fontSize: '0.95rem',
                        fontWeight: '500',
                        color: '#343a40',
                        display: 'flex',
                        alignItems: 'center'
                      }}>
                        <span style={{ marginRight: '10px' }}>
                          {step.type === 'delay' ? '⏱️' :
                           step.type === 'stake' ? '💰' :
                           step.type === 'swap' ? '🔄' :
                           step.type === 'deploy' ? '🚀' :
                           step.type === 'send' ? '📤' :
                           step.type === 'bebop' || step.type === 'izumi' ? '🔄' :
                           step.type === 'lilchogstars mint' ? '🎨' :
                           step.type === 'mono' ? '💸' :
                           step.type === 'rubic' ? '💱' :
                           step.type === 'ambient' ? '💹' :
                           step.type === 'apriori' ? '⚡' :
                           step.type === 'bean' ? '🌱' :
                           step.type === 'bima' ? '💳' : '📋'}
                        </span>
                        {getStepDescription(step)}
          </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                        title="Edit step configuration"
                        onClick={() => handleEditStep(step.step_id)}
                          style={{
                            background: 'linear-gradient(to right, #ff5c8d, #ff8fab)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                            fontWeight: '500',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            transition: 'all 0.2s ease'
                          }}
                        >
                          <span style={{ fontSize: '0.9rem' }}>✏️</span>
                          Edit
                    </button>
                    <button
                        title="Delete step"
                        onClick={() => handleDeleteStep(step.step_id)}
                          style={{
                            background: 'transparent',
                            color: '#ff5c8d',
                            border: '1px solid #ff5c8d',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                            fontWeight: '500',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            transition: 'all 0.2s ease'
                          }}
                          onMouseOver={(e) => {
                            e.currentTarget.style.backgroundColor = '#fff0f3';
                          }}
                          onMouseOut={(e) => {
                            e.currentTarget.style.backgroundColor = 'transparent';
                          }}
                        >
                          <span style={{ fontSize: '0.9rem' }}>🗑️</span>
                          Delete
                    </button>
                  </div>
                </div>
                
                {editingStepId === step.step_id && (
                      <div style={{
                        padding: '20px',
                        background: 'white',
                        borderTop: '1px solid #e9ecef'
                      }}>
                      <StepConfigEditor
                          workflowId={selectedWorkflow.id}
                          step={step}
                          onConfigChange={handleConfigSaved}
                          onCancel={() => setEditingStepId(null)}
                      />
                  </div>
                )}
              </div>
            ))}
              </div>
            )}
            
            {/* Add Step Control */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              borderTop: (!selectedWorkflow.steps || selectedWorkflow.steps.length === 0) ? 'none' : '1px solid #e9ecef',
              paddingTop: (!selectedWorkflow.steps || selectedWorkflow.steps.length === 0) ? '0' : '20px'
            }}>
               <select
                  value={newStepType}
                  onChange={(e) => setNewStepType(e.target.value)}
                style={{
                  flex: '1',
                  padding: '10px 14px',
                  border: '1px solid #ced4da',
                  borderRadius: '8px',
                  fontSize: '0.95rem',
                  color: '#495057',
                  backgroundColor: 'white',
                  outline: 'none',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.02)',
                  transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
                }}
              >
                <option value="delay">⏱️ Delay</option>
                <option value="stake">💰 kitsu Stake</option>
                <option value="swap">🔄 UniSwap</option>
                <option value="deploy">🚀 Deploy Contract</option>
                <option value="send">📤 Send MON</option>
                <option value="bebop">🔄 Bebop</option>
                <option value="izumi">🔄 Izumi</option>
                <option value="lilchogstars">🎨 Lilchogstars Mint</option>
                <option value="mono">💸 Mono</option>
                <option value="rubic">💱 Rubic</option>
                <option value="ambient">💹 Ambient</option>
                <option value="apriori">⚡ Apriori</option>
                <option value="bean">🌱 Bean</option>
                <option value="bima">💳 Bima</option>
               </select>
              <button 
                onClick={handleAddStep}
                style={{
                  background: 'linear-gradient(to right, #ffb6c1, #ffc8d0)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '10px 20px',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.2s ease',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.boxShadow = '0 2px 6px rgba(0,0,0,0.1)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <span style={{ fontSize: '1.1rem' }}>+</span>
                Add Step
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default WorkflowDetail; 