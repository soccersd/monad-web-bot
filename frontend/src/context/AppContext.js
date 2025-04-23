import React, { createContext, useState, useContext, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid'; // Import UUID for step IDs

// Define API base URL
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Mock data for workflows (Added initial empty steps array)
const MOCK_WORKFLOWS = [
  { id: 1, name: 'Kitsu Stake', type: 'stake', contractType: 'kitsu', steps: [] },
  { id: 2, name: 'NFT Minter (Counter)', type: 'deploy', contractType: 'counter', steps: [] },
  { id: 3, name: 'Uniswap Swap', type: 'swap', fromToken: 'ETH', toToken: 'USDC', steps: [] },
  { id: 4, name: 'Send MON', type: 'send', mode: 'random', steps: [] },
  { id: 5, name: 'Bebop Wrap/Unwrap', type: 'bebop', steps: [] },
  { id: 6, name: 'Izumi Wrap/Unwrap', type: 'izumi', steps: [] },
  { id: 7, name: 'Lilchogstars Mint', type: 'lilchogstars', steps: [] },
  { id: 8, name: 'Mono Transaction', type: 'mono', steps: [] },
  { id: 9, name: 'Rubic Swap MON->USDT', type: 'rubic', steps: [] },
  { id: 10, name: 'Ambient Swap (Random)', type: 'ambient', steps: [] },
  { id: 11, name: 'Apriori Full Cycle', type: 'apriori', steps: [] },
  { id: 12, name: 'Bean Swap (MON->USDC)', type: 'bean', steps: [] },
  { id: 13, name: 'Bima Lend', type: 'bima', steps: [] }
];

// Create the context
const AppContext = createContext();

// Provider component that wraps the app
export const AppProvider = ({ children }) => {
  // Workflows state - using MOCK for now, but steps can be modified
  const [workflows, setWorkflows] = useState(MOCK_WORKFLOWS);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState(2); // Default to NFT Minter

  // Wallets state
  const [wallets, setWallets] = useState([]);
  const [isLoadingWallets, setIsLoadingWallets] = useState(false);
  const [walletError, setWalletError] = useState(null);
  const [isImportingWallet, setIsImportingWallet] = useState(false);
  const [newWalletImport, setNewWalletImport] = useState({ privateKey: '', nickname: '' });

  // Tasks/runs state
  const [tasks, setTasks] = useState([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [taskError, setTaskError] = useState(null);

  // Get the selected workflow object
  const selectedWorkflow = workflows.find(w => w.id === selectedWorkflowId) || workflows[0];

  // Get selected wallets
  const selectedWallets = wallets.filter(w => w.selected);

  // --- Workflow Selection ---
  const selectWorkflow = (id) => {
    setSelectedWorkflowId(id);
  };

  // --- Wallet Management ---
  const toggleWalletSelection = (id) => {
    setWallets(wallets.map(wallet =>
      wallet.id === id ? { ...wallet, selected: !wallet.selected } : wallet
    ));
  };

  const importWallet = async (privateKey, nickname = '') => {
    setIsImportingWallet(true);
    setWalletError(null);
    try {
      if (!privateKey.startsWith('0x') || privateKey.length !== 66) {
        throw new Error('Invalid private key format (must be 0x followed by 64 hex chars)');
      }
      const addressResponse = await fetch(`${API_BASE_URL}/api/v1/get-address-from-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ private_key: privateKey }),
      });
      if (!addressResponse.ok) {
        let errorMsg = 'Failed to derive address from key.';
        try { const errorData = await addressResponse.json(); errorMsg = errorData.detail || errorMsg; } catch { /* Ignore */ }
        throw new Error(errorMsg);
      }
      const addressData = await addressResponse.json();
      const realAddress = addressData.address;
      if (wallets.some(w => w.address === realAddress)) {
        throw new Error(`Wallet with address ${realAddress} already exists.`);
      }
      const newWallet = {
        id: wallets.length > 0 ? Math.max(...wallets.map(w => w.id)) + 1 : 1,
        address: realAddress,
        privateKey: privateKey,
        balance: null,
        selected: true,
        nickname: nickname || `Wallet ${realAddress.substring(0, 6)}...`
      };
      setWallets(prevWallets => [...prevWallets, newWallet]);
      setNewWalletImport({ privateKey: '', nickname: '' });
      await fetchWalletBalance(newWallet.id, newWallet.address);
      return { success: true, message: 'Wallet imported successfully' };
    } catch (error) {
      console.error('Error importing wallet:', error);
      setWalletError(`Failed to import wallet: ${error.message}`);
      return { success: false, message: error.message };
    } finally {
      setIsImportingWallet(false);
    }
  };

  const fetchWalletBalances = async () => {
    setIsLoadingWallets(true);
    setWalletError(null);
    const balancePromises = wallets.map(wallet => fetchWalletBalance(wallet.id, wallet.address));
    try {
      await Promise.all(balancePromises);
    } catch (error) {
      console.error('Error fetching some wallet balances:', error);
    } finally {
      setIsLoadingWallets(false);
    }
  };

  const fetchWalletBalance = async (walletId, walletAddress) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/get-balance/${walletAddress}`);
      if (!response.ok) {
        let errorMsg = `Failed to fetch balance for ${walletAddress}. Status: ${response.status}`;
        try { const errorData = await response.json(); errorMsg = `${errorMsg} - ${errorData.detail || 'Unknown error'}`; } catch { /* Ignore */ }
        throw new Error(errorMsg);
      }
      const data = await response.json();
      const balance = data.balance;
      setWallets(prevWallets =>
        prevWallets.map(wallet =>
          wallet.id === walletId ? { ...wallet, balance: balance } : wallet
        )
      );
    } catch (error) {
      console.error(`Error fetching balance for wallet ${walletAddress} (ID: ${walletId}):`, error);
      setWallets(prevWallets =>
        prevWallets.map(wallet =>
          wallet.id === walletId ? { ...wallet, balance: 'Error' } : wallet
        )
      );
      throw error;
    }
  };

  const handleWalletImportChange = (field, value) => {
    setNewWalletImport(prev => ({ ...prev, [field]: value }));
  };

  const deleteWallet = (id) => {
    setWallets(prevWallets => prevWallets.filter(wallet => wallet.id !== id));
    // TODO: Optionally call a backend endpoint to delete server-side if needed
  };

  // --- Task Management ---
  const fetchTasks = async () => {
    setIsLoadingTasks(true);
    setTaskError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/tasks`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      const tasksData = Object.entries(data.tasks || {}).map(([id, task]) => ({
        id, // Use the task ID from the backend object key
        ...task,
        startTime: new Date(task.start_time),
        // Ensure steps array exists in task data if provided by backend
        steps: task.steps || [],
      }));
      tasksData.sort((a, b) => b.startTime - a.startTime);
      setTasks(tasksData);
    } catch (error) {
      console.error("Failed to fetch tasks:", error);
      setTaskError(`Error fetching tasks: ${error.message}`);
      setTasks([]);
    } finally {
      setIsLoadingTasks(false);
    }
  };

  // --- Workflow Step Management ---
  const addStepToWorkflow = (workflowId, stepType) => {
      console.log('AppContext: addStepToWorkflow called with:', workflowId, stepType); // DEBUG
      setWorkflows(prevWorkflows => {
          const updatedWorkflows = prevWorkflows.map(w => {
              if (w.id === workflowId) {
                  const newStep = {
                      step_id: uuidv4(), // Generate a unique ID for the step
                      type: stepType,
                      config: getDefaultConfigForStepType(stepType), // Get default config based on type
                  };
                  // Ensure steps array exists before spreading
                  const existingSteps = Array.isArray(w.steps) ? w.steps : [];
                  return { ...w, steps: [...existingSteps, newStep] };
              }
              return w;
          });
          console.log('AppContext: Workflows state AFTER update:', updatedWorkflows); // DEBUG
          return updatedWorkflows;
        }
      );
  };

  const deleteStepFromWorkflow = (workflowId, stepId) => {
       console.log('AppContext: deleteStepFromWorkflow called with:', workflowId, stepId); // DEBUG
      setWorkflows(prevWorkflows =>
          prevWorkflows.map(w => {
              if (w.id === workflowId) {
                   // Ensure steps array exists before filtering
                  const existingSteps = Array.isArray(w.steps) ? w.steps : [];
                  return { ...w, steps: existingSteps.filter(step => step.step_id !== stepId) };
              }
              return w;
          })
      );
  };

  const updateStepConfig = (workflowId, stepId, newConfig) => {
       console.log('AppContext: updateStepConfig called with:', workflowId, stepId, newConfig); // DEBUG
      setWorkflows(prevWorkflows =>
          prevWorkflows.map(w => {
              if (w.id === workflowId) {
                  // Ensure steps array exists before mapping
                  const existingSteps = Array.isArray(w.steps) ? w.steps : [];
                  return {
                      ...w,
                      steps: existingSteps.map(step =>
                          step.step_id === stepId ? { ...step, config: newConfig } : step
                      )
                  };
              }
              return w;
          })
      );
  };

  // Helper to get default config for a new step
  const getDefaultConfigForStepType = (stepType) => {
      console.log('AppContext: getDefaultConfigForStepType called with:', stepType); // DEBUG
      switch (stepType) {
          case 'delay': return { duration_seconds: 60 };
          case 'stake': return { contract_type: 'kitsu', amount: '0.1', amount_mon: 0.1 }; // amount_mon for backend maybe?
          case 'swap': return { token_from_symbol: 'MON', token_to_symbol: 'USDC', amount_str: '1' };
          case 'deploy': return { contract_name: 'MyCounter', contract_symbol: 'MCT' };
          case 'send': return { amount_mon: 0.001, mode: 'random' };
          case 'bebop': return { amount_mon: 0.01 };
          case 'izumi': return { amount_mon: 0.01 };
          case 'lilchogstars': return { quantity: 1 };
          case 'mono': return { recipient_address: '0x052135aBEc9A037C15554dEC1ca60a5B5aD88e52', value_mon: 0.005 };
          case 'rubic': return { amount_mon: 0.01 };
          case 'ambient': return { amount_percent: 100.0 }; // token_in/out default to null/random
          case 'apriori': return {}; // No specific config needed for full cycle step
          case 'bean': return { direction: 'to_token', token_symbol: 'USDC', amount: 0.001 };
          case 'bima': return {}; // percent_to_lend defaults to null/backend default
          default: return {};
      }
  };

  // --- Run Multi-Step Workflow ---
  const runMultiStepWorkflow = async (workflowId, rpcUrl = 'https://testnet-rpc.monad.xyz/', delayBetweenKeys = 5) => {
    const workflowToRun = workflows.find(w => w.id === workflowId);
    if (!workflowToRun || selectedWallets.length === 0) {
        console.error("runMultiStepWorkflow Error: Workflow not found or no wallets selected", workflowToRun, selectedWallets);
        return { success: false, message: "Workflow not found or no wallets selected" };
    }
     // Ensure steps array exists
    const stepsToRun = Array.isArray(workflowToRun.steps) ? workflowToRun.steps : [];
    if (stepsToRun.length === 0) {
         console.error("runMultiStepWorkflow Error: Workflow has no steps defined");
        return { success: false, message: "Workflow has no steps defined" };
    }

    console.log("Running multi-step workflow:", workflowToRun.name);
    console.log("Steps:", stepsToRun);
    console.log("Selected Wallets:", selectedWallets.map(w => w.address));

    const payload = {
        private_keys: selectedWallets.map(w => w.privateKey),
        rpc_url: rpcUrl, // Allow override later if needed
        task_description: `${workflowToRun.name} (Multi-Step Run)`, // More specific description
        delay_between_keys_seconds: delayBetweenKeys, // Use provided or default
        steps: stepsToRun.map(step => ({ // Ensure payload matches backend model
            step_id: step.step_id,
            type: step.type,
            // Make sure config is not null/undefined before sending
            config: step.config || {},
        }))
    };

    console.log("Sending payload to backend:", payload);

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/start-multi-step-workflow`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        const result = await response.json();
        console.log("Backend response:", response.status, result);

        if (!response.ok) {
            throw new Error(result.detail || `HTTP error! status: ${response.status}`);
        }

        console.log("Multi-step workflow started successfully:", result);
        // Fetch tasks again to show the newly started task
        await fetchTasks();
        return { success: true, message: "Workflow started successfully", taskId: result.task_id };

    } catch (error) {
        console.error("Failed to start multi-step workflow:", error);
        setTaskError(`Error starting workflow: ${error.message}`); // Display error to user
        return { success: false, message: `Failed to start workflow: ${error.message}` };
    }
  };

  // --- (DEPRECATED/Optional) Old Run Workflow ---
  // Keep or remove based on whether single-step endpoints are still needed
  const runWorkflow = async () => {
    // ... (existing runWorkflow logic - kept for reference, but shouldn't be called by new UI) ...
    console.warn("runWorkflow (single-step) is deprecated. Use runMultiStepWorkflow.");
    // Find the appropriate old endpoint based on selectedWorkflow.type
    let endpoint = '';
    let payloadData = { /* ... construct old payload ... */ };
     switch (selectedWorkflow.type) {
         case 'stake': endpoint = '/api/v1/start-stake-cycle'; break;
         // ... other cases ...
         default: return { success: false, message: "Deprecated workflow type" };
     }
     // Make fetch call to old endpoint...
    return { success: false, message: "Use Multi-Step Runner" }; // Return failure for now
  };

  // --- Initialization & Polling ---
  useEffect(() => {
    // Initial fetch of tasks
    fetchTasks();
    // Initial fetch of balances only if wallets exist
    if (wallets.length > 0) {
        fetchWalletBalances();
    }

    // Set up polling intervals
    const tasksInterval = setInterval(fetchTasks, 10000); // Refresh tasks every 10 seconds
    const walletsInterval = setInterval(() => {
         if (wallets.length > 0) { // Only fetch balances if wallets exist
             fetchWalletBalances();
         }
     }, 30000); // Refresh wallets every 30 seconds

    // Clean up intervals on unmount
    return () => {
      clearInterval(tasksInterval);
      clearInterval(walletsInterval);
    };
  }, [wallets.length]); // Re-run effect if wallet count changes (to start/stop polling balances)


  // --- Context Value ---
  // Make sure all required functions and state are included
  const value = {
    workflows,
    selectedWorkflowId,
    selectedWorkflow,
    selectWorkflow,

    wallets,
    selectedWallets,
    toggleWalletSelection,
    importWallet,
    fetchWalletBalances,
    deleteWallet, // Added deleteWallet function
    isLoadingWallets,
    walletError,
    isImportingWallet,
    newWalletImport,
    handleWalletImportChange,

    tasks,
    isLoadingTasks,
    taskError,
    fetchTasks,

    // New Step Management Functions
    addStepToWorkflow,
    deleteStepFromWorkflow,
    updateStepConfig,
    // getDefaultConfigForStepType, // Not needed directly by consumers

    // New Multi-Step Runner
    runMultiStepWorkflow,

    // Old runner (optional/deprecated)
    runWorkflow,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

// Custom hook to use the context
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

export default AppContext; // Ensure default export is correct if used elsewhere