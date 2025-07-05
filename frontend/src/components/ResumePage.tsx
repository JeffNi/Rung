import React, { useState } from 'react';
import { useParallax } from '../hooks/useParallax';

const ResumePage: React.FC = () => {
  const scrollY = useParallax();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    title: '',
    summary: '',
    skills: '',
    experience: '',
    education: ''
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Integrate with resume generation API
    console.log('Resume data:', formData);
  };

  return (
    <div className="page-container resume-page">
      {/* Stars */}
      <div 
        className="stars"
        style={{ transform: `translateY(${scrollY * 0.2}px)` }}
      >
        {[...Array(30)].map((_, i) => (
          <div key={i} className="star" style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 60}%`,
            animationDelay: `${Math.random() * 3}s`,
            animationDuration: `${2 + Math.random() * 3}s`
          }}></div>
        ))}
      </div>

      {/* Shooting Stars */}
      <div className="shooting-stars">
        {[...Array(10)].map((_, i) => (
          <div 
            key={`shooting-${i}`} 
            className="shooting-star" 
            style={{
              top: `${Math.random() * 60}%`,
              animationDelay: `${Math.random() * 30 + 10}s`,
              animationDuration: `${2 + Math.random() * 2}s`
            }}
          ></div>
        ))}
      </div>
      
      <div className="page-header">
        <h1>Resume Builder</h1>
        <p>Create a professional resume tailored to your experience and goals</p>
      </div>

      <form className="resume-form" onSubmit={handleSubmit}>
        <div className="form-section">
          <h3>Personal Information</h3>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="name">Full Name</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="title">Professional Title</label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleInputChange}
                placeholder="e.g., Software Engineer, Marketing Manager"
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="phone">Phone</label>
              <input
                type="tel"
                id="phone"
                name="phone"
                value={formData.phone}
                onChange={handleInputChange}
              />
            </div>
          </div>
        </div>

        <div className="form-section">
          <h3>Professional Summary</h3>
          <div className="form-group">
            <label htmlFor="summary">Summary</label>
            <textarea
              id="summary"
              name="summary"
              value={formData.summary}
              onChange={handleInputChange}
              rows={4}
              placeholder="Brief overview of your professional background and key strengths..."
            />
          </div>
        </div>

        <div className="form-section">
          <h3>Skills</h3>
          <div className="form-group">
            <label htmlFor="skills">Skills (comma-separated)</label>
            <textarea
              id="skills"
              name="skills"
              value={formData.skills}
              onChange={handleInputChange}
              rows={3}
              placeholder="e.g., JavaScript, React, Project Management, Leadership"
            />
          </div>
        </div>

        <div className="form-section">
          <h3>Work Experience</h3>
          <div className="form-group">
            <label htmlFor="experience">Experience Details</label>
            <textarea
              id="experience"
              name="experience"
              value={formData.experience}
              onChange={handleInputChange}
              rows={6}
              placeholder="Describe your work experience, achievements, and responsibilities..."
            />
          </div>
        </div>

        <div className="form-section">
          <h3>Education</h3>
          <div className="form-group">
            <label htmlFor="education">Education Details</label>
            <textarea
              id="education"
              name="education"
              value={formData.education}
              onChange={handleInputChange}
              rows={3}
              placeholder="Your educational background, degrees, certifications..."
            />
          </div>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn-primary">
            Generate Resume
          </button>
        </div>
      </form>
    </div>
  );
};

export default ResumePage; 