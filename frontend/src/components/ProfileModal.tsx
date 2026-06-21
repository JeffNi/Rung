import React, { useState, useEffect } from 'react';
import { auth, db } from '../firebase';
import { doc, getDoc, setDoc } from 'firebase/firestore';
import '../styles/components/ProfileModal.css';
import type { User } from 'firebase/auth';

export interface ExperienceEntry {
  company: string;
  title: string;
  location?: string;
  startDate?: string;
  endDate?: string;
  bullets: string[];
  ai_bullets: Record<string, string[]>;  // job_id -> AI-generated bullets
  context: string;                        // Grounding info for LLM (team size, scale, etc.)
}

export interface UserProfile {
  name: string;
  title: string;
  contact: {
    email: string;
    phone: string;
  };
  skills: string[];
  courses: string[];
  experience: Record<string, ExperienceEntry>;
  projects: Record<string, ExperienceEntry>;
  goals: string[];
  values: string[];
  interests: string[];
  writingSample?: string;
  latexUrl?: string | null;
  latexContent?: string | null;
  searchTitles?: string[];
  skillsToLearn?: string[];
  llmSearchTerms?: string[];
}

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProfileSaved: (profile: UserProfile) => void;
}

const ProfileModal: React.FC<ProfileModalProps> = ({ isOpen, onClose, onProfileSaved }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [profile, setProfile] = useState<UserProfile>({
    name: '',
    title: '',
    contact: {
      email: '',
      phone: ''
    },
    skills: [],
    courses: [],
    experience: {},
    projects: {},
    goals: [],
    values: [],
    interests: []
  });

  // Form state for easier handling
  const [formData, setFormData] = useState({
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

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user);
    });

    return () => unsubscribe();
  }, []);

  useEffect(() => {
    if (isOpen && user) {
      loadProfile(user.uid);
    }
  }, [isOpen, user]);

  const loadProfile = async (userId: string) => {
    setIsLoading(true);
    try {
      const profileDoc = await getDoc(doc(db, 'userProfiles', userId));
      
      if (profileDoc.exists()) {
        const data = profileDoc.data() as UserProfile;
        setProfile(data);
        // Convert arrays and objects back to strings for form
        setFormData({
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

  const formatExperience = (experience: Record<string, ExperienceEntry>): string => {
    if (!experience) return '';
    return Object.entries(experience)
      .map(([company, entry]) => {
        const bullets = entry.bullets || [];
        return `${company}:\n${bullets.join('\n')}`;
      })
      .join('\n\n');
  };

  const formatProjects = (projects: Record<string, ExperienceEntry>): string => {
    if (!projects) return '';
    return Object.entries(projects)
      .map(([project, entry]) => {
        const bullets = entry.bullets || [];
        return `${project}:\n${bullets.join('\n')}`;
      })
      .join('\n\n');
  };

  const parseExperience = (experienceText: string): Record<string, ExperienceEntry> => {
    const experience: Record<string, ExperienceEntry> = {};
    const sections = experienceText.split('\n\n').filter(s => s.trim());
    
    sections.forEach(section => {
      const lines = section.split('\n').filter(l => l.trim());
      if (lines.length > 0) {
        const titleLine = lines[0].replace(':', '');
        const tasks = lines.slice(1).filter(task => task.trim().startsWith('-'));
        // Parse company from "Title at Company" format or use title as company
        const atIndex = titleLine.toLowerCase().indexOf(' at ');
        const title = atIndex > 0 ? titleLine.substring(0, atIndex).trim() : titleLine;
        const company = atIndex > 0 ? titleLine.substring(atIndex + 4).trim() : titleLine;
        // Preserve existing data if available
        const existing = profile.experience?.[titleLine];
        experience[titleLine] = {
          company,
          title,
          location: existing?.location || '',
          startDate: existing?.startDate || '',
          endDate: existing?.endDate || '',
          bullets: tasks.map(task => task.trim().substring(1).trim()),
          ai_bullets: existing?.ai_bullets || {},
          context: existing?.context || ''
        };
      }
    });
    
    return experience;
  };

  const parseProjects = (projectsText: string): Record<string, ExperienceEntry> => {
    const projects: Record<string, ExperienceEntry> = {};
    const sections = projectsText.split('\n\n').filter(s => s.trim());
    
    sections.forEach(section => {
      const lines = section.split('\n').filter(l => l.trim());
      if (lines.length > 0) {
        const project = lines[0].replace(':', '');
        const details = lines.slice(1).filter(detail => detail.trim().startsWith('-'));
        const existing = profile.projects?.[project];
        projects[project] = {
          company: existing?.company || '',
          title: existing?.title || project,
          location: existing?.location || '',
          startDate: existing?.startDate || '',
          endDate: existing?.endDate || '',
          bullets: details.map(detail => detail.trim().substring(1).trim()),
          ai_bullets: existing?.ai_bullets || {},
          context: existing?.context || ''
        };
      }
    });
    
    return projects;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };



  const handleSave = async () => {
    if (!user) return;

    setIsSaving(true);
    try {
      const newProfile: UserProfile = {
        name: formData.name,
        title: formData.title,
        contact: {
          email: formData.email,
          phone: formData.phone
        },
        skills: formData.skills.split(',').map(s => s.trim()).filter(s => s),
        courses: formData.courses.split(',').map(s => s.trim()).filter(s => s),
        experience: parseExperience(formData.experience),
        projects: parseProjects(formData.projects),
        goals: formData.goals.split(',').map(s => s.trim()).filter(s => s),
        values: formData.values.split(',').map(s => s.trim()).filter(s => s),
        interests: formData.interests.split(',').map(s => s.trim()).filter(s => s),
        writingSample: formData.writingSample
      };

      await setDoc(doc(db, 'userProfiles', user.uid), newProfile);
      setProfile(newProfile);
      onProfileSaved(newProfile);
      onClose();
    } catch (error) {
      console.error('Error saving profile:', error);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Create/Edit Profile</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {isLoading ? (
          <div className="modal-loading">Loading profile...</div>
        ) : (
          <div className="modal-body">
            <div className="form-section">
              <h3>Basic Information</h3>
              <div className="form-group">
                <label htmlFor="modal-name">Full Name</label>
                <input
                  type="text"
                  id="modal-name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="modal-title">Professional Title</label>
                <input
                  type="text"
                  id="modal-title"
                  name="title"
                  value={formData.title}
                  onChange={handleInputChange}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="modal-email">Email</label>
                  <input
                    type="email"
                    id="modal-email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="modal-phone">Phone</label>
                  <input
                    type="tel"
                    id="modal-phone"
                    name="phone"
                    value={formData.phone}
                    onChange={handleInputChange}
                  />
                </div>
              </div>
            </div>

            <div className="form-section">
              <h3>Skills & Education</h3>
              <div className="form-group">
                <label htmlFor="modal-skills">Skills (comma-separated)</label>
                <textarea
                  id="modal-skills"
                  name="skills"
                  value={formData.skills}
                  onChange={handleInputChange}
                  rows={3}
                  placeholder="e.g., machine learning, Python, React, etc."
                />
              </div>
              <div className="form-group">
                <label htmlFor="modal-courses">Relevant Courses (comma-separated)</label>
                <textarea
                  id="modal-courses"
                  name="courses"
                  value={formData.courses}
                  onChange={handleInputChange}
                  rows={3}
                  placeholder="e.g., Machine Learning, Data Structures, etc."
                />
              </div>
            </div>

            <div className="form-section">
              <h3>Experience</h3>
              <div className="form-group">
                <label htmlFor="modal-experience">Work Experience</label>
                <textarea
                  id="modal-experience"
                  name="experience"
                  value={formData.experience}
                  onChange={handleInputChange}
                  rows={6}
                  placeholder={`Company Name:
- Achievement or responsibility
- Another achievement

Another Company:
- Achievement or responsibility
- Another achievement`}
                />
                <small>Format: Company name followed by bullet points for achievements</small>
              </div>
            </div>

            <div className="form-section">
              <h3>Projects</h3>
              <div className="form-group">
                <label htmlFor="modal-projects">Projects</label>
                <textarea
                  id="modal-projects"
                  name="projects"
                  value={formData.projects}
                  onChange={handleInputChange}
                  rows={6}
                  placeholder={`Project Name:
- Key feature or achievement
- Another feature

Another Project:
- Key feature or achievement
- Another feature`}
                />
                <small>Format: Project name followed by bullet points for features/achievements</small>
              </div>
            </div>

            <div className="form-section">
              <h3>Personal</h3>
              <div className="form-group">
                <label htmlFor="modal-goals">Career Goals (comma-separated)</label>
                <textarea
                  id="modal-goals"
                  name="goals"
                  value={formData.goals}
                  onChange={handleInputChange}
                  rows={2}
                  placeholder="e.g., Work on impactful AI projects, Lead a team, etc."
                />
              </div>
              <div className="form-group">
                <label htmlFor="modal-values">Personal Values (comma-separated)</label>
                <textarea
                  id="modal-values"
                  name="values"
                  value={formData.values}
                  onChange={handleInputChange}
                  rows={2}
                  placeholder="e.g., creativity, collaboration, innovation, etc."
                />
              </div>
              <div className="form-group">
                <label htmlFor="modal-interests">Interests (comma-separated)</label>
                <textarea
                  id="modal-interests"
                  name="interests"
                  value={formData.interests}
                  onChange={handleInputChange}
                  rows={2}
                  placeholder="e.g., AI research, game development, etc."
                />
              </div>
            </div>

            <div className="form-section">
              <h3>Writing Sample</h3>
              <div className="form-group">
                <label htmlFor="modal-writing-sample">
                  Tell us about a challenging project you worked on and how you overcame obstacles. 
                  What did you learn from the experience? (Minimum 100 words)
                </label>
                <textarea
                  id="modal-writing-sample"
                  name="writingSample"
                  value={formData.writingSample}
                  onChange={handleInputChange}
                  rows={6}
                  placeholder="Describe a challenging project, the obstacles you faced, how you overcame them, and what you learned from the experience..."
                />
                <small>
                  Word count: {formData.writingSample.split(/\s+/).filter(word => word.length > 0).length} 
                  {formData.writingSample.split(/\s+/).filter(word => word.length > 0).length < 100 && 
                    ` (${100 - formData.writingSample.split(/\s+/).filter(word => word.length > 0).length} more words needed)`}
                </small>
              </div>
            </div>
          </div>
        )}

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button 
            className="btn-primary" 
            onClick={handleSave}
            disabled={isSaving || !user}
          >
            {isSaving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileModal; 