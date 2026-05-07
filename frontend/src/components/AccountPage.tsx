import React, { useState, useEffect } from 'react';
import { auth } from '../firebase';
import { signOut, onAuthStateChanged } from 'firebase/auth';
import type { User } from 'firebase/auth';
import { doc, getDoc } from 'firebase/firestore';
import { db } from '../firebase';
import '../styles/components/AccountPage.css';
import BackgroundStars from './BackgroundStars';

// API Key management helpers
const getStoredApiKey = () => localStorage.getItem('apiKey') || '';
const setStoredApiKey = (key: string) => localStorage.setItem('apiKey', key);
const clearStoredApiKey = () => localStorage.removeItem('apiKey');

const AccountPage: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [apiKey, setApiKey] = useState<string>('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [addingApiKey, setAddingApiKey] = useState(false);
  const [newApiKey, setNewApiKey] = useState('');
  // Modal for adding API key
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [showApiKeyModalValue, setShowApiKeyModalValue] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user);
      setIsLoading(false);
    });

    return () => unsubscribe();
  }, []);

  useEffect(() => {
    setApiKey(getStoredApiKey());
  }, []);

  const handleLogout = async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const handleApiKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setApiKey(e.target.value);
    setStoredApiKey(e.target.value);
  };

  const handleClearApiKey = () => {
    setApiKey('');
    clearStoredApiKey();
  };

  const validateApiKey = (key: string): { valid: boolean; provider: string; message: string } => {
    if (!key || key.trim().length === 0) {
      return { valid: false, provider: 'none', message: 'API key is empty' };
    }
    
    // Check for Gemini key format
    if (key.startsWith('AIza') && key.length >= 35) {
      return { valid: true, provider: 'gemini', message: 'Valid Gemini API key format' };
    }
    
    // Check for Groq key format
    if (key.startsWith('gsk_') && key.length >= 40) {
      return { valid: true, provider: 'groq', message: 'Valid Groq API key format' };
    }
    
    // Invalid format
    let message = `Invalid API key format (${key.length} chars). `;
    if (key.length === 56) {
      message += 'This looks like a Firebase UID, not an API key. ';
    }
    message += 'Expected: Gemini (starts with "AIza") or Groq (starts with "gsk_")';
    
    return { valid: false, provider: 'unknown', message };
  };

  const handleAddApiKey = () => {
    if (newApiKey.trim() === '') {
      clearStoredApiKey();
      setApiKey('');
    } else {
      const validation = validateApiKey(newApiKey);
      if (!validation.valid) {
        alert(`⚠️ Warning: ${validation.message}\n\nPlease make sure you're using the correct API key from:\n- Gemini: https://aistudio.google.com/apikey\n- Groq: https://console.groq.com`);
      }
      setStoredApiKey(newApiKey);
      setApiKey(newApiKey);
    }
    setNewApiKey('');
    setAddingApiKey(false);
  };

  if (isLoading) {
    return (
      <BackgroundStars>
        <div className="account-page">
          <div className="account-card">
            <div className="loading">Loading...</div>
          </div>
        </div>
      </BackgroundStars>
    );
  }

  if (!user) {
    return (
      <BackgroundStars>
        <div className="account-page">
          <div className="account-card">
            <div className="account-header">
              <h1>Not Signed In</h1>
              <p>Please sign in to view your account</p>
            </div>
          </div>
        </div>
      </BackgroundStars>
    );
  }

  return (
    <BackgroundStars>
      <div className="account-page">
        <div className="account-card">
          <div className="account-header">
            <h1>My Account</h1>
            <p>Welcome back, {user.email}</p>
          </div>

          <div className="account-info">
            <div className="info-section">
              <h3>Account Information</h3>
              <div className="info-item">
                <label>Email:</label>
                <span>{user.email}</span>
              </div>
              <div className="info-item">
                <label>Account Created:</label>
                <span>{user.metadata.creationTime ? new Date(user.metadata.creationTime).toLocaleDateString() : 'Unknown'}</span>
              </div>
              <div className="info-item">
                <label>Last Sign In:</label>
                <span>{user.metadata.lastSignInTime ? new Date(user.metadata.lastSignInTime).toLocaleDateString() : 'Unknown'}</span>
              </div>
              <div className="info-item">
                <label>Email Verified:</label>
                <span className={user.emailVerified ? 'verified' : 'not-verified'}>
                  {user.emailVerified ? '✓ Verified' : '✗ Not Verified'}
                </span>
              </div>
              <div className="info-item">
                <label>API Key:</label>
                {apiKey ? (
                  <div>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.2rem', letterSpacing: '0.2em' }}>
                      <span style={{ background: '#f3f4f6', borderRadius: '0.25rem', padding: '0.25rem 1.5rem', border: '1px solid #d1d5db', fontSize: '1.2rem', color: '#374151' }}>
                        {'•'.repeat(8)}
                      </span>
                      <button
                        type="button"
                        className="btn-primary"
                        style={{ fontSize: '0.9rem', padding: '0.25rem 0.75rem', marginLeft: '1rem' }}
                        onClick={() => { setNewApiKey(apiKey); setShowApiKeyModal(true); }}
                      >
                        Change
                      </button>
                    </span>
                    {(() => {
                      const validation = validateApiKey(apiKey);
                      if (!validation.valid) {
                        return (
                          <div style={{ 
                            marginTop: '0.5rem', 
                            padding: '0.75rem', 
                            backgroundColor: '#fef2f2', 
                            border: '1px solid #ef4444', 
                            borderRadius: '0.375rem',
                            fontSize: '0.9rem',
                            color: '#991b1b'
                          }}>
                            <strong>⚠️ Invalid API Key Format</strong><br/>
                            {validation.message}<br/>
                            <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>Get Gemini Key</a> | <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>Get Groq Key</a>
                          </div>
                        );
                      } else {
                        return (
                          <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#059669' }}>
                            ✓ {validation.message} ({validation.provider.toUpperCase()})
                          </div>
                        );
                      }
                    })()}
                  </div>
                ) : (
                  <span className="not-verified" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '1.2rem', color: '#ef4444' }}>✗</span> No API key
                    <button
                      type="button"
                      className="btn-primary"
                      style={{ fontSize: '0.9rem', padding: '0.25rem 0.75rem', marginLeft: '1rem' }}
                      onClick={() => { setNewApiKey(apiKey); setShowApiKeyModal(true); }}
                    >
                      Add
                    </button>
                  </span>
                )}
              </div>
            </div>

            <div className="account-actions">
              <button className="btn-primary" onClick={handleLogout}>
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </div>
      {/* API Key Modal */}
      {showApiKeyModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: 400, margin: '0 auto', padding: '2rem', borderRadius: '0.75rem', background: 'white', boxShadow: '0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px 0 rgba(0,0,0,0.06)' }}>
            <div className="modal-header" style={{ marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Add API Key</h2>
            </div>
            <div className="modal-body" style={{ marginBottom: '1.5rem' }}>
              <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#f0f9ff', border: '1px solid #3b82f6', borderRadius: '0.375rem', fontSize: '0.9rem' }}>
                <strong>Get a free API key:</strong><br/>
                <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>Gemini (starts with "AIza")</a> - 20 requests/day<br/>
                <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>Groq (starts with "gsk_")</a> - 14,400 requests/day ⚡
              </div>
              <div style={{ display: 'flex', alignItems: 'center', position: 'relative' }}>
                <input
                  type={showApiKeyModalValue ? 'text' : 'password'}
                  value={newApiKey}
                  onChange={e => setNewApiKey(e.target.value)}
                  placeholder="Enter API key (AIza... or gsk_...)"
                  style={{ width: '100%', fontSize: '1rem', padding: '0.5rem 2.5rem 0.5rem 0.5rem', borderRadius: '0.25rem', border: '1px solid #d1d5db', background: '#f3f4f6' }}
                />
                <button
                  type="button"
                  onClick={() => setShowApiKeyModalValue(v => !v)}
                  style={{
                    position: 'absolute',
                    right: '0.5rem',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: 0,
                    height: '1.5rem',
                    width: '2rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                  tabIndex={-1}
                  aria-label={showApiKeyModalValue ? 'Hide API key' : 'Show API key'}
                >
                  {showApiKeyModalValue ? (
                    <span role="img" aria-label="Hide">🙈</span>
                  ) : (
                    <span role="img" aria-label="Show">👁️</span>
                  )}
                </button>
              </div>
              <div style={{ color: '#ef4444', fontSize: '0.95rem', marginTop: '0.75rem', lineHeight: 1.4 }}>
                <strong>Warning:</strong> Your API key will be stored in your browser. Do not use this on shared or public computers.
              </div>
            </div>
            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn-secondary"
                style={{ background: '#ef4444', color: 'white', border: 'none' }}
                onClick={() => { setShowApiKeyModal(false); setNewApiKey(''); }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => { handleAddApiKey(); setShowApiKeyModal(false); }}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </BackgroundStars>
  );
};

export default AccountPage; 