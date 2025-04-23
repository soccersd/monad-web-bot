import React, { useState, useEffect } from 'react';
import { useAppContext } from '../context/AppContext';
import './LogsPage.css';

function LogsPage() {
  const { tasks, isLoadingTasks, taskError, fetchTasks } = useAppContext();
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');

  // API base URL from environment or default
  const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

  // Fetch details for a specific task
  const fetchTaskDetails = async (taskId) => {
    if (!taskId) return;
    
    setIsLoadingDetails(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch task details for ID: ${taskId}`);
      }
      const data = await response.json();
      setSelectedTask(data);
      setDetailsError(null);
    } catch (err) {
      setDetailsError(err.message);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  // Auto-select the newest task when tasks are loaded or changed
  useEffect(() => {
    if (tasks.length > 0 && !selectedTaskId) {
      setSelectedTaskId(tasks[0].id);
    }
  }, [tasks, selectedTaskId]);

  // Fetch details when a task is selected
  useEffect(() => {
    if (selectedTaskId) {
      fetchTaskDetails(selectedTaskId);
      
      // Set up polling for in-progress tasks
      const pollInterval = setInterval(() => {
        if (selectedTask && selectedTask.status?.toLowerCase() !== 'completed' && selectedTask.status?.toLowerCase() !== 'failed') {
          fetchTaskDetails(selectedTaskId);
        }
      }, 5000);
      
      return () => clearInterval(pollInterval);
    }
  }, [selectedTaskId, selectedTask?.status]);

  const handleTaskSelect = (taskId) => {
    setSelectedTaskId(taskId);
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    if (timestamp instanceof Date) {
      return timestamp.toLocaleString();
    }
    return new Date(timestamp).toLocaleString();
  };

  const getStatusBadge = (status) => {
    const statusLower = status?.toLowerCase() || 'pending';
    let badgeColor = '#e9ecef'; // Default gray
    let textColor = '#6c757d';
    
    switch (statusLower) {
      case 'running':
        badgeColor = '#cfe2ff';
        textColor = '#0a58ca';
        break;
      case 'completed':
        badgeColor = '#d1e7dd';
        textColor = '#146c43';
        break;
      case 'failed':
        badgeColor = '#f8d7da';
        textColor = '#dc3545';
        break;
      default:
        break;
    }
    
    return (
      <span style={{
        display: 'inline-block',
        padding: '0.2rem 0.5rem',
        borderRadius: '4px',
        fontSize: '0.75rem',
        fontWeight: '500',
        backgroundColor: badgeColor,
        color: textColor,
        textAlign: 'center',
        minWidth: '80px',
        whiteSpace: 'nowrap'
      }}>
        {statusLower === 'running' ? 'Running' : 
          statusLower === 'completed' ? 'Completed' : 
          statusLower === 'failed' ? 'Failed' : 'Pending'}
      </span>
    );
  };

  // Filter tasks based on selected status
  const filteredTasks = tasks.filter(task => {
    if (filterStatus === 'all') return true;
    return task.status?.toLowerCase() === filterStatus;
  });

  return (
    <div style={{ 
      height: '100%',
      display: 'flex',
      flexDirection: 'column' 
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px'
      }}>
        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: '600' }}>Task Logs</h2>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setFilterStatus('all')}
            style={{
              backgroundColor: filterStatus === 'all' ? '#ffedf2' : 'transparent',
              border: '1px solid #ffd6df',
              color: filterStatus === 'all' ? '#ffb6c1' : '#333',
              padding: '4px 10px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: filterStatus === 'all' ? '600' : '400',
              marginRight: '4px'
            }}
          >
            All
          </button>
          <button
            onClick={() => setFilterStatus('pending')}
            style={{
              backgroundColor: filterStatus === 'pending' ? '#ffedf2' : 'transparent',
              border: '1px solid #ffd6df',
              color: filterStatus === 'pending' ? '#ffb6c1' : '#333',
              padding: '4px 10px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: filterStatus === 'pending' ? '600' : '400',
              marginRight: '4px'
            }}
          >
            Pending
          </button>
          <button
            onClick={() => setFilterStatus('running')}
            style={{
              backgroundColor: filterStatus === 'running' ? '#ffedf2' : 'transparent',
              border: '1px solid #ffd6df',
              color: filterStatus === 'running' ? '#ffb6c1' : '#333',
              padding: '4px 10px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: filterStatus === 'running' ? '600' : '400',
              marginRight: '4px'
            }}
          >
            Running
          </button>
          <button
            onClick={() => setFilterStatus('completed')}
            style={{
              backgroundColor: filterStatus === 'completed' ? '#ffedf2' : 'transparent',
              border: '1px solid #ffd6df',
              color: filterStatus === 'completed' ? '#ffb6c1' : '#333',
              padding: '4px 10px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: filterStatus === 'completed' ? '600' : '400'
            }}
          >
            Completed
          </button>
          <button
            onClick={() => setFilterStatus('failed')}
            style={{
              backgroundColor: filterStatus === 'failed' ? '#ffedf2' : 'transparent',
              border: '1px solid #ffd6df',
              color: filterStatus === 'failed' ? '#ffb6c1' : '#333',
              padding: '4px 10px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem', 
              fontWeight: filterStatus === 'failed' ? '600' : '400'
            }}
          >
            Failed
          </button>
          <button
            onClick={fetchTasks}
            style={{
              backgroundColor: 'transparent',
              border: '1px solid #ffd6df',
              color: '#333',
              padding: '4px 10px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              marginLeft: '8px'
            }}
          >
            {isLoadingTasks ? 'Refreshing...' : '↻ Refresh'}
          </button>
        </div>
      </div>
      
      <div style={{
        display: 'grid',
        gridTemplateColumns: '350px 1fr',
        gap: '16px',
        flex: '1',
        overflow: 'hidden'
      }}>
        {/* Task List */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          border: '1px solid #e9ecef',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            borderBottom: '1px solid #e9ecef',
            paddingBottom: '12px',
            marginBottom: '12px'
          }}>
            <h3 style={{ 
              margin: 0, 
              fontSize: '0.9rem', 
              fontWeight: '600' 
            }}>
              Recent Tasks
            </h3>
            <span style={{ 
              fontSize: '0.8rem', 
              color: '#6c757d',
              marginTop: '2px'
            }}>
              {filteredTasks.length} {filteredTasks.length === 1 ? 'task' : 'tasks'}
            </span>
          </div>
          
          {isLoadingTasks && tasks.length === 0 ? (
            <div style={{ 
              padding: '20px',
              textAlign: 'center',
              color: '#6c757d'
            }}>
              Loading tasks...
            </div>
          ) : filteredTasks.length === 0 ? (
            <div style={{ 
              padding: '20px',
              textAlign: 'center',
              color: '#6c757d'
            }}>
              No {filterStatus !== 'all' ? filterStatus : ''} tasks found
            </div>
          ) : (
            <div style={{ 
              overflow: 'auto',
              flex: '1'
            }}>
              {filteredTasks.map((task) => (
                <div 
                  key={task.id} 
                  onClick={() => handleTaskSelect(task.id)}
                  style={{
                    padding: '12px',
                    marginBottom: '6px',
                    borderRadius: '6px',
                    backgroundColor: selectedTaskId === task.id ? '#f0ebfa' : 'white',
                    cursor: 'pointer',
                    borderLeft: selectedTaskId === task.id ? '3px solid #8359d4' : '3px solid transparent',
                    transition: 'background-color 0.15s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    {getStatusBadge(task.status)}
                    <span style={{ 
                      fontSize: '0.75rem',
                      color: '#6c757d' 
                    }}>
                      {formatTimestamp(task.startTime || task.start_time).split(' ')[1]}
                    </span>
                  </div>
                  <div style={{
                    fontWeight: '500',
                    fontSize: '0.85rem',
                    color: '#343a40',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {task.task_type || task.description || 'Task'}
                  </div>
                  <div style={{
                    fontSize: '0.75rem',
                    color: '#6c757d'
                  }}>
                    ID: {task.id.substring(0, 8)}...
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Task Details */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          border: '1px solid #e9ecef',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden'
        }}>
          <div style={{
            borderBottom: '1px solid #e9ecef',
            paddingBottom: '12px',
            marginBottom: '12px'
          }}>
            <h3 style={{ 
              margin: 0, 
              fontSize: '0.9rem', 
              fontWeight: '600' 
            }}>
              Task Details
            </h3>
          </div>
          
          {taskError && (
            <div style={{
              backgroundColor: '#f8d7da',
              color: '#721c24',
              padding: '8px 12px',
              marginBottom: '16px',
              borderRadius: '4px',
              fontSize: '0.85rem',
              border: '1px solid #f5c6cb'
            }}>
              {taskError}
            </div>
          )}
          
          {detailsError && (
            <div style={{
              backgroundColor: '#f8d7da',
              color: '#721c24',
              padding: '8px 12px',
              marginBottom: '16px',
              borderRadius: '4px',
              fontSize: '0.85rem',
              border: '1px solid #f5c6cb'
            }}>
              {detailsError}
            </div>
          )}
          
          {isLoadingDetails && (
            <div style={{ 
              padding: '40px 0',
              textAlign: 'center',
              color: '#6c757d',
              flex: '1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              Loading details...
            </div>
          )}
          
          {!isLoadingDetails && selectedTask && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              height: '100%'
            }}>
              <div style={{
                backgroundColor: '#f8f9fa',
                borderRadius: '6px',
                padding: '12px',
                marginBottom: '16px'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '12px'
                }}>
                  <div style={{
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                    color: '#6c757d'
                  }}>
                    ID: {selectedTask.id || selectedTask.task_id}
                  </div>
                  {getStatusBadge(selectedTask.status)}
                </div>
                
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'auto 1fr',
                  gap: '8px 24px',
                  fontSize: '0.85rem'
                }}>
                  <div style={{ fontWeight: '600', color: '#495057' }}>Type:</div>
                  <div>{selectedTask.task_type || selectedTask.description || 'Task'}</div>
                  
                  <div style={{ fontWeight: '600', color: '#495057' }}>Started:</div>
                  <div>{formatTimestamp(selectedTask.start_time)}</div>
                  
                  {selectedTask.end_time && (
                    <>
                      <div style={{ fontWeight: '600', color: '#495057' }}>Completed:</div>
                      <div>{formatTimestamp(selectedTask.end_time)}</div>
                    </>
                  )}
                  
                  {selectedTask.description && (
                    <>
                      <div style={{ fontWeight: '600', color: '#495057' }}>Description:</div>
                      <div>{selectedTask.description}</div>
                    </>
                  )}
                </div>
              </div>
              
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                flex: '1',
                overflow: 'hidden'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px'
                }}>
                  <h4 style={{ 
                    margin: 0, 
                    fontSize: '0.9rem', 
                    fontWeight: '600' 
                  }}>
                    Logs
                  </h4>
                  {selectedTask.logs && (
                    <span style={{ 
                      fontSize: '0.8rem', 
                      color: '#6c757d' 
                    }}>
                      {selectedTask.logs.length} entries
                    </span>
                  )}
                </div>
                
                <div style={{
                  backgroundColor: '#f1f3f5',
                  borderRadius: '6px',
                  padding: '12px',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  flex: '1',
                  overflow: 'auto',
                  border: '1px solid #e9ecef'
                }}>
                  {selectedTask.logs && selectedTask.logs.length > 0 ? (
                    selectedTask.logs.map((log, index) => (
                      <div 
                        key={index}
                        style={{
                          marginBottom: '4px',
                          lineHeight: '1.4',
                          display: 'flex',
                          alignItems: 'baseline',
                          gap: '8px'
                        }}
                      >
                        <span style={{
                          color: '#6c757d',
                          fontSize: '0.75rem',
                          whiteSpace: 'nowrap'
                        }}>
                          {formatTimestamp(log.timestamp).split(' ')[1]}
                        </span>
                        <span style={{
                          color: log.level === 'error' ? '#dc3545' : 
                                 log.level === 'warning' ? '#fd7e14' : 
                                 log.level === 'debug' ? '#6c757d' : '#212529'
                        }}>
                          {log.message}
                        </span>
                </div>
                    ))
                  ) : (
                    <div style={{ 
                      color: '#6c757d',
                      fontStyle: 'italic',
                      textAlign: 'center',
                      padding: '20px 0'
                    }}>
                      No logs available
                  </div>
                )}
              </div>
              </div>
            </div>
          )}
          
          {!isLoadingDetails && !selectedTask && !detailsError && (
            <div style={{ 
              padding: '40px 0',
              textAlign: 'center',
              color: '#6c757d',
              flex: '1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              Select a task to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default LogsPage; 