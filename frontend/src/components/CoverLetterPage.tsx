import React, { useState } from 'react';
import BackgroundStars from './BackgroundStars';
import '../styles/components/CoverLetterPage.css';

const CoverLetterPage: React.FC<{ setCurrentPage: (page: string) => void }> = ({ setCurrentPage }) => {
  const [userProfile, setUserProfile] = useState({
    name: '',
    title: '',
    email: '',
    phone: '',
    skills: '',
    courses: '',
    experience: '',
    projects: '',
    goals: '',
    values: '',
    interests: ''
  });

  const [jobDescription, setJobDescription] = useState({
    description: ''
  });

  const [coverLetter, setCoverLetter] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleUserProfileChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setUserProfile(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleJobDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setJobDescription(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const generateCoverLetter = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with your actual API endpoint
      const response = await fetch('http://localhost:8000/generate-cover-letter', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_profile: {
            name: userProfile.name,
            title: userProfile.title,
            contact: {
              email: userProfile.email,
              phone: userProfile.phone
            },
            skills: userProfile.skills.split(',').map(s => s.trim()).filter(s => s),
            courses: userProfile.courses.split(',').map(s => s.trim()).filter(s => s),
            experience: [], // TODO: Parse experience properly
            projects: [], // TODO: Parse projects properly
            goals: userProfile.goals.split(',').map(s => s.trim()).filter(s => s),
            values: userProfile.values.split(',').map(s => s.trim()).filter(s => s),
            interests: userProfile.interests.split(',').map(s => s.trim()).filter(s => s)
          },
          job_description: jobDescription.description,
          paragraph_count: 4
        })
      });

      if (response.ok) {
        const data = await response.json();
        setCoverLetter(data.cover_letter);
      } else {
        console.error('Failed to generate cover letter');
        setCoverLetter('Error: Failed to generate cover letter. Please try again.');
      }
    } catch (error) {
      console.error('Error:', error);
      setCoverLetter('Error: Unable to connect to the server. Please check if the API is running.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <BackgroundStars>
      <div className="page-header">
        <h1>Cover Letter Generator</h1>
        <p>Create personalized cover letters using AI</p>
      </div>

      <div className="cover-letter-layout" style={{ display: 'block', maxWidth: '800px', margin: '0 auto' }}>
        <div className="form-section">
          <h3>Job Description</h3>
          <div className="form-group">
            <label htmlFor="jobDescription">Paste the full job description here</label>
            <textarea
              id="jobDescription"
              name="description"
              value={jobDescription.description}
              onChange={handleJobDescriptionChange}
              rows={8}
              placeholder="Paste the complete job description, including title, company, requirements, responsibilities, etc..."
              style={{ width: '100%', resize: 'vertical' }}
            />
          </div>
        </div>

        <div className="form-actions" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginTop: '2rem' }}>
          <button 
            onClick={() => setCurrentPage('edit-profile')}
            className="btn-secondary"
          >
            Edit Profile
          </button>
          <button 
            onClick={generateCoverLetter} 
            className="btn-primary"
            disabled={isLoading}
          >
            {isLoading ? 'Generating...' : 'Generate Cover Letter'}
          </button>
        </div>
      </div>
    </BackgroundStars>
  );
};

export default CoverLetterPage; 