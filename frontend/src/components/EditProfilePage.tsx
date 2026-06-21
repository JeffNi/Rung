import React, { useState, useEffect } from 'react';
import { auth, db } from '../firebase';
import { doc, setDoc, getDoc } from 'firebase/firestore';
import type { User } from 'firebase/auth';
import type { UserProfile, ExperienceEntry } from './ProfileModal';
import {
  downloadLatexResumePdf,
  downloadProfileSummaryPdf,
  previewLatexResumePdf,
} from '../lib/profilePdf';
import { normalizeProfileDate } from '../lib/dateUtils';
import { markProfileUpdated } from '../lib/profileRefresh';
import { DateRangeFields } from './DateRangeFields';
import '../styles/components/ProfileModal.css';

// AI bullet with tracking
interface AiBullet {
  text: string;
  jobId: string;
  originalText: string;  // Track original to detect edits
}

// Add Experience type
interface Experience {
  title: string;
  company: string;
  location: string;
  startDate: string;
  endDate: string;
  achievements: string[];
  aiBullets: AiBullet[];
  context: string;
}

// Add Project type
interface Project {
  title: string;
  company: string;
  location: string;
  startDate: string;
  endDate: string;
  details: string[];
  aiBullets: AiBullet[];
  context: string;
}

// Add dynamic list helpers
function useDynamicList(initial: string[] = []) {
  const [items, setItems] = useState<string[]>(initial);
  const [input, setInput] = useState('');
  const addItem = () => {
    if (input.trim()) {
      setItems(prev => [...prev, input.trim()]);
      setInput('');
    }
  };
  const removeItem = (idx: number) => setItems(prev => prev.filter((_, i) => i !== idx));
  const setItem = (idx: number, value: string) => setItems(prev => prev.map((item, i) => i === idx ? value : item));
  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addItem();
    }
  };
  return { items, setItems, input, setInput, addItem, removeItem, setItem, handleInputKeyDown };
}

const EditProfilePage: React.FC<{ setCurrentPage: (page: string) => void }> = ({ setCurrentPage }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
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
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);

  const skillsList = useDynamicList();
  const searchTitlesList = useDynamicList();
  const skillsToLearnList = useDynamicList();
  const coursesList = useDynamicList();
  const goalsList = useDynamicList();
  const valuesList = useDynamicList();
  const interestsList = useDynamicList();
  const [editingInterestIdx, setEditingInterestIdx] = useState<number | null>(null);

  // LaTeX resume state
  const [latexFile, setLatexFile] = useState<File | null>(null);
  const [latexContent, setLatexContent] = useState<string>('');
  const [latexUrl, setLatexUrl] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const CHIP_MAX = 24;
  const [editingSkillIdx, setEditingSkillIdx] = useState<number | null>(null);
  const [editingSearchTitleIdx, setEditingSearchTitleIdx] = useState<number | null>(null);
  const [editingSkillToLearnIdx, setEditingSkillToLearnIdx] = useState<number | null>(null);
  const [editingCourseIdx, setEditingCourseIdx] = useState<number | null>(null);
  const [editingValueIdx, setEditingValueIdx] = useState<number | null>(null);
  const [editingGoalIdx, setEditingGoalIdx] = useState<number | null>(null);

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
    // eslint-disable-next-line
  }, [user]);

  const loadProfile = async (userId: string) => {
    setIsLoading(true);
    try {
      const profileDoc = await getDoc(doc(db, 'userProfiles', userId));
      if (profileDoc.exists()) {
        const data = profileDoc.data() as any; // May be old or new format
        // Parse experience
        const expArr: Experience[] = Object.entries(data.experience || {} as Record<string, any>).map(([title, entry]: [string, any]) => {
          // Handle both old format (string[]) and new format (ExperienceEntry)
          const isOldFormat = Array.isArray(entry);
          const bullets = isOldFormat ? entry : (entry as ExperienceEntry).bullets || [];
          const aiEntries = isOldFormat ? {} : (entry as ExperienceEntry).ai_bullets || {};
          const context = isOldFormat ? '' : (entry as ExperienceEntry).context || '';
          // Flatten ai_bullets into AiBullet[] for UI
          const aiBullets: AiBullet[] = [];
          for (const [jobId, jobBullets] of Object.entries(aiEntries)) {
            for (const b of jobBullets) {
              aiBullets.push({ text: b, jobId, originalText: b });
            }
          }
          const entryData = entry as ExperienceEntry;
          return {
            title,
            company: entryData.company || '',
            location: entryData.location || '',
            startDate: normalizeProfileDate(entryData.startDate || ''),
            endDate: normalizeProfileDate(entryData.endDate || '', true),
            achievements: bullets,
            aiBullets,
            context,
          };
        });
        setExperiences(expArr);
        // Parse projects
        const projArr: Project[] = Object.entries(data.projects || {}).map(([title, entry]) => {
          const isOldFormat = Array.isArray(entry);
          const bullets = isOldFormat ? entry : (entry as ExperienceEntry).bullets || [];
          const aiEntries = isOldFormat ? {} : (entry as ExperienceEntry).ai_bullets || {};
          const context = isOldFormat ? '' : (entry as ExperienceEntry).context || '';
          const aiBullets: AiBullet[] = [];
          for (const [jobId, jobBullets] of Object.entries(aiEntries)) {
            for (const b of jobBullets) {
              aiBullets.push({ text: b, jobId, originalText: b });
            }
          }
          const entryData = entry as ExperienceEntry;
          return {
            title,
            company: entryData.company || '',
            location: entryData.location || '',
            startDate: normalizeProfileDate(entryData.startDate || ''),
            endDate: normalizeProfileDate(entryData.endDate || '', true),
            details: bullets,
            aiBullets,
            context,
          };
        });
        setProjects(projArr);
        skillsList.setItems(data.skills || []);
        searchTitlesList.setItems(data.searchTitles || []);
        skillsToLearnList.setItems(data.skillsToLearn || []);
        coursesList.setItems(data.courses || []);
        goalsList.setItems(data.goals || []);
        valuesList.setItems(data.values || []);
        interestsList.setItems(data.interests || []);
        setFormData({
          ...formData,
          name: data.name || '',
          title: data.title || '',
          email: data.contact?.email || '',
          phone: data.contact?.phone || '',
          interests: data.interests?.join(', ') || '',
          writingSample: data.writingSample || ''
        });
        if (data.latexContent) {
          setLatexContent(data.latexContent);
        }
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Experience handlers
  const handleExperienceTitleChange = (idx: number, value: string) => {
    setExperiences(prev => prev.map((exp, i) => i === idx ? { ...exp, title: value } : exp));
  };
  const handleExperienceCompanyChange = (idx: number, value: string) => {
    setExperiences(prev => prev.map((exp, i) => i === idx ? { ...exp, company: value } : exp));
  };
  const handleExperienceLocationChange = (idx: number, value: string) => {
    setExperiences(prev => prev.map((exp, i) => i === idx ? { ...exp, location: value } : exp));
  };
  const handleExperienceStartDateChange = (idx: number, value: string) => {
    setExperiences(prev => prev.map((exp, i) => i === idx ? { ...exp, startDate: value } : exp));
  };
  const handleExperienceEndDateChange = (idx: number, value: string) => {
    setExperiences(prev => prev.map((exp, i) => i === idx ? { ...exp, endDate: value } : exp));
  };
  const handleAchievementChange = (expIdx: number, achIdx: number, value: string) => {
    setExperiences(prev => prev.map((exp, i) =>
      i === expIdx ? { ...exp, achievements: exp.achievements.map((a, j) => j === achIdx ? value : a) } : exp
    ));
  };
  const addExperience = () => {
    setExperiences(prev => [...prev, { title: '', company: '', location: '', startDate: '', endDate: '', achievements: [''], aiBullets: [], context: '' }]);
  };
  const removeExperience = (idx: number) => {
    setExperiences(prev => prev.filter((_, i) => i !== idx));
  };
  const addAchievement = (expIdx: number) => {
    setExperiences(prev => prev.map((exp, i) =>
      i === expIdx ? { ...exp, achievements: [...exp.achievements, ''] } : exp
    ));
  };
  const removeAchievement = (expIdx: number, achIdx: number) => {
    setExperiences(prev => prev.map((exp, i) =>
      i === expIdx ? { ...exp, achievements: exp.achievements.filter((_, j) => j !== achIdx) } : exp
    ));
  };

  // Project handlers
  const handleProjectTitleChange = (idx: number, value: string) => {
    setProjects(prev => prev.map((proj, i) => i === idx ? { ...proj, title: value } : proj));
  };
  const handleProjectCompanyChange = (idx: number, value: string) => {
    setProjects(prev => prev.map((proj, i) => i === idx ? { ...proj, company: value } : proj));
  };
  const handleProjectLocationChange = (idx: number, value: string) => {
    setProjects(prev => prev.map((proj, i) => i === idx ? { ...proj, location: value } : proj));
  };
  const handleProjectStartDateChange = (idx: number, value: string) => {
    setProjects(prev => prev.map((proj, i) => i === idx ? { ...proj, startDate: value } : proj));
  };
  const handleProjectEndDateChange = (idx: number, value: string) => {
    setProjects(prev => prev.map((proj, i) => i === idx ? { ...proj, endDate: value } : proj));
  };
  const handleDetailChange = (projIdx: number, detIdx: number, value: string) => {
    setProjects(prev => prev.map((proj, i) =>
      i === projIdx ? { ...proj, details: proj.details.map((d, j) => j === detIdx ? value : d) } : proj
    ));
  };
  const addProject = () => {
    setProjects(prev => [...prev, { title: '', company: '', location: '', startDate: '', endDate: '', details: [''], aiBullets: [], context: '' }]);
  };
  const removeProject = (idx: number) => {
    setProjects(prev => prev.filter((_, i) => i !== idx));
  };
  const addDetail = (projIdx: number) => {
    setProjects(prev => prev.map((proj, i) =>
      i === projIdx ? { ...proj, details: [...proj.details, ''] } : proj
    ));
  };
  const removeDetail = (projIdx: number, detIdx: number) => {
    setProjects(prev => prev.map((proj, i) =>
      i === projIdx ? { ...proj, details: proj.details.filter((_, j) => j !== detIdx) } : proj
    ));
  };

  // LaTeX file handlers
  const handleLatexFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.name.endsWith('.tex')) {
      setUploadError('Please upload a .tex file');
      return;
    }
    
    setUploadError('');
    setLatexFile(file);
    
    // Read file content
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setLatexContent(content);
    };
    reader.readAsText(file);
  };

  const readLatexFile = async (): Promise<{ content: string } | null> => {
    if (!latexFile) return null;
    return { content: latexContent };
  };

  const detectProvider = (apiKey: string) => {
    if (apiKey.startsWith('gsk_')) return 'groq';
    if (apiKey.length > 20) return 'gemini';
    return 'gemini';
  };

  const buildProfileSnapshot = (): UserProfile => {
    const experienceObj: Record<string, ExperienceEntry> = {};
    experiences.forEach((exp) => {
      if (exp.title.trim()) {
        const userBullets = [...exp.achievements.filter((a) => a.trim())];
        const remainingAi: Record<string, string[]> = {};
        for (const ab of exp.aiBullets) {
          if (ab.text !== ab.originalText) {
            if (ab.text.trim()) userBullets.push(ab.text);
          } else {
            if (!remainingAi[ab.jobId]) remainingAi[ab.jobId] = [];
            remainingAi[ab.jobId].push(ab.text);
          }
        }
        experienceObj[exp.title] = {
          company: exp.company,
          title: exp.title,
          location: exp.location,
          startDate: exp.startDate,
          endDate: exp.endDate,
          bullets: userBullets,
          ai_bullets: remainingAi,
          context: exp.context,
        };
      }
    });

    const projectsObj: Record<string, ExperienceEntry> = {};
    projects.forEach((proj) => {
      if (proj.title.trim()) {
        const userBullets = [...proj.details.filter((d) => d.trim())];
        const remainingAi: Record<string, string[]> = {};
        for (const ab of proj.aiBullets) {
          if (ab.text !== ab.originalText) {
            if (ab.text.trim()) userBullets.push(ab.text);
          } else {
            if (!remainingAi[ab.jobId]) remainingAi[ab.jobId] = [];
            remainingAi[ab.jobId].push(ab.text);
          }
        }
        projectsObj[proj.title] = {
          company: proj.company,
          title: proj.title,
          location: proj.location,
          startDate: proj.startDate,
          endDate: proj.endDate,
          bullets: userBullets,
          ai_bullets: remainingAi,
          context: proj.context,
        };
      }
    });

    let latexData: { content?: string } = {};
    if (latexFile) {
      latexData = { content: latexContent };
    } else if (latexContent) {
      latexData = { content: latexContent };
    }

    return {
      name: formData.name,
      title: formData.title,
      contact: {
        email: formData.email,
        phone: formData.phone,
      },
      skills: skillsList.items.filter((s) => s.trim()),
      searchTitles: searchTitlesList.items.filter((s) => s.trim()),
      skillsToLearn: skillsToLearnList.items.filter((s) => s.trim()),
      courses: coursesList.items.filter((s) => s.trim()),
      experience: experienceObj,
      projects: projectsObj,
      goals: goalsList.items.filter((s) => s.trim()),
      values: valuesList.items.filter((s) => s.trim()),
      interests: interestsList.items.filter((s) => s.trim()),
      writingSample: formData.writingSample,
      latexUrl: null,
      latexContent: latexData.content || null,
    };
  };

  const handleDownloadProfilePdf = async () => {
    setUploadError('');
    setIsDownloadingPdf(true);
    try {
      const profile = buildProfileSnapshot();
      if (profile.latexContent?.trim()) {
        await downloadLatexResumePdf(profile.latexContent, profile.name);
      } else {
        downloadProfileSummaryPdf(profile);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to generate PDF';
      setUploadError(message);
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const handleSave = async () => {
    if (!user) return;
    setIsSaving(true);
    try {
      const newProfile = buildProfileSnapshot();
      await setDoc(doc(db, 'userProfiles', user.uid), newProfile);

      const apiKey = localStorage.getItem('apiKey') || '';
      if (apiKey.trim()) {
        try {
          const baseApi = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
          const suggestRes = await fetch(`${baseApi}/suggest-search-terms`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_profile: newProfile,
              api_key: apiKey,
              provider: detectProvider(apiKey),
            }),
          });
          if (suggestRes.ok) {
            const suggestData = await suggestRes.json();
            const llmTerms = suggestData.llmSearchTerms || [];
            if (llmTerms.length > 0) {
              await setDoc(doc(db, 'userProfiles', user.uid), { llmSearchTerms: llmTerms }, { merge: true });
            }
          }
        } catch (suggestErr) {
          console.warn('LLM search term suggestion failed:', suggestErr);
        }
      }

      markProfileUpdated();
      setCurrentPage('apply');
    } catch (error) {
      console.error('Error saving profile:', error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="page-container" style={{ color: 'white' }}>
      <div className="page-header">
        <h1 style={{ color: '#3b82f6' }}>Edit Profile</h1>
        <p style={{ color: 'white' }}>Update your information for personalized cover letters and resumes.</p>
      </div>
      {isLoading ? (
        <div className="loading">Loading...</div>
      ) : (
        <form className="form-section" onSubmit={e => { e.preventDefault(); handleSave(); }}>
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <input type="text" id="name" name="name" value={formData.name} onChange={handleInputChange} required />
          </div>
          <div className="form-group">
            <label htmlFor="title">Professional Title</label>
            <input type="text" id="title" name="title" value={formData.title} onChange={handleInputChange} />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input type="email" id="email" name="email" value={formData.email} onChange={handleInputChange} required />
            </div>
            <div className="form-group">
              <label htmlFor="phone">Phone</label>
              <input type="tel" id="phone" name="phone" value={formData.phone} onChange={handleInputChange} />
            </div>
          </div>
          <div className="form-group">
            <label>Experience</label>
            {experiences.map((exp, expIdx) => (
              <div key={expIdx} style={{ border: '1px solid #3b82f6', borderRadius: 8, padding: 12, marginBottom: 16, background: 'rgba(59,130,246,0.05)' }}>
                {/* Title and Company - both in blue */}
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8, gap: 8 }}>
                  <input
                    type="text"
                    placeholder="Job Title"
                    value={exp.title}
                    onChange={e => handleExperienceTitleChange(expIdx, e.target.value)}
                    style={{ flex: 1, fontWeight: 600, fontSize: '1.1rem', color: '#3b82f6', background: 'transparent', border: 'none', borderBottom: '1px dashed #3b82f6', padding: '4px 0' }}
                  />
                  <span style={{ color: '#64748b' }}>at</span>
                  <input
                    type="text"
                    placeholder="Company"
                    value={exp.company}
                    onChange={e => handleExperienceCompanyChange(expIdx, e.target.value)}
                    style={{ flex: 1, fontWeight: 600, fontSize: '1.1rem', color: '#3b82f6', background: 'transparent', border: 'none', borderBottom: '1px dashed #3b82f6', padding: '4px 0' }}
                  />
                </div>
                {/* Location and Dates */}
                <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                  <input
                    type="text"
                    placeholder="Location (e.g., San Francisco, CA)"
                    value={exp.location}
                    onChange={e => handleExperienceLocationChange(expIdx, e.target.value)}
                    style={{ flex: 1, minWidth: 140, fontSize: '0.875rem' }}
                  />
                  <DateRangeFields
                    startDate={exp.startDate}
                    endDate={exp.endDate}
                    onStartChange={(value) => handleExperienceStartDateChange(expIdx, value)}
                    onEndChange={(value) => handleExperienceEndDateChange(expIdx, value)}
                  />
                </div>
                {exp.achievements.map((ach, achIdx) => (
                  <div key={achIdx} style={{ display: 'flex', alignItems: 'center', marginBottom: 4, transition: 'background 0.2s' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#e0e7ff'}
                    onMouseLeave={e => e.currentTarget.style.background = ''}
                  >
                    <input
                      type="text"
                      placeholder={`Achievement ${achIdx + 1}`}
                      value={ach}
                      onChange={e => handleAchievementChange(expIdx, achIdx, e.target.value)}
                      style={{ flex: 1 }}
                    />
                    {exp.achievements.length > 1 && (
                      <button type="button" onClick={() => removeAchievement(expIdx, achIdx)} style={{ marginLeft: 8, color: '#ef4444', background: 'none', border: 'none', fontSize: 18, cursor: 'pointer' }}>×</button>
                    )}
                  </div>
                ))}
                <button type="button" onClick={() => addAchievement(expIdx)} style={{ color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer', marginTop: 4 }}>+ Add Achievement</button>
                <button type="button" onClick={() => removeExperience(expIdx)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', marginLeft: 12 }}>Remove Experience</button>
                {/* AI-generated bullets with dark background */}
                {exp.aiBullets.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <span style={{ fontSize: '0.85rem', color: '#9ca3af', fontStyle: 'italic' }}>AI-Generated Bullets</span>
                    {exp.aiBullets.map((ab, abIdx) => (
                      <div key={`ai-${abIdx}`} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                        <input
                          type="text"
                          value={ab.text}
                          onChange={e => {
                            const val = e.target.value;
                            setExperiences(prev => prev.map((ex, i) =>
                              i === expIdx ? { ...ex, aiBullets: ex.aiBullets.map((b, j) => j === abIdx ? { ...b, text: val } : b) } : ex
                            ));
                          }}
                          style={{ flex: 1, background: '#1e293b', color: '#e2e8f0', border: '1px solid #475569', borderRadius: 4, padding: '4px 8px' }}
                        />
                        <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: 6, whiteSpace: 'nowrap' }}>{ab.jobId}</span>
                        <button type="button" onClick={() => {
                          setExperiences(prev => prev.map((ex, i) =>
                            i === expIdx ? { ...ex, aiBullets: ex.aiBullets.filter((_, j) => j !== abIdx) } : ex
                          ));
                        }} style={{ marginLeft: 4, color: '#ef4444', background: 'none', border: 'none', fontSize: 18, cursor: 'pointer' }}>×</button>
                      </div>
                    ))}
                  </div>
                )}
                {/* Context field */}
                <div style={{ marginTop: 8 }}>
                  <textarea
                    placeholder="Context: team size, company scale, technologies, metrics (helps AI generate better bullets)"
                    value={exp.context}
                    onChange={e => setExperiences(prev => prev.map((ex, i) => i === expIdx ? { ...ex, context: e.target.value } : ex))}
                    rows={2}
                    style={{ width: '100%', fontSize: '0.85rem', background: 'rgba(59,130,246,0.02)', border: '1px dashed #475569', borderRadius: 4, padding: 8, color: '#94a3b8', resize: 'vertical' }}
                  />
                </div>
              </div>
            ))}
            <button type="button" onClick={addExperience} style={{ color: '#3b82f6', background: 'none', border: '1px solid #3b82f6', borderRadius: 4, padding: '4px 12px', cursor: 'pointer' }}>+ Add Experience</button>
          </div>
          <div className="form-group">
            <label>Projects</label>
            {projects.map((proj, projIdx) => (
              <div key={projIdx} style={{ border: '1px solid #3b82f6', borderRadius: 8, padding: 12, marginBottom: 16, background: 'rgba(59,130,246,0.05)' }}>
                {/* Title and Company - both in blue */}
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8, gap: 8 }}>
                  <input
                    type="text"
                    placeholder="Project Name"
                    value={proj.title}
                    onChange={e => handleProjectTitleChange(projIdx, e.target.value)}
                    style={{ flex: 1, fontWeight: 600, fontSize: '1.1rem', color: '#3b82f6', background: 'transparent', border: 'none', borderBottom: '1px dashed #3b82f6', padding: '4px 0' }}
                  />
                  <span style={{ color: '#64748b' }}>at</span>
                  <input
                    type="text"
                    placeholder="Organization (optional)"
                    value={proj.company}
                    onChange={e => handleProjectCompanyChange(projIdx, e.target.value)}
                    style={{ flex: 1, fontWeight: 600, fontSize: '1.1rem', color: '#3b82f6', background: 'transparent', border: 'none', borderBottom: '1px dashed #3b82f6', padding: '4px 0' }}
                  />
                </div>
                {/* Location and Dates */}
                <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                  <input
                    type="text"
                    placeholder="Location (optional)"
                    value={proj.location}
                    onChange={e => handleProjectLocationChange(projIdx, e.target.value)}
                    style={{ flex: 1, minWidth: 140, fontSize: '0.875rem' }}
                  />
                  <DateRangeFields
                    startDate={proj.startDate}
                    endDate={proj.endDate}
                    onStartChange={(value) => handleProjectStartDateChange(projIdx, value)}
                    onEndChange={(value) => handleProjectEndDateChange(projIdx, value)}
                  />
                </div>
                {proj.details.map((det, detIdx) => (
                  <div key={detIdx} style={{ display: 'flex', alignItems: 'center', marginBottom: 4, transition: 'background 0.2s' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#e0e7ff'}
                    onMouseLeave={e => e.currentTarget.style.background = ''}
                  >
                    <input
                      type="text"
                      placeholder={`Detail ${detIdx + 1}`}
                      value={det}
                      onChange={e => handleDetailChange(projIdx, detIdx, e.target.value)}
                      style={{ flex: 1 }}
                    />
                    {proj.details.length > 1 && (
                      <button type="button" onClick={() => removeDetail(projIdx, detIdx)} style={{ marginLeft: 8, color: '#ef4444', background: 'none', border: 'none', fontSize: 18, cursor: 'pointer' }}>×</button>
                    )}
                  </div>
                ))}
                <button type="button" onClick={() => addDetail(projIdx)} style={{ color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer', marginTop: 4 }}>+ Add Detail</button>
                <button type="button" onClick={() => removeProject(projIdx)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', marginLeft: 12 }}>Remove Project</button>
                {/* AI-generated bullets with dark background */}
                {proj.aiBullets.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <span style={{ fontSize: '0.85rem', color: '#9ca3af', fontStyle: 'italic' }}>AI-Generated Bullets</span>
                    {proj.aiBullets.map((ab, abIdx) => (
                      <div key={`ai-${abIdx}`} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                        <input
                          type="text"
                          value={ab.text}
                          onChange={e => {
                            const val = e.target.value;
                            setProjects(prev => prev.map((p, i) =>
                              i === projIdx ? { ...p, aiBullets: p.aiBullets.map((b, j) => j === abIdx ? { ...b, text: val } : b) } : p
                            ));
                          }}
                          style={{ flex: 1, background: '#1e293b', color: '#e2e8f0', border: '1px solid #475569', borderRadius: 4, padding: '4px 8px' }}
                        />
                        <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: 6, whiteSpace: 'nowrap' }}>{ab.jobId}</span>
                        <button type="button" onClick={() => {
                          setProjects(prev => prev.map((p, i) =>
                            i === projIdx ? { ...p, aiBullets: p.aiBullets.filter((_, j) => j !== abIdx) } : p
                          ));
                        }} style={{ marginLeft: 4, color: '#ef4444', background: 'none', border: 'none', fontSize: 18, cursor: 'pointer' }}>×</button>
                      </div>
                    ))}
                  </div>
                )}
                {/* Context field */}
                <div style={{ marginTop: 8 }}>
                  <textarea
                    placeholder="Context: team size, company scale, technologies, metrics (helps AI generate better bullets)"
                    value={proj.context}
                    onChange={e => setProjects(prev => prev.map((p, i) => i === projIdx ? { ...p, context: e.target.value } : p))}
                    rows={2}
                    style={{ width: '100%', fontSize: '0.85rem', background: 'rgba(59,130,246,0.02)', border: '1px dashed #475569', borderRadius: 4, padding: 8, color: '#94a3b8', resize: 'vertical' }}
                  />
                </div>
              </div>
            ))}
            <button type="button" onClick={addProject} style={{ color: '#3b82f6', background: 'none', border: '1px solid #3b82f6', borderRadius: 4, padding: '4px 12px', cursor: 'pointer' }}>+ Add Project</button>
          </div>
          <div className="form-group">
            <label>Job search titles <span style={{ color: '#94a3b8', fontWeight: 400 }}>(required for Jobs page)</span></label>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: 8 }}>
              Role names to search on Google Jobs — e.g. ML Engineer, AI Engineer. Not your resume title.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', minHeight: 40, marginBottom: 4 }}>
              {searchTitlesList.items.map((title, idx) => (
                editingSearchTitleIdx === idx ? (
                  <input
                    key={idx}
                    type="text"
                    value={title}
                    autoFocus
                    onChange={e => searchTitlesList.setItem(idx, e.target.value)}
                    onBlur={() => setEditingSearchTitleIdx(null)}
                    onKeyDown={e => { if (e.key === 'Enter') setEditingSearchTitleIdx(null); }}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200 }}
                  />
                ) : (
                  <span
                    key={idx}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer' }}
                    title={title}
                    onClick={() => setEditingSearchTitleIdx(idx)}
                  >
                    {title.length > CHIP_MAX ? title.slice(0, CHIP_MAX) + '...' : title}
                    <button type="button" onClick={e => { e.stopPropagation(); searchTitlesList.removeItem(idx); }} style={{ color: '#ef4444', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', lineHeight: 1, paddingLeft: 6, paddingRight: 0 }}>&times;</button>
                  </span>
                )
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
              <input
                type="text"
                placeholder="Add search title"
                value={searchTitlesList.input}
                onChange={e => searchTitlesList.setInput(e.target.value)}
                onKeyDown={searchTitlesList.handleInputKeyDown}
                style={{ minWidth: 140, borderRadius: 16, padding: '4px 12px', fontSize: 14, border: '1px solid #3b82f6', outline: 'none' }}
              />
              <button type="button" onClick={searchTitlesList.addItem} style={{ color: '#3b82f6', background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>+</button>
            </div>
          </div>
          <div className="form-group">
            <label>Skills to learn</label>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: 8 }}>
              Growth areas — used for search keywords and future ranking boosts.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', minHeight: 40, marginBottom: 4 }}>
              {skillsToLearnList.items.map((skill, idx) => (
                editingSkillToLearnIdx === idx ? (
                  <input
                    key={idx}
                    type="text"
                    value={skill}
                    autoFocus
                    onChange={e => skillsToLearnList.setItem(idx, e.target.value)}
                    onBlur={() => setEditingSkillToLearnIdx(null)}
                    onKeyDown={e => { if (e.key === 'Enter') setEditingSkillToLearnIdx(null); }}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(16,185,129,0.08)', color: '#047857', borderRadius: 16, padding: '4px 12px', fontSize: 14, border: '1px solid #10b981', maxWidth: 200 }}
                  />
                ) : (
                  <span
                    key={idx}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(16,185,129,0.08)', color: '#047857', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #10b981', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer' }}
                    title={skill}
                    onClick={() => setEditingSkillToLearnIdx(idx)}
                  >
                    {skill.length > CHIP_MAX ? skill.slice(0, CHIP_MAX) + '...' : skill}
                    <button type="button" onClick={e => { e.stopPropagation(); skillsToLearnList.removeItem(idx); }} style={{ color: '#ef4444', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', lineHeight: 1, paddingLeft: 6, paddingRight: 0 }}>&times;</button>
                  </span>
                )
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
              <input
                type="text"
                placeholder="Add skill to learn"
                value={skillsToLearnList.input}
                onChange={e => skillsToLearnList.setInput(e.target.value)}
                onKeyDown={skillsToLearnList.handleInputKeyDown}
                style={{ minWidth: 140, borderRadius: 16, padding: '4px 12px', fontSize: 14, border: '1px solid #10b981', outline: 'none' }}
              />
              <button type="button" onClick={skillsToLearnList.addItem} style={{ color: '#10b981', background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>+</button>
            </div>
          </div>
          <div className="form-group">
            <label>Skills</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', minHeight: 40, marginBottom: 4 }}>
              {skillsList.items.map((skill, idx) => (
                editingSkillIdx === idx ? (
                  <input
                    key={idx}
                    type="text"
                    value={skill}
                    autoFocus
                    onChange={e => skillsList.setItem(idx, e.target.value)}
                    onBlur={() => setEditingSkillIdx(null)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') setEditingSkillIdx(null);
                    }}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, marginRight: 0 }}
                  />
                ) : (
                  <span
                    key={idx}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer' }}
                    title={skill}
                    onClick={() => setEditingSkillIdx(idx)}
                  >
                    {skill.length > CHIP_MAX ? skill.slice(0, CHIP_MAX) + '...' : skill}
                    <button type="button" onClick={e => { e.stopPropagation(); skillsList.removeItem(idx); }} style={{ color: '#ef4444', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', lineHeight: 1, paddingLeft: 6, paddingRight: 0 }}>&times;</button>
                  </span>
                )
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
              <input
                type="text"
                placeholder="Add skill"
                value={skillsList.input}
                onChange={e => skillsList.setInput(e.target.value)}
                onKeyDown={skillsList.handleInputKeyDown}
                style={{ minWidth: 100, borderRadius: 16, padding: '4px 12px', fontSize: 14, border: '1px solid #3b82f6', outline: 'none' }}
              />
              <button type="button" onClick={skillsList.addItem} style={{ color: '#3b82f6', background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>+</button>
            </div>
          </div>
          <div className="form-group">
            <label>Courses</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', minHeight: 40, marginBottom: 4 }}>
              {coursesList.items.map((course, idx) => (
                editingCourseIdx === idx ? (
                  <input
                    key={idx}
                    type="text"
                    value={course}
                    autoFocus
                    onChange={e => coursesList.setItem(idx, e.target.value)}
                    onBlur={() => setEditingCourseIdx(null)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') setEditingCourseIdx(null);
                    }}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, marginRight: 0 }}
                  />
                ) : (
                  <span
                    key={idx}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer' }}
                    title={course}
                    onClick={() => setEditingCourseIdx(idx)}
                  >
                    {course.length > CHIP_MAX ? course.slice(0, CHIP_MAX) + '...' : course}
                    <button type="button" onClick={e => { e.stopPropagation(); coursesList.removeItem(idx); }} style={{ color: '#ef4444', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', lineHeight: 1, paddingLeft: 6, paddingRight: 0 }}>&times;</button>
                  </span>
                )
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
              <input
                type="text"
                placeholder="Add course"
                value={coursesList.input}
                onChange={e => coursesList.setInput(e.target.value)}
                onKeyDown={coursesList.handleInputKeyDown}
                style={{ minWidth: 100, borderRadius: 16, padding: '4px 12px', fontSize: 14, border: '1px solid #3b82f6', outline: 'none' }}
              />
              <button type="button" onClick={coursesList.addItem} style={{ color: '#3b82f6', background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>+</button>
            </div>
          </div>
          <div className="form-group">
            <label>Values</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', minHeight: 40, marginBottom: 4 }}>
              {valuesList.items.map((value, idx) => (
                editingValueIdx === idx ? (
                  <input
                    key={idx}
                    type="text"
                    value={value}
                    autoFocus
                    onChange={e => valuesList.setItem(idx, e.target.value)}
                    onBlur={() => setEditingValueIdx(null)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') setEditingValueIdx(null);
                    }}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, marginRight: 0 }}
                  />
                ) : (
                  <span
                    key={idx}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer' }}
                    title={value}
                    onClick={() => setEditingValueIdx(idx)}
                  >
                    {value.length > CHIP_MAX ? value.slice(0, CHIP_MAX) + '...' : value}
                    <button type="button" onClick={e => { e.stopPropagation(); valuesList.removeItem(idx); }} style={{ color: '#ef4444', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', lineHeight: 1, paddingLeft: 6, paddingRight: 0 }}>&times;</button>
                  </span>
                )
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
              <input
                type="text"
                placeholder="Add value"
                value={valuesList.input}
                onChange={e => valuesList.setInput(e.target.value)}
                onKeyDown={valuesList.handleInputKeyDown}
                style={{ minWidth: 100, borderRadius: 16, padding: '4px 12px', fontSize: 14, border: '1px solid #3b82f6', outline: 'none' }}
              />
              <button type="button" onClick={valuesList.addItem} style={{ color: '#3b82f6', background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>+</button>
            </div>
          </div>
          <div className="form-group">
            <label>Goals</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', minHeight: 40, marginBottom: 4 }}>
              {goalsList.items.map((goal, idx) => (
                editingGoalIdx === idx ? (
                  <input
                    key={idx}
                    type="text"
                    value={goal}
                    autoFocus
                    onChange={e => goalsList.setItem(idx, e.target.value)}
                    onBlur={() => setEditingGoalIdx(null)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') setEditingGoalIdx(null);
                    }}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, marginRight: 0 }}
                  />
                ) : (
                  <span
                    key={idx}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer' }}
                    title={goal}
                    onClick={() => setEditingGoalIdx(idx)}
                  >
                    {goal.length > CHIP_MAX ? goal.slice(0, CHIP_MAX) + '...' : goal}
                    <button type="button" onClick={e => { e.stopPropagation(); goalsList.removeItem(idx); }} style={{ color: '#ef4444', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', lineHeight: 1, paddingLeft: 6, paddingRight: 0 }}>&times;</button>
                  </span>
                )
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
              <input
                type="text"
                placeholder="Add goal"
                value={goalsList.input}
                onChange={e => goalsList.setInput(e.target.value)}
                onKeyDown={goalsList.handleInputKeyDown}
                style={{ minWidth: 100, borderRadius: 16, padding: '4px 12px', fontSize: 14, border: '1px solid #3b82f6', outline: 'none' }}
              />
              <button type="button" onClick={goalsList.addItem} style={{ color: '#3b82f6', background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>+</button>
            </div>
          </div>
          <div className="form-group">
            <label>Interests</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', minHeight: 40, marginBottom: 4 }}>
              {interestsList.items.map((interest, idx) => (
                editingInterestIdx === idx ? (
                  <input
                    key={idx}
                    type="text"
                    value={interest}
                    autoFocus
                    onChange={e => interestsList.setItem(idx, e.target.value)}
                    onBlur={() => setEditingInterestIdx(null)}
                    onKeyDown={e => { if (e.key === 'Enter') setEditingInterestIdx(null); }}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, marginRight: 0 }}
                  />
                ) : (
                  <span
                    key={idx}
                    style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(59,130,246,0.05)', color: '#1e40af', borderRadius: 16, padding: '4px 12px 4px 12px', fontSize: 14, border: '1px solid #3b82f6', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer' }}
                    title={interest}
                    onClick={() => setEditingInterestIdx(idx)}
                  >
                    {interest.length > CHIP_MAX ? interest.slice(0, CHIP_MAX) + '...' : interest}
                    <button type="button" onClick={e => { e.stopPropagation(); interestsList.removeItem(idx); }} style={{ color: '#ef4444', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', lineHeight: 1, paddingLeft: 6, paddingRight: 0 }}>&times;</button>
                  </span>
                )
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
              <input
                type="text"
                placeholder="Add interest"
                value={interestsList.input}
                onChange={e => interestsList.setInput(e.target.value)}
                onKeyDown={interestsList.handleInputKeyDown}
                style={{ minWidth: 100, borderRadius: 16, padding: '4px 12px', fontSize: 14, border: '1px solid #3b82f6', outline: 'none' }}
              />
              <button type="button" onClick={interestsList.addItem} style={{ color: '#3b82f6', background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>+</button>
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="writingSample">Writing Sample (optional)</label>
            <textarea id="writingSample" name="writingSample" value={formData.writingSample} onChange={handleInputChange} rows={3} />
          </div>
          <div className="form-group" style={{ border: '1px solid #3b82f6', borderRadius: 8, padding: 16, background: 'rgba(59,130,246,0.05)' }}>
            <label style={{ fontWeight: 600, color: '#3b82f6', marginBottom: 8, display: 'block' }}>
              LaTeX Resume (optional)
            </label>
            <p style={{ fontSize: '0.9rem', marginBottom: 12, color: '#9ca3af' }}>
              Upload your LaTeX resume template. We'll use this to generate tailored versions by modifying specific sections.
            </p>
            <input
              type="file"
              accept=".tex"
              onChange={handleLatexFileChange}
              style={{ display: 'none' }}
              id="latex-upload"
            />
            <label htmlFor="latex-upload" style={{ cursor: 'pointer' }}>
              <div style={{
                border: '2px dashed #3b82f6',
                borderRadius: 8,
                padding: '20px',
                textAlign: 'center',
                background: 'rgba(59,130,246,0.1)'
              }}>
                {latexFile ? (
                  <div>
                    <span style={{ color: '#3b82f6', fontWeight: 500 }}> {latexFile.name}</span>
                    <p style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: 4 }}>
                      {isUploading ? 'Uploading...' : 'Ready to upload on save'}
                    </p>
                  </div>
                ) : latexContent ? (
                  <div>
                    <span style={{ color: '#22c55e', fontWeight: 500 }}>✓ Resume template saved</span>
                    <p style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: 4 }}>
                      Upload a new file to replace it
                    </p>
                  </div>
                ) : (
                  <div>
                    <span style={{ fontSize: '1.5rem' }}> </span>
                    <p style={{ color: '#3b82f6', marginTop: 8 }}>Click to upload .tex file</p>
                    <p style={{ fontSize: '0.8rem', color: '#6b7280' }}>Supports: .tex</p>
                  </div>
                )}
              </div>
            </label>
            {uploadError && (
              <p style={{ color: '#ef4444', fontSize: '0.85rem', marginTop: 8 }}>{uploadError}</p>
            )}
            {latexContent && (
              <div style={{ marginTop: 12 }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    onClick={async () => {
                      setUploadError('');
                      try {
                        await previewLatexResumePdf(latexContent);
                      } catch (err) {
                        const message = err instanceof Error ? err.message : 'Failed to compile PDF';
                        setUploadError(message);
                      }
                    }}
                    style={{ fontSize: '0.85rem', color: '#3b82f6', background: 'none', border: '1px solid #3b82f6', borderRadius: 4, padding: '4px 10px', cursor: 'pointer' }}
                  >
                    Preview compiled PDF
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      setUploadError('');
                      try {
                        await downloadLatexResumePdf(latexContent, formData.name);
                      } catch (err) {
                        const message = err instanceof Error ? err.message : 'Failed to download PDF';
                        setUploadError(message);
                      }
                    }}
                    style={{ fontSize: '0.85rem', color: '#22c55e', background: 'none', border: '1px solid #22c55e', borderRadius: 4, padding: '4px 10px', cursor: 'pointer' }}
                  >
                    Download resume PDF
                  </button>
                  <button
                    type="button"
                    onClick={() => downloadProfileSummaryPdf(buildProfileSnapshot())}
                    style={{ fontSize: '0.85rem', color: '#6b7280', background: 'none', border: '1px solid #6b7280', borderRadius: 4, padding: '4px 10px', cursor: 'pointer' }}
                  >
                    Download profile summary
                  </button>
                  <details style={{ display: 'inline' }}>
                    <summary style={{ color: '#6b7280', cursor: 'pointer', fontSize: '0.85rem', listStyle: 'none' }}>View source</summary>
                    <pre style={{
                      background: '#1f2937',
                      padding: 12,
                      borderRadius: 4,
                      fontSize: '0.8rem',
                      maxHeight: 200,
                      overflow: 'auto',
                      marginTop: 8,
                      color: '#e5e7eb'
                    }}>
                      {latexContent.slice(0, 2000)}{latexContent.length > 2000 ? '\n...' : ''}
                    </pre>
                  </details>
                </div>
              </div>
            )}
          </div>
          <div className="form-actions" style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn-cancel"
              style={{ backgroundColor: '#ef4444', color: 'white', minWidth: '100px', height: '36px', fontSize: '0.875rem', border: 'none', borderRadius: '0.375rem', fontWeight: 500, cursor: 'pointer' }}
              onClick={() => setCurrentPage('apply')}
            >
              Cancel
            </button>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                disabled={isDownloadingPdf}
                onClick={handleDownloadProfilePdf}
                style={{
                  minWidth: '120px',
                  height: '36px',
                  fontSize: '0.875rem',
                  border: '1px solid #3b82f6',
                  borderRadius: '0.375rem',
                  fontWeight: 500,
                  cursor: isDownloadingPdf ? 'not-allowed' : 'pointer',
                  background: 'transparent',
                  color: '#3b82f6',
                  opacity: isDownloadingPdf ? 0.7 : 1,
                }}
              >
                {isDownloadingPdf
                  ? 'Generating...'
                  : latexContent
                    ? 'Download resume PDF'
                    : 'Download profile PDF'}
              </button>
              <button type="submit" className="btn-primary" disabled={isSaving} style={{ minWidth: '100px', height: '36px', fontSize: '0.875rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {isSaving ? 'Saving...' : 'Save Profile'}
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  );
};

export default EditProfilePage;