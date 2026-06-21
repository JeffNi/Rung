import React, { useState, useEffect } from 'react';
import './App.css';
import HomePage from './components/HomePage';
import ResumePage from './components/ResumePage';
import ApplyPage from './components/ApplyPage';
import ProfilePage from './components/EditProfilePage';
import JobSearchPage from './components/JobSearchPage';
import StoredJobsPage from './components/StoredJobsPage';
import LoginPage from './components/LoginPage';
import AccountPage from './components/AccountPage';
import { useParallax } from './hooks/useParallax';
import { auth } from './firebase';
import { onAuthStateChanged } from 'firebase/auth';
import type { User } from 'firebase/auth';

function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const scrollY = useParallax();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user);
      setIsLoading(false);
      
      // Redirect to account page if user is logged in and on login page
      if (user && currentPage === 'login') {
        setCurrentPage('account');
      }
    });

    return () => unsubscribe();
  }, [currentPage]);

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage />;
      case 'resume':
        return <ResumePage />;
      case 'jobsearch':
        return <JobSearchPage setCurrentPage={setCurrentPage} />;
      case 'savedjobs':
        return <StoredJobsPage setCurrentPage={setCurrentPage} />;
      case 'apply':
        return <ApplyPage setCurrentPage={setCurrentPage} />;
      case 'profile':
        return <ProfilePage setCurrentPage={setCurrentPage} />;
      case 'login':
        return <LoginPage />;
      case 'account':
        return <AccountPage />;
      default:
        return <HomePage />;
    }
  };

  const handleNavClick = (page: string) => {
    // If user is not logged in and tries to access account page, redirect to login
    if (page === 'account' && !user) {
      setCurrentPage('login');
    } else {
      setCurrentPage(page);
    }
  };

  if (isLoading) {
    return (
      <div className="App">
        <div className="loading-screen">
          <div className="loading">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      {/* Parallax Background */}
      <div 
        className="parallax-bg"
        style={{ 
          background: `linear-gradient(to bottom, #0a0a0a 0%, #1a1a2e 10%, #16213e 20%, #0f3460 35%, #1e40af 50%, #3b82f6 65%, #60a5fa 80%, #93c5fd 95%, #dbeafe 100%)`,
          transform: `translateY(${scrollY * 0.3}px)`,
          backgroundSize: '100% 200vh',
          backgroundRepeat: 'no-repeat'
        }}
      ></div>
      
      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="nav-container">
          <div className="nav-logo">
            <img src="/images/Skyward.png" alt="Skyward Logo" className="nav-logo-img" />
            <h2>Skyward</h2>
          </div>
          <div className="nav-links">
            <button 
              className={`nav-link ${currentPage === 'home' ? 'active' : ''}`}
              onClick={() => handleNavClick('home')}
            >
              Home
            </button>
            <button 
              className={`nav-link ${currentPage === 'profile' ? 'active' : ''}`}
              onClick={() => handleNavClick('profile')}
            >
              Profile
            </button>
            <button 
              className={`nav-link ${currentPage === 'jobsearch' ? 'active' : ''}`}
              onClick={() => handleNavClick('jobsearch')}
            >
              Jobs
            </button>
            <button 
              className={`nav-link ${currentPage === 'savedjobs' ? 'active' : ''}`}
              onClick={() => handleNavClick('savedjobs')}
            >
              Saved
            </button>
            <button 
              className={`nav-link ${currentPage === 'apply' ? 'active' : ''}`}
              onClick={() => handleNavClick('apply')}
            >
              Apply
            </button>
            <button 
              className={`nav-link ${currentPage === 'login' || currentPage === 'account' ? 'active' : ''}`}
              onClick={() => handleNavClick(user ? 'account' : 'login')}
            >
              {user ? 'Account' : 'Login'}
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {renderPage()}
      </main>
    </div>
  );
}

export default App;
