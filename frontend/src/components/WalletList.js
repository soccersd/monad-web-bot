import React, { useState } from 'react';
import { useAppContext } from '../context/AppContext';
import './WalletList.css';

function WalletList() {
  const { 
    wallets, 
    toggleWalletSelection, 
    isLoadingWallets, 
    walletError, 
    fetchWalletBalances, 
    importWallet, 
    isImportingWallet, 
    newWalletImport, 
    handleWalletImportChange,
    deleteWallet
  } = useAppContext();

  const [showImportForm, setShowImportForm] = useState(false);

  const handleImportSubmit = async (e) => {
    e.preventDefault();
    if (!newWalletImport.privateKey) {
      alert('Please enter a private key.');
      return;
    }
    const result = await importWallet(newWalletImport.privateKey, newWalletImport.nickname);
    if (result.success) {
      setShowImportForm(false);
    }
  };

  return (
    <div className="wallets-container">
      <div className="wallets-header">
        <h2>Wallets</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={() => setShowImportForm(!showImportForm)} 
            style={{
              backgroundColor: showImportForm ? '#f0ebfa' : 'transparent',
              border: '1px solid #ddd',
              color: '#333',
              padding: '4px 8px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: '500',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <span style={{ fontSize: '1rem' }}>+</span> {showImportForm ? 'Hide Form' : 'Add Wallet'}
          </button>
          <button 
            onClick={fetchWalletBalances} 
            disabled={isLoadingWallets}
            style={{
              backgroundColor: 'transparent',
              border: '1px solid #ddd',
              color: '#333',
              padding: '4px 8px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: '500',
              opacity: isLoadingWallets ? '0.6' : '1'
            }}
          >
            {isLoadingWallets ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {walletError && (
        <div style={{
          backgroundColor: '#f8d7da', 
          color: '#721c24',
          padding: '8px 12px',
          margin: '8px 0',
          borderRadius: '4px',
          fontSize: '0.85rem',
          border: '1px solid #f5c6cb'
        }}>
          {walletError}
        </div>
      )}

      {/* Import Wallet Form */}
      {showImportForm && (
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '16px',
          marginBottom: '16px',
          border: '1px solid #e9ecef',
          boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
        }}>
          <form onSubmit={handleImportSubmit}>
            <div style={{ marginBottom: '16px' }}>
              <label 
                htmlFor="privateKey" 
                style={{ 
                  display: 'block', 
                  marginBottom: '6px', 
                  fontSize: '0.85rem',
                  fontWeight: '500',
                  color: '#495057'
                }}
              >
                Private Key:
              </label>
              <input
                type="password"
                id="privateKey"
                value={newWalletImport.privateKey}
                onChange={(e) => handleWalletImportChange('privateKey', e.target.value)}
                placeholder="0x..."
                required
                disabled={isImportingWallet}
                style={{ 
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '0.9rem'
                }}
              />
              <small style={{ display: 'block', marginTop: '4px', color: '#6c757d', fontSize: '0.75rem' }}>
                Your private key is never stored on our servers
              </small>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label 
                htmlFor="nickname"
                style={{ 
                  display: 'block', 
                  marginBottom: '6px', 
                  fontSize: '0.85rem',
                  fontWeight: '500',
                  color: '#495057'
                }}
              >
                Nickname (Optional):
              </label>
              <input
                type="text"
                id="nickname"
                value={newWalletImport.nickname}
                onChange={(e) => handleWalletImportChange('nickname', e.target.value)}
                placeholder="My Wallet 1"
                disabled={isImportingWallet}
                style={{ 
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '0.9rem'
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button 
                type="button" 
                onClick={() => setShowImportForm(false)}
                style={{
                  backgroundColor: 'transparent',
                  border: '1px solid #ffd6df',
                  color: '#6c757d',
                  padding: '8px 16px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                disabled={isImportingWallet || !newWalletImport.privateKey} 
                style={{
                  backgroundColor: '#ffb6c1',
                  color: 'white',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: '500',
                  opacity: (isImportingWallet || !newWalletImport.privateKey) ? '0.6' : '1'
                }}
              >
                {isImportingWallet ? 'Importing...' : 'Import Wallet'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Wallet List */}
      <div style={{ marginTop: '12px' }}>
        {wallets.length === 0 ? (
          <div style={{ 
            padding: '16px', 
            textAlign: 'center', 
            color: '#6c757d',
            fontSize: '0.9rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px dashed #ced4da'
          }}>
            No wallets imported yet. Click "Add Wallet" to get started.
          </div>
        ) : (
          <>
            <div style={{ 
              display: 'grid',
              gridTemplateColumns: '40px 1fr auto',
              padding: '8px 12px',
              borderBottom: '1px solid #e9ecef',
              fontSize: '0.8rem',
              color: '#6c757d',
              fontWeight: '600'
            }}>
              <div></div>
              <div>Wallet</div>
              <div>Balance</div>
            </div>
            
            {wallets.map(wallet => (
              <div 
                key={wallet.id} 
                style={{
                  display: 'grid',
                  gridTemplateColumns: '40px 1fr auto',
                  alignItems: 'center',
                  padding: '10px 12px',
                  backgroundColor: wallet.selected ? '#f0ebfa' : 'white',
                  borderRadius: '6px',
                  marginTop: '4px',
                  border: '1px solid #e9ecef',
                  transition: 'background-color 0.2s'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <input 
                    type="checkbox" 
                    checked={wallet.selected} 
                    onChange={() => toggleWalletSelection(wallet.id)}
                    style={{
                      width: '18px',
                      height: '18px',
                      cursor: 'pointer',
                      accentColor: '#8359d4'
                    }}
                  />
                </div>
                <div>
                  <div style={{ 
                    fontWeight: '500', 
                    fontSize: '0.9rem',
                    color: '#343a40'
                  }}>
                    {wallet.nickname || `Wallet ${wallet.id}`}
                  </div>
                  <div style={{
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                    color: '#6c757d',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {wallet.address}
                  </div>
                </div>
                <div style={{
                  fontWeight: '500',
                  fontSize: '0.9rem',
                  color: (typeof wallet.balance === 'string' && !isNaN(parseFloat(wallet.balance)) && parseFloat(wallet.balance) > 0) ? '#343a40' : '#6c757d'
                }}>
                  {typeof wallet.balance === 'string' && !isNaN(parseFloat(wallet.balance))
                    ? parseFloat(wallet.balance).toFixed(4)
                    : (wallet.balance === 'Error' ? 'Error' : '?.???')
                  }
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

export default WalletList; 