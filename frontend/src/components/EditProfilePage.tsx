import React, { useState, useEffect } from 'react';
import { auth, db } from '../firebase';
import { doc, setDoc, getDoc } from 'firebase/firestore';
import type { User } from 'firebase/auth';
import type { UserProfile } from './ProfileModal';
import '../styles/components/ProfileModal.css';

// Add Experience type
interface Experience {
  title: string;
  achievements: string[];
}

// Add Project type
interface Project {
  title: string;
  details: string[];
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
  // Add editing state for experience titles
  const [editingTitleIdx, setEditingTitleIdx] = useState<number | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [editingProjectTitleIdx, setEditingProjectTitleIdx] = useState<number | null>(null);

  const skillsList = useDynamicList();
  const coursesList = useDynamicList();
  const goalsList = useDynamicList();
  const valuesList = useDynamicList();
  const interestsList = useDynamicList();
  const [editingInterestIdx, setEditingInterestIdx] = useState<number | null>(null);

  const CHIP_MAX = 24;
  const [editingSkillIdx, setEditingSkillIdx] = useState<number | null>(null);
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
        const data = profileDoc.data() as UserProfile;
        // Parse experience
        const expArr: Experience[] = Object.entries(data.experience || {}).map(([title, achievements]) => ({
          title,
          achievements: Array.isArray(achievements) ? achievements : [],
        }));
        setExperiences(expArr);
        // Parse projects
        const projArr: Project[] = Object.entries(data.projects || {}).map(([title, details]) => ({
          title,
          details: Array.isArray(details) ? details : [],
        }));
        setProjects(projArr);
        skillsList.setItems(data.skills || []);
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

  const parseExperience = (experienceText: string): Record<string, string[]> => {
    const experience: Record<string, string[]> = {};
    const sections = experienceText.split('\n\n').filter(s => s.trim());
    sections.forEach(section => {
      const lines = section.split('\n').filter(l => l.trim());
      if (lines.length > 0) {
        const company = lines[0].replace(':', '');
        const tasks = lines.slice(1).filter(task => task.trim().startsWith('-'));
        experience[company] = tasks.map(task => task.trim().substring(1).trim());
      }
    });
    return experience;
  };

  const parseProjects = (projectsText: string): Record<string, string[]> => {
    const projects: Record<string, string[]> = {};
    const sections = projectsText.split('\n\n').filter(s => s.trim());
    sections.forEach(section => {
      const lines = section.split('\n').filter(l => l.trim());
      if (lines.length > 0) {
        const project = lines[0].replace(':', '');
        const details = lines.slice(1).filter(detail => detail.trim().startsWith('-'));
        projects[project] = details.map(detail => detail.trim().substring(1).trim());
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

  // Experience handlers
  const handleExperienceTitleChange = (idx: number, value: string) => {
    setExperiences(prev => prev.map((exp, i) => i === idx ? { ...exp, title: value } : exp));
  };
  const handleAchievementChange = (expIdx: number, achIdx: number, value: string) => {
    setExperiences(prev => prev.map((exp, i) =>
      i === expIdx ? { ...exp, achievements: exp.achievements.map((a, j) => j === achIdx ? value : a) } : exp
    ));
  };
  const addExperience = () => {
    setExperiences(prev => [...prev, { title: '', achievements: [''] }]);
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
  const handleDetailChange = (projIdx: number, detIdx: number, value: string) => {
    setProjects(prev => prev.map((proj, i) =>
      i === projIdx ? { ...proj, details: proj.details.map((d, j) => j === detIdx ? value : d) } : proj
    ));
  };
  const addProject = () => {
    setProjects(prev => [...prev, { title: '', details: [''] }]);
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

  const handleSave = async () => {
    if (!user) return;
    setIsSaving(true);
    try {
      // Convert experiences to object
      const experienceObj: Record<string, string[]> = {};
      experiences.forEach(exp => {
        if (exp.title.trim()) experienceObj[exp.title] = exp.achievements.filter(a => a.trim());
      });
      // Convert projects to object
      const projectsObj: Record<string, string[]> = {};
      projects.forEach(proj => {
        if (proj.title.trim()) projectsObj[proj.title] = proj.details.filter(d => d.trim());
      });
      const newProfile: UserProfile = {
        name: formData.name,
        title: formData.title,
        contact: {
          email: formData.email,
          phone: formData.phone
        },
        skills: skillsList.items.filter(s => s.trim()),
        courses: coursesList.items.filter(s => s.trim()),
        experience: experienceObj,
        projects: projectsObj,
        goals: goalsList.items.filter(s => s.trim()),
        values: valuesList.items.filter(s => s.trim()),
        interests: interestsList.items.filter(s => s.trim()),
        writingSample: formData.writingSample
      };
      await setDoc(doc(db, 'userProfiles', user.uid), newProfile);
      setCurrentPage('cover-letter');
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
                {editingTitleIdx === expIdx ? (
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                    <input
                      type="text"
                      placeholder="Job Title at Company"
                      value={exp.title}
                      onChange={e => handleExperienceTitleChange(expIdx, e.target.value)}
                      style={{ width: '100%', marginRight: 8 }}
                      autoFocus
                    />
                    <button type="button" onClick={() => setEditingTitleIdx(null)} style={{ color: '#3b82f6', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer' }}>✔</button>
                  </div>
                ) : exp.title ? (
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: '1.1rem', color: '#3b82f6' }}>{exp.title}</span>
                    <button type="button" onClick={() => setEditingTitleIdx(expIdx)} style={{ marginLeft: 8, color: '#3b82f6', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer' }}>✎</button>
                  </div>
                ) : (
                  <input
                    type="text"
                    placeholder="Job Title at Company"
                    value={exp.title}
                    onChange={e => handleExperienceTitleChange(expIdx, e.target.value)}
                    style={{ width: '100%', marginBottom: 8 }}
                    autoFocus
                  />
                )}
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
              </div>
            ))}
            <button type="button" onClick={addExperience} style={{ color: '#3b82f6', background: 'none', border: '1px solid #3b82f6', borderRadius: 4, padding: '4px 12px', cursor: 'pointer' }}>+ Add Experience</button>
          </div>
          <div className="form-group">
            <label>Projects</label>
            {projects.map((proj, projIdx) => (
              <div key={projIdx} style={{ border: '1px solid #3b82f6', borderRadius: 8, padding: 12, marginBottom: 16, background: 'rgba(59,130,246,0.05)' }}>
                {editingProjectTitleIdx === projIdx ? (
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                    <input
                      type="text"
                      placeholder="Project Name"
                      value={proj.title}
                      onChange={e => handleProjectTitleChange(projIdx, e.target.value)}
                      style={{ width: '100%', marginRight: 8 }}
                      autoFocus
                    />
                    <button type="button" onClick={() => setEditingProjectTitleIdx(null)} style={{ color: '#3b82f6', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer' }}>✔</button>
                  </div>
                ) : proj.title ? (
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: '1.1rem', color: '#3b82f6' }}>{proj.title}</span>
                    <button type="button" onClick={() => setEditingProjectTitleIdx(projIdx)} style={{ marginLeft: 8, color: '#3b82f6', background: 'none', border: 'none', fontSize: 16, cursor: 'pointer' }}>✎</button>
                  </div>
                ) : (
                  <input
                    type="text"
                    placeholder="Project Name"
                    value={proj.title}
                    onChange={e => handleProjectTitleChange(projIdx, e.target.value)}
                    style={{ width: '100%', marginBottom: 8 }}
                    autoFocus
                  />
                )}
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
              </div>
            ))}
            <button type="button" onClick={addProject} style={{ color: '#3b82f6', background: 'none', border: '1px solid #3b82f6', borderRadius: 4, padding: '4px 12px', cursor: 'pointer' }}>+ Add Project</button>
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
          <div className="form-actions" style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
            <button
              type="button"
              className="btn-cancel"
              style={{ backgroundColor: '#ef4444', color: 'white', minWidth: '100px', height: '36px', fontSize: '0.875rem', border: 'none', borderRadius: '0.375rem', fontWeight: 500, cursor: 'pointer' }}
              onClick={() => setCurrentPage('cover-letter')}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={isSaving} style={{ minWidth: '100px', height: '36px', fontSize: '0.875rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {isSaving ? 'Saving...' : 'Save Profile'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default EditProfilePage; 