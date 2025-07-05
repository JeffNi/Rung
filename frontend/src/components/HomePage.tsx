import React from 'react';
import { useParallax } from '../hooks/useParallax';

const HomePage: React.FC = () => {
  const scrollY = useParallax();
  
  return (
    <div className="page-container home-page">
      {/* Stars */}
      <div 
        className="stars"
        style={{ transform: `translateY(${scrollY * 0.2}px)` }}
      >
        {[...Array(50)].map((_, i) => (
          <div key={i} className="star" style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 60}%`,
            animationDelay: `${Math.random() * 3}s`,
            animationDuration: `${2 + Math.random() * 3}s`
          }}></div>
        ))}
      </div>
      
      {/* Clouds */}
      <div className="clouds">
        <div className="cloud cloud1"></div>
        <div className="cloud cloud2"></div>
        <div className="cloud cloud3"></div>
        <div className="cloud cloud4"></div>
        <div className="cloud cloud5"></div>
      </div>
      
      <div className="hero-section">
        <h1>Welcome to Skyward</h1>
        <p className="hero-subtitle">
          Your AI-powered career companion for creating standout resumes and cover letters
        </p>
        <div className="hero-features">
          <div className="feature-card">
            <h3>📄 Smart Resume Builder</h3>
            <p>Create professional resumes tailored to your industry and experience level</p>
          </div>
          <div className="feature-card">
            <h3>✉️ Cover Letters</h3>
            <p>Generate personalized cover letters that match your voice and the job requirements</p>
          </div>
          <div className="feature-card">
            <h3>🎯 Job-Specific Optimization</h3>
            <p>Optimize your applications for specific job descriptions and company cultures</p>
          </div>
        </div>
      </div>
      
      <div className="cta-section">
        <h2>Ready to boost your career?</h2>
        <p>Choose from the navigation above to get started with your resume or cover letter</p>
      </div>
    </div>
  );
};

export default HomePage; 