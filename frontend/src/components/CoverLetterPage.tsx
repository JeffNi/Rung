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

  const [coverLetter, setCoverLetter] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user);
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    if (user) {
      loadProfile(user.uid);
    }
  }, [user]);

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
      const response = await fetch('http://localhost:8000/generate-cover-letter', {
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
          paragraph_count: 4
        })
      });

      if (response.ok) {
        const data = await response.json();
        setCoverLetter(data.cover_letter);
        setShowModal(true);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to generate cover letter. Please try again.');
      }
    } catch (error) {
      setError('Unable to connect to the server. Please check if the API is running.');
    } finally {
      setIsGenerating(false);
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
        <div className="form-section wide-form-section" style={{ minHeight: '40vh' }}>
          <h3>Job Description</h3>
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
            <div className="modal-body cover-letter-result">
              <textarea
                className="cover-letter-edit-textarea"
                value={coverLetter}
                onChange={e => {
                  setCoverLetter(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = e.target.scrollHeight + 'px';
                }}
                rows={1}
                style={{ width: '100%', fontFamily: 'inherit', fontSize: '1rem', lineHeight: 1.6, color: '#374151', background: 'transparent', border: 'none', outline: 'none', marginBottom: '1rem', overflow: 'hidden', resize: 'none' }}
                ref={el => {
                  if (el) {
                    el.style.height = 'auto';
                    el.style.height = el.scrollHeight + 'px';
                  }
                }}
              />
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