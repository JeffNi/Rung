import React, { useState, useEffect } from 'react';
import { auth } from '../firebase';
import { signOut, onAuthStateChanged } from 'firebase/auth';
import type { User } from 'firebase/auth';
import { doc, getDoc } from 'firebase/firestore';
import { db } from '../firebase';
import '../styles/components/AccountPage.css';
import BackgroundStars from './BackgroundStars';

const AccountPage: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user);
      setIsLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const handleLogout = async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.error('Error signing out:', error);
    }
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
            </div>

            <div className="account-actions">
              <button className="btn-primary" onClick={handleLogout}>
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </div>
    </BackgroundStars>
  );
};

export default AccountPage; 