import React from 'react';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import { AppProvider } from './context/AppContext';
import './App.css';

function App() {
    return (
        <AppProvider>
            <div className="App">
                <div className="app-container">
                    <Sidebar />
                    <MainContent />
                </div>
            </div>
        </AppProvider>
    );
}

export default App;
