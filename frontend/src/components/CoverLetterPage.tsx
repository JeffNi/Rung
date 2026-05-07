import React, { useState, useEffect } from 'react';
import { auth, db } from '../firebase';
import { doc, getDoc } from 'firebase/firestore';
import type { User } from 'firebase/auth';
import type { UserProfile } from './ProfileModal';
import BackgroundStars from './BackgroundStars';
import '../styles/components/CoverLetterPage.css';
import jsPDF from 'jspdf';

const CoverLetterPage: React.FC<{ setCurrentPage: (page: string) => void }> = ({ setCurrentPage }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
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
    interests: '',
    writingSample: ''
  });

  const [jobDescription, setJobDescription] = useState({
    description: ''
  });
  
  const [additionalInstructions, setAdditionalInstructions] = useState('');
  const [instructionPresets, setInstructionPresets] = useState<{[key: string]: string}>({});
  const [selectedPreset, setSelectedPreset] = useState('');
  const [showSavePreset, setShowSavePreset] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');
  
  const [provider, setProvider] = useState('gemini'); // 'gemini' or 'groq'

  const [coverLetter, setCoverLetter] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user);
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    // Check if API key is set
    const apiKey = localStorage.getItem('apiKey');
    setHasApiKey(!!apiKey && apiKey.trim().length > 0);
  }, []);

  useEffect(() => {
    if (user) {
      loadProfile(user.uid);
    }
  }, [user]);

  // Load instruction presets from localStorage
  useEffect(() => {
    const savedPresets = localStorage.getItem('instructionPresets');
    if (savedPresets) {
      try {
        setInstructionPresets(JSON.parse(savedPresets));
      } catch (e) {
        console.error('Failed to load instruction presets:', e);
      }
    }
  }, []);

  useEffect(() => {
    if (showModal) {
      document.body.classList.add('modal-open');
    } else {
      document.body.classList.remove('modal-open');
    }
    return () => {
      document.body.classList.remove('modal-open');
    };
  }, [showModal]);

  const loadProfile = async (userId: string) => {
    setIsLoading(true);
    try {
      const profileDoc = await getDoc(doc(db, 'userProfiles', userId));
      if (profileDoc.exists()) {
        const data = profileDoc.data() as UserProfile;
        // Convert arrays and objects back to strings for form
        setUserProfile({
          name: data.name || '',
          title: data.title || '',
          email: data.contact?.email || '',
          phone: data.contact?.phone || '',
          skills: data.skills?.join(', ') || '',
          courses: data.courses?.join(', ') || '',
          experience: formatExperience(data.experience),
          projects: formatProjects(data.projects),
          goals: data.goals?.join(', ') || '',
          values: data.values?.join(', ') || '',
          interests: data.interests?.join(', ') || '',
          writingSample: data.writingSample || ''
        });
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatExperience = (experience: Record<string, string[]>): string => {
    if (!experience) return '';
    return Object.entries(experience)
      .map(([company, tasks]) => `${company}:\n${tasks.map(t => `- ${t}`).join('\n')}`)
      .join('\n\n');
  };

  const formatProjects = (projects: Record<string, string[]>): string => {
    if (!projects) return '';
    return Object.entries(projects)
      .map(([project, details]) => `${project}:\n${details.map(d => `- ${d}`).join('\n')}`)
      .join('\n\n');
  };

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

  const parseExperience = (expString: string) => {
    // Example format: "Job Title at Company: - achievement1 - achievement2"
    if (!expString.trim()) return [];
    return expString.split('\n\n').map(section => {
      const [header, ...rest] = section.split('\n');
      const [title, ...companyArr] = header.split(' at ');
      const company = companyArr.join(' at ');
      const achievements = rest.filter(line => line.trim().startsWith('-')).map(line => line.replace(/^\s*-\s*/, ''));
      return { title: title?.trim() || '', company: company?.trim() || '', achievements };
    });
  };
  const parseProjects = (projString: string) => {
    if (!projString.trim()) return [];
    return projString.split('\n\n').map(section => {
      const [name, ...rest] = section.split('\n');
      const description = rest.filter(line => line.trim().startsWith('-')).map(line => line.replace(/^\s*-\s*/, ''));
      return { name: name?.replace(':', '').trim() || '', description };
    });
  };

  const generateCoverLetter = async () => {
    setIsGenerating(true);
    setError('');
    setCoverLetter('');
    try {
      const { writingSample, ...userProfileRest } = userProfile;
      const baseApi = (import.meta.env.VITE_API_URL || '').replace(/\/+$/,'');
      const endpoint = '/generate-cover-letter';
      const url = baseApi.endsWith(endpoint) ? baseApi : `${baseApi}${endpoint}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_profile: {
            name: userProfileRest.name,
            title: userProfileRest.title,
            contact: {
              email: userProfileRest.email,
              phone: userProfileRest.phone
            },
            skills: userProfileRest.skills.split(',').map(s => s.trim()).filter(s => s),
            courses: userProfileRest.courses.split(',').map(s => s.trim()).filter(s => s),
            experience: parseExperience(userProfileRest.experience),
            projects: parseProjects(userProfileRest.projects),
            goals: userProfileRest.goals.split(',').map(s => s.trim()).filter(s => s),
            values: userProfileRest.values.split(',').map(s => s.trim()).filter(s => s),
            interests: userProfileRest.interests.split(',').map(s => s.trim()).filter(s => s)
          },
          job_description: jobDescription.description,
          writing_sample: writingSample || '',
          paragraph_count: 3,
          provider: provider,
          api_key: localStorage.getItem('apiKey') || '',
          additional_instructions: additionalInstructions
        })
      });

      if (response.ok) {
        const data = await response.json();
        setCoverLetter(data.cover_letter);
        setShowModal(true);
      } else {
        const errorData = await response.json();
        let errorMessage = errorData.detail || 'Failed to generate cover letter. Please try again.';
        
        // Check if it's an API key error
        if (errorMessage.toLowerCase().includes('invalid api key') || errorMessage.toLowerCase().includes('api key')) {
          errorMessage = `Invalid API key. Please add a valid ${provider === 'groq' ? 'Groq' : 'Gemini'} API key in your Account page. Get a free API key at ${provider === 'groq' ? 'https://console.groq.com' : 'https://aistudio.google.com/apikey'}`;
        }
        
        setError(errorMessage);
      }
    } catch (error) {
      setError('Unable to connect to the server. Please check if the API is running.');
    } finally {
      setIsGenerating(false);
    }
  };

  const savePreset = () => {
    if (!newPresetName.trim()) {
      alert('Please enter a preset name');
      return;
    }
    if (!additionalInstructions.trim()) {
      alert('Please enter some instructions to save');
      return;
    }
    const updatedPresets = {
      ...instructionPresets,
      [newPresetName]: additionalInstructions
    };
    setInstructionPresets(updatedPresets);
    localStorage.setItem('instructionPresets', JSON.stringify(updatedPresets));
    setNewPresetName('');
    setShowSavePreset(false);
    alert(`Preset "${newPresetName}" saved!`);
  };

  const loadPreset = (presetName: string) => {
    if (presetName && instructionPresets[presetName]) {
      setAdditionalInstructions(instructionPresets[presetName]);
      setSelectedPreset(presetName);
    }
  };

  const deletePreset = (presetName: string) => {
    if (window.confirm(`Delete preset "${presetName}"?`)) {
      const updatedPresets = { ...instructionPresets };
      delete updatedPresets[presetName];
      setInstructionPresets(updatedPresets);
      localStorage.setItem('instructionPresets', JSON.stringify(updatedPresets));
      if (selectedPreset === presetName) {
        setSelectedPreset('');
      }
    }
  };

  const handleCopyCoverLetter = async () => {
    if (coverLetter) {
      try {
        await navigator.clipboard.writeText(coverLetter);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      } catch (err) {
        setCopied(false);
      }
    }
  };

  const handleDownloadPDF = () => {
    const doc = new jsPDF();
    const lines = doc.splitTextToSize(coverLetter, 180);
    doc.text(lines, 15, 20);
    doc.save('cover_letter.pdf');
  };

  if (isLoading) {
    return (
      <BackgroundStars>
        <div className="page-header">
          <h1>Cover Letter Generator</h1>
          <p>Loading your profile...</p>
        </div>
      </BackgroundStars>
    );
  }

  return (
    <BackgroundStars>
      <div className="cover-letter-generator-container">
        <div className="page-header" style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1>Cover Letter Generator</h1>
          <p style={{ marginTop: '0.5rem' }}>Create personalized cover letters using AI</p>
        </div>
        
        {/* API Key Warning */}
        {!hasApiKey && (
          <div style={{
            backgroundColor: '#fef2f2',
            border: '2px solid #ef4444',
            borderRadius: '0.75rem',
            padding: '1.25rem',
            marginBottom: '2rem',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⚠️</div>
            <h3 style={{ color: '#dc2626', marginBottom: '0.5rem', fontSize: '1.1rem' }}>API Key Required</h3>
            <p style={{ color: '#991b1b', marginBottom: '0.75rem', lineHeight: 1.5 }}>
              You need to add an API key to generate cover letters. Get a free API key from:
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
              <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" 
                 style={{ color: '#2563eb', textDecoration: 'underline', fontWeight: 500 }}>
                Google Gemini (20 requests/day free)
              </a>
              <span style={{ color: '#991b1b' }}>or</span>
              <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer" 
                 style={{ color: '#2563eb', textDecoration: 'underline', fontWeight: 500 }}>
                Groq (14,400 requests/day free) ⚡
              </a>
            </div>
            <button
              onClick={() => setCurrentPage('account')}
              style={{
                backgroundColor: '#dc2626',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                padding: '0.5rem 1.5rem',
                fontSize: '1rem',
                fontWeight: 600,
                cursor: 'pointer',
                marginTop: '0.5rem'
              }}
            >
              Add API Key in Account Page →
            </button>
          </div>
        )}
        
        <div className="form-section wide-form-section" style={{ minHeight: '40vh' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Job Description</h3>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.9rem', color: '#6b7280' }}>AI Provider:</span>
              <select 
                value={provider} 
                onChange={(e) => setProvider(e.target.value)}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '0.375rem',
                  border: '1px solid #d1d5db',
                  backgroundColor: 'white',
                  color: '#1f2937',
                  cursor: 'pointer',
                  fontSize: '0.9rem'
                }}
              >
                <option value="gemini" style={{ color: '#1f2937' }}>Gemini (20/day free)</option>
                <option value="groq" style={{ color: '#1f2937' }}>Groq (14,400/day free) ⚡</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="jobDescription">Paste the full job description here</label>
            <textarea
              id="jobDescription"
              name="description"
              value={jobDescription.description}
              onChange={handleJobDescriptionChange}
              rows={10}
              placeholder="Paste the complete job description, including title, company, requirements, responsibilities, etc..."
              className="job-description-textarea"
            />
          </div>
          <div className="form-group" style={{ marginTop: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <label htmlFor="additionalInstructions">Additional Instructions (Optional)</label>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                {Object.keys(instructionPresets).length > 0 && (
                  <>
                    <select
                      value={selectedPreset}
                      onChange={(e) => {
                        setSelectedPreset(e.target.value);
                        if (e.target.value) loadPreset(e.target.value);
                      }}
                      style={{
                        padding: '0.4rem 0.6rem',
                        fontSize: '0.85rem',
                        borderRadius: '6px',
                        border: '1px solid #d1d5db',
                        backgroundColor: 'white',
                        color: '#1f2937',
                        cursor: 'pointer'
                      }}
                    >
                      <option value="" style={{ color: '#1f2937' }}>Load Preset...</option>
                      {Object.keys(instructionPresets).map(name => (
                        <option key={name} value={name} style={{ color: '#1f2937' }}>{name}</option>
                      ))}
                    </select>
                    {selectedPreset && (
                      <button
                        onClick={() => deletePreset(selectedPreset)}
                        style={{
                          padding: '0.4rem 0.8rem',
                          fontSize: '0.85rem',
                          borderRadius: '6px',
                          border: '1px solid #dc2626',
                          backgroundColor: 'white',
                          color: '#dc2626',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </>
                )}
                <button
                  onClick={() => setShowSavePreset(!showSavePreset)}
                  style={{
                    padding: '0.4rem 0.8rem',
                    fontSize: '0.85rem',
                    borderRadius: '6px',
                    border: '1px solid #3b82f6',
                    backgroundColor: 'white',
                    color: '#3b82f6',
                    cursor: 'pointer'
                  }}
                >
                  {showSavePreset ? 'Cancel' : 'Save as Preset'}
                </button>
              </div>
            </div>
            {showSavePreset && (
              <div style={{ 
                display: 'flex', 
                gap: '0.5rem', 
                marginBottom: '0.75rem',
                padding: '0.75rem',
                backgroundColor: '#f3f4f6',
                borderRadius: '6px'
              }}>
                <input
                  type="text"
                  value={newPresetName}
                  onChange={(e) => setNewPresetName(e.target.value)}
                  placeholder="Preset name (e.g., 'Startup Focus')"
                  style={{
                    flex: 1,
                    padding: '0.5rem',
                    fontSize: '0.9rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px'
                  }}
                />
                <button
                  onClick={savePreset}
                  style={{
                    padding: '0.5rem 1rem',
                    fontSize: '0.9rem',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor: '#3b82f6',
                    color: 'white',
                    cursor: 'pointer'
                  }}
                >
                  Save
                </button>
              </div>
            )}
            <textarea
              id="additionalInstructions"
              value={additionalInstructions}
              onChange={(e) => setAdditionalInstructions(e.target.value)}
              rows={3}
              placeholder="Add any specific instructions for the AI (e.g., 'Focus on leadership skills', 'Keep it under 300 words', 'Emphasize remote work experience')..."
              style={{
                width: '100%',
                padding: '0.75rem',
                fontSize: '0.95rem',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                fontFamily: 'inherit',
                resize: 'vertical',
                color: '#000000'
              }}
            />
          </div>
        </div>
        <div className="wide-form-section">
          {error && (
            <div className="error-message" style={{ textAlign: 'center', marginBottom: '2rem' }}>{error}</div>
          )}
          <div className="form-actions" style={{ justifyContent: 'center', marginTop: '2rem' }}>
            <button 
              onClick={() => setCurrentPage('edit-profile')}
              className="btn-secondary"
              style={{ minWidth: 150 }}
            >
              Edit Profile
            </button>
            <button 
              onClick={generateCoverLetter} 
              className="btn-primary"
              disabled={isGenerating}
              style={{ minWidth: 150 }}
            >
              {isGenerating ? 'Generating...' : 'Generate Cover Letter'}
            </button>
          </div>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content result-column">
            <div className="modal-header">
              <h2>Generated Cover Letter</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <div
              className="modal-body cover-letter-result"
              style={{
                maxHeight: '60vh',
                overflowY: 'auto',
                paddingBottom: '2rem',
                whiteSpace: 'pre-wrap',
                fontFamily: 'inherit',
                fontSize: '1rem',
                lineHeight: 1.6,
                color: '#374151',
                background: 'transparent',
                border: 'none',
                outline: 'none',
                marginBottom: '1rem',
              }}
            >
              {coverLetter}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={handleCopyCoverLetter} style={{ marginRight: '0.5rem' }}>
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button className="btn-secondary" onClick={handleDownloadPDF} style={{ marginRight: '0.5rem' }}>
                Download as PDF
              </button>
              <button className="btn-primary" onClick={() => setShowModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </BackgroundStars>
  );
};

export default CoverLetterPage; 