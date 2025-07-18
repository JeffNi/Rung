import React, { useState } from 'react';
import BackgroundStars from './BackgroundStars';

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
    title: '',
    company: '',
    location: '',
    summary: '',
    responsibilities: '',
    requiredSkills: '',
    niceToHaveSkills: '',
    companyCulture: ''
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

  const handleJobDescriptionChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
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
          job_description: {
            title: jobDescription.title,
            company: jobDescription.company,
            location: jobDescription.location,
            summary: jobDescription.summary,
            responsibilities: jobDescription.responsibilities,
            required_skills: jobDescription.requiredSkills.split(',').map(s => s.trim()).filter(s => s),
            nice_to_have_skills: jobDescription.niceToHaveSkills.split(',').map(s => s.trim()).filter(s => s),
            company_culture: jobDescription.companyCulture
          },
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

      <div className="cover-letter-layout">
        <div className="form-column">
          <div className="form-actions" style={{ marginBottom: '2rem' }}>
            <button 
              onClick={() => setCurrentPage('edit-profile')}
              className="btn-secondary"
            >
              Edit Profile
            </button>
          </div>

          <div className="form-section">
            <h3>Job Description</h3>
            <div className="form-group">
              <label htmlFor="jobTitle">Job Title</label>
              <input
                type="text"
                id="jobTitle"
                name="title"
                value={jobDescription.title}
                onChange={handleJobDescriptionChange}
                required
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="company">Company</label>
                <input
                  type="text"
                  id="company"
                  name="company"
                  value={jobDescription.company}
                  onChange={handleJobDescriptionChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="location">Location</label>
                <input
                  type="text"
                  id="location"
                  name="location"
                  value={jobDescription.location}
                  onChange={handleJobDescriptionChange}
                />
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="jobSummary">Job Summary</label>
              <textarea
                id="jobSummary"
                name="summary"
                value={jobDescription.summary}
                onChange={handleJobDescriptionChange}
                rows={3}
                placeholder="Brief description of the role..."
              />
            </div>
            <div className="form-group">
              <label htmlFor="responsibilities">Responsibilities</label>
              <textarea
                id="responsibilities"
                name="responsibilities"
                value={jobDescription.responsibilities}
                onChange={handleJobDescriptionChange}
                rows={4}
                placeholder="Key responsibilities and duties..."
              />
            </div>
            <div className="form-group">
              <label htmlFor="requiredSkills">Required Skills</label>
              <textarea
                id="requiredSkills"
                name="requiredSkills"
                value={jobDescription.requiredSkills}
                onChange={handleJobDescriptionChange}
                rows={3}
                placeholder="Required skills (comma-separated)..."
              />
            </div>
          </div>

          <div className="form-actions">
            <button 
              onClick={generateCoverLetter} 
              className="btn-primary"
              disabled={isLoading}
            >
              {isLoading ? 'Generating...' : 'Generate Cover Letter'}
            </button>
          </div>
        </div>

        <div className="result-column">
          <h3>Generated Cover Letter</h3>
          {coverLetter ? (
            <div className="cover-letter-result">
              <pre>{coverLetter}</pre>
              <button 
                onClick={() => navigator.clipboard.writeText(coverLetter)}
                className="btn-secondary"
              >
                Copy to Clipboard
              </button>
            </div>
          ) : (
            <div className="placeholder">
              <p>Fill out the form and click "Generate Cover Letter" to create your personalized cover letter.</p>
            </div>
          )}
        </div>
      </div>
    </BackgroundStars>
  );
};

export default CoverLetterPage; 