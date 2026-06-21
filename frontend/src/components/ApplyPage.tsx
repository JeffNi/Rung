import React, { useState, useEffect } from 'react';
import { auth, db } from '../firebase';
import { doc, getDoc } from 'firebase/firestore';
import type { User } from 'firebase/auth';
import type { UserProfile } from './ProfileModal';
import BackgroundStars from './BackgroundStars';
import '../styles/components/CoverLetterPage.css';
import {
  readApplyJobContext,
  clearApplyJobContext,
  saveApplicationSnapshot,
  type ApplyJobContext,
} from '../lib/jobPostings';
import jsPDF from 'jspdf';

interface ApplyResult {
  resume?: string;
  coverLetter?: string;
}

const ApplyPage: React.FC<{ setCurrentPage: (page: string) => void }> = ({ setCurrentPage }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

  const [jobDescription, setJobDescription] = useState('');
  const [additionalInstructions, setAdditionalInstructions] = useState('');

  // Auto-detect provider from API key
  const getDetectedProvider = () => {
    const apiKey = localStorage.getItem('apiKey') || '';
    if (apiKey.startsWith('gsk_')) return 'groq';
    if (apiKey.length > 20) return 'gemini'; // Gemini keys are long
    return 'unknown';
  };
  
  const provider = getDetectedProvider();

  const [result, setResult] = useState<ApplyResult | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [copied, setCopied] = useState<{resume: boolean, coverLetter: boolean}>({ resume: false, coverLetter: false });
  const [hasApiKey, setHasApiKey] = useState(false);
  const [activeTab, setActiveTab] = useState<'resume' | 'coverLetter'>('resume');
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionResult, setExtractionResult] = useState<{
    keyword_to_experiences: Record<string, string[]>;
    easy_no_match: string[];
    drop: string[];
    all_keywords_to_include: string[];
    must_have: string[];
    nice_to_have: string[];
    token_usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number; calls: number };
    elapsed_seconds?: number;
  } | null>(null);
  const [isGeneratingStrategy, setIsGeneratingStrategy] = useState(false);
  const [isGeneratingResume, setIsGeneratingResume] = useState(false);
  const [resumeResult, setResumeResult] = useState<{
    success: boolean;
    latex_source: string;
    pdf_base64: string;
    strategy: {
      experiences: Array<{
        title: string;
        should_include: boolean;
        keywords_covered: string[];
        dotjots: string[];
      }>;
      skills_strategy: {
        front_load: string[];
        add: string[];
        keep: string[];
        deprioritize: string[];
      };
      title_suggestions: Array<{
        original: string;
        suggested: string;
        reason: string;
      }>;
    };
    token_usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number; calls: number };
    elapsed_seconds?: number;
  } | null>(null);
  const [showLatexSource, setShowLatexSource] = useState(false);
  const [applyJobContext, setApplyJobContext] = useState<ApplyJobContext | null>(null);
  const [activeJobId, setActiveJobId] = useState<string>(() => `job_${Date.now()}`);
  const [markAppliedMsg, setMarkAppliedMsg] = useState('');
  const [strategyResult, setStrategyResult] = useState<{
    experiences: Array<{
      title: string;
      should_include: boolean;
      keywords_covered: string[];
      dotjots: string[];
    }>;
    skills_strategy: {
      front_load: string[];
      add: string[];
      keep: string[];
      deprioritize: string[];
    };
    title_suggestions: Array<{
      original: string;
      suggested: string;
      reason: string;
    }>;
    keywords: {
      must_have: string[];
      nice_to_have: string[];
      matched: string[];
      easy_no_match: string[];
      drop: string[];
    };
    token_usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number; calls: number };
    elapsed_seconds?: number;
  } | null>(null);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user);
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    const apiKey = localStorage.getItem('apiKey');
    setHasApiKey(!!apiKey && apiKey.trim().length > 0);
  }, []);

  useEffect(() => {
    if (user) {
      loadProfile(user.uid);
    }
  }, [user]);

  useEffect(() => {
    const ctx = readApplyJobContext();
    if (ctx) {
      setApplyJobContext(ctx);
      setActiveJobId(ctx.job_id);
      const header = `${ctx.title} at ${ctx.company}\n\n`;
      setJobDescription(header + ctx.description);
      clearApplyJobContext();
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
        setUserProfile(profileDoc.data() as UserProfile);
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExtractKeywords = async () => {
    if (!userProfile) {
      setError('Please complete your profile first');
      return;
    }
    if (!jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }

    setIsExtracting(true);
    setError('');
    setExtractionResult(null);

    try {
      const baseApi = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
      const url = `${baseApi}/extract-keywords`;

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_profile: userProfile,
          job_description: jobDescription,
          provider: provider,
          api_key: localStorage.getItem('apiKey') || ''
        })
      });

      if (response.ok) {
        const data = await response.json();
        setExtractionResult(data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to extract keywords.');
      }
    } catch (error) {
      setError('Unable to connect to the server. Please check if the API is running.');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleGenerateStrategy = async () => {
    if (!userProfile) {
      setError('Please complete your profile first');
      return;
    }
    if (!jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }

    setIsGeneratingStrategy(true);
    setError('');
    setStrategyResult(null);

    try {
      const baseApi = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
      const url = `${baseApi}/generate-strategy`;

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_profile: userProfile,
          job_description: jobDescription,
          provider: provider,
          api_key: localStorage.getItem('apiKey') || '',
          job_id: activeJobId
        })
      });

      if (response.ok) {
        const data = await response.json();
        setStrategyResult(data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to generate strategy.');
      }
    } catch (error) {
      setError('Unable to connect to the server. Please check if the API is running.');
    } finally {
      setIsGeneratingStrategy(false);
    }
  };

  const handleGenerateResume = async () => {
    if (!userProfile) {
      setError('Please complete your profile first');
      return;
    }
    if (!jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }
    if (!userProfile.latexContent) {
      setError('Please upload a LaTeX resume template in your profile first');
      return;
    }

    setIsGeneratingResume(true);
    setError('');
    setResumeResult(null);
    setShowLatexSource(false);

    try {
      const baseApi = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
      const url = `${baseApi}/generate-resume`;

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_profile: userProfile,
          job_description: jobDescription,
          provider: provider,
          api_key: localStorage.getItem('apiKey') || '',
          job_id: activeJobId,
          latex_template: userProfile.latexContent
        })
      });

      if (response.ok) {
        const data = await response.json();
        setResumeResult(data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to generate resume.');
      }
    } catch (error) {
      setError('Unable to connect to the server. Please check if the API is running.');
    } finally {
      setIsGeneratingResume(false);
    }
  };

  const handleDownloadResumePDF = () => {
    if (!resumeResult?.pdf_base64) return;
    const byteCharacters = atob(resumeResult.pdf_base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `resume_${Date.now()}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyLatex = async () => {
    if (!resumeResult?.latex_source) return;
    try {
      await navigator.clipboard.writeText(resumeResult.latex_source);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleMarkApplied = async () => {
    if (!user || !applyJobContext) {
      setError('No linked job from Jobs page to mark as applied.');
      return;
    }
    setMarkAppliedMsg('');
    try {
      await saveApplicationSnapshot(user.uid, applyJobContext.job_id, {
        cover_letter_text: result?.coverLetter || undefined,
        resume_latex: resumeResult?.latex_source || undefined,
        strategy_snapshot: strategyResult || resumeResult?.strategy || undefined,
      });
      setMarkAppliedMsg('Saved application snapshot. Open the apply link to submit on the employer site.');
    } catch (err) {
      console.error(err);
      setError('Failed to save application snapshot.');
    }
  };

  const handleGenerate = async () => {
    if (!userProfile) {
      setError('Please complete your profile first');
      return;
    }
    if (!jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }

    setIsGenerating(true);
    setError('');
    setResult(null);

    try {
      const baseApi = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
      const url = `${baseApi}/generate-cover-letter`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_profile: userProfile,
          job_description: jobDescription,
          provider: provider,
          api_key: localStorage.getItem('apiKey') || '',
          additional_instructions: additionalInstructions
        })
      });

      if (response.ok) {
        const data = await response.json();
        setResult({
          coverLetter: data.cover_letter
        });
        setShowModal(true);
      } else {
        const errorData = await response.json();
        let errorMessage = errorData.detail || 'Failed to generate cover letter.';
        if (errorMessage.toLowerCase().includes('api key')) {
          errorMessage = `Invalid API key. Please add a valid ${provider === 'groq' ? 'Groq' : 'Gemini'} API key in your Account page.`;
        }
        setError(errorMessage);
      }
    } catch (error) {
      setError('Unable to connect to the server. Please check if the API is running.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async (text: string, type: 'resume' | 'coverLetter') => {
    if (text) {
      try {
        await navigator.clipboard.writeText(text);
        setCopied({ ...copied, [type]: true });
        setTimeout(() => setCopied({ ...copied, [type]: false }), 1500);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    }
  };

  const handleDownloadPDF = (text: string, filename: string) => {
    const doc = new jsPDF();
    const lines = doc.splitTextToSize(text, 180);
    doc.text(lines, 15, 20);
    doc.save(filename);
  };

  if (isLoading) {
    return (
      <BackgroundStars>
        <div className="page-header">
          <h1>Apply</h1>
          <p>Loading your profile...</p>
        </div>
      </BackgroundStars>
    );
  }

  return (
    <BackgroundStars>
      <div className="cover-letter-generator-container">
        <div className="page-header" style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1>Apply for a Job</h1>
          <p style={{ marginTop: '0.5rem' }}>Generate tailored resume and cover letter for any job</p>
        </div>

        {!userProfile && (
          <div style={{
            backgroundColor: '#fef3c7',
            border: '2px solid #f59e0b',
            borderRadius: '0.75rem',
            padding: '1.25rem',
            marginBottom: '2rem',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>👤</div>
            <h3 style={{ color: '#b45309', marginBottom: '0.5rem' }}>Profile Required</h3>
            <p style={{ color: '#92400e', marginBottom: '0.75rem' }}>
              Please complete your profile before applying to jobs.
            </p>
            <button
              onClick={() => setCurrentPage('profile')}
              style={{
                backgroundColor: '#f59e0b',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                padding: '0.5rem 1.5rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Complete Profile →
            </button>
          </div>
        )}

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
            <h3 style={{ color: '#dc2626', marginBottom: '0.5rem' }}>API Key Required</h3>
            <p style={{ color: '#991b1b', marginBottom: '0.75rem' }}>
              Add an API key to generate application materials.
            </p>
            <button
              onClick={() => setCurrentPage('account')}
              style={{
                backgroundColor: '#dc2626',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                padding: '0.5rem 1.5rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Add API Key →
            </button>
          </div>
        )}


        <div className="form-section wide-form-section">
          {applyJobContext && (
            <div className="apply-job-banner">
              <strong>{applyJobContext.title}</strong> at {applyJobContext.company}
              {applyJobContext.apply_url && (
                <a
                  href={applyJobContext.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ marginLeft: '1rem' }}
                >
                  Open apply link →
                </a>
              )}
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Job Description</h3>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.85rem', color: '#9ca3af' }}>
              <span>Using:</span>
              <span style={{ 
                color: provider === 'groq' ? '#f59e0b' : provider === 'gemini' ? '#8b5cf6' : '#ef4444',
                fontWeight: 600 
              }}>
                {provider === 'groq' ? 'Groq ⚡' : provider === 'gemini' ? 'Gemini' : 'No API Key'}
              </span>
            </div>
          </div>
          
          <div className="form-group">
            <label htmlFor="jobDescription">Paste the full job description here</label>
            <textarea
              id="jobDescription"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows={10}
              placeholder="Paste the complete job description, including title, company, requirements, responsibilities, etc..."
              className="job-description-textarea"
            />
          </div>

          <div className="form-group" style={{ marginTop: '1.5rem' }}>
            <label htmlFor="additionalInstructions">Cover Letter Instructions (Optional)</label>
            <textarea
              id="additionalInstructions"
              value={additionalInstructions}
              onChange={(e) => setAdditionalInstructions(e.target.value)}
              rows={3}
              placeholder="Add any specific instructions (e.g., 'Emphasize leadership experience', 'Keep resume to 1 page')..."
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

          {error && (
            <div className="error-message" style={{ textAlign: 'center', marginBottom: '2rem' }}>{error}</div>
          )}
          <div className="form-actions" style={{ justifyContent: 'center', marginTop: '1.5rem', gap: '1rem' }}>
            <button 
              onClick={() => setCurrentPage('profile')}
              className="btn-secondary"
              style={{ minWidth: 150 }}
            >
              Edit Profile
            </button>
            <button 
              onClick={handleExtractKeywords}
              className="btn-secondary"
              disabled={isExtracting || !userProfile}
              style={{ minWidth: 180, borderColor: '#8b5cf6', color: '#8b5cf6' }}
            >
              {isExtracting ? 'Extracting...' : 'Extract Keywords'}
            </button>
            <button 
              onClick={handleGenerateStrategy}
              className="btn-secondary"
              disabled={isGeneratingStrategy || !userProfile}
              style={{ minWidth: 180, borderColor: '#10b981', color: '#10b981' }}
            >
              {isGeneratingStrategy ? 'Generating...' : 'Generate Strategy'}
            </button>
            <button 
              onClick={handleGenerate} 
              className="btn-primary"
              disabled={isGenerating || !userProfile}
              style={{ minWidth: 200 }}
            >
              {isGenerating ? 'Generating...' : 'Generate Cover Letter'}
            </button>
            <button 
              onClick={handleGenerateResume}
              className="btn-primary"
              disabled={isGeneratingResume || !userProfile}
              style={{ minWidth: 200, backgroundColor: '#f59e0b' }}
            >
              {isGeneratingResume ? 'Generating Resume...' : 'Generate Resume'}
            </button>
            {applyJobContext && (
              <button
                onClick={handleMarkApplied}
                className="btn-secondary"
                style={{ minWidth: 200, borderColor: '#10b981', color: '#10b981' }}
              >
                Mark as applied
              </button>
            )}
          </div>
          {markAppliedMsg && (
            <p style={{ textAlign: 'center', color: '#10b981', marginTop: '1rem' }}>{markAppliedMsg}</p>
          )}

          {extractionResult && (
            <div className="apply-result-panel apply-result-panel--purple">
              <h3>Keyword Extraction Results</h3>
              {(extractionResult.elapsed_seconds !== undefined || extractionResult.token_usage) && (
                <p className="meta">
                  {extractionResult.elapsed_seconds !== undefined && <span>{extractionResult.elapsed_seconds}s</span>}
                  {extractionResult.token_usage && (
                    <span> &middot; {extractionResult.token_usage.calls} LLM calls &middot; {extractionResult.token_usage.total_tokens} tokens</span>
                  )}
                </p>
              )}
              
              {(() => {
                const matched = extractionResult.keyword_to_experiences;
                const easy = new Set(extractionResult.easy_no_match);
                const dropped = new Set(extractionResult.drop);

                const renderKeyword = (kw: string) => {
                  const isMatched = kw in matched;
                  const isEasy = easy.has(kw);
                  const isDrop = dropped.has(kw);
                  const color = isMatched ? '#047857' : isEasy ? '#b45309' : isDrop ? '#dc2626' : '#6b7280';
                  const bg = isMatched ? 'rgba(16,185,129,0.12)' : isEasy ? 'rgba(245,158,11,0.12)' : isDrop ? 'rgba(239,68,68,0.12)' : 'rgba(156,163,175,0.12)';
                  const label = isMatched ? '✓' : isEasy ? '+' : isDrop ? '✗' : '?';
                  return (
                    <div key={kw} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                      <span style={{ background: bg, color, padding: '0.15rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem', fontWeight: 700, minWidth: '1.5rem', textAlign: 'center' }}>{label}</span>
                      <span style={{ color, fontWeight: 600, fontSize: '0.9rem' }}>{kw}</span>
                      {isMatched && <span style={{ color: '#374151', fontSize: '0.8rem' }}>→ {matched[kw].join(', ')}</span>}
                      {isEasy && <span style={{ color: '#6b7280', fontSize: '0.8rem' }}>— add to skills</span>}
                      {isDrop && <span style={{ color: '#6b7280', fontSize: '0.8rem' }}>— no match</span>}
                    </div>
                  );
                };

                return (
                  <>
                    {extractionResult.must_have?.length > 0 && (
                      <div style={{ marginBottom: '1.25rem' }}>
                        <h4>Must-Have ({extractionResult.must_have.length})</h4>
                        <p className="meta">ATS hard filters — recruiters search for these</p>
                        {extractionResult.must_have.map(renderKeyword)}
                      </div>
                    )}

                    {extractionResult.nice_to_have?.length > 0 && (
                      <div style={{ marginBottom: '1.25rem' }}>
                        <h4>Nice-to-Have ({extractionResult.nice_to_have.length})</h4>
                        <p className="meta">Bonus keywords — weave into bullet points</p>
                        {extractionResult.nice_to_have.map(renderKeyword)}
                      </div>
                    )}

                    <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #e5e7eb' }}>
                      <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem', color: '#6b7280' }}>
                        <span><span style={{ color: '#10b981' }}>✓</span> Matched: {Object.keys(matched).length}</span>
                        <span><span style={{ color: '#b45309' }}>+</span> Easy to add: {extractionResult.easy_no_match.length}</span>
                        <span><span style={{ color: '#ef4444' }}>✗</span> No match: {extractionResult.drop.length}</span>
                      </div>
                    </div>
                  </>
                );
              })()}
            </div>
          )}

          {strategyResult && (
            <div className="apply-result-panel apply-result-panel--green">
              <h3>Resume Strategy</h3>
              {(strategyResult.elapsed_seconds !== undefined || strategyResult.token_usage) && (
                <p className="meta">
                  {strategyResult.elapsed_seconds !== undefined && <span>{strategyResult.elapsed_seconds}s</span>}
                  {strategyResult.token_usage && (
                    <span> &middot; {strategyResult.token_usage.calls} LLM calls &middot; {strategyResult.token_usage.total_tokens} tokens</span>
                  )}
                </p>
              )}

              {strategyResult.title_suggestions.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <h4>Title Suggestions</h4>
                  {strategyResult.title_suggestions.map((t, i) => (
                    <div key={i} className="body-text" style={{ marginBottom: '0.5rem' }}>
                      <span style={{ textDecoration: 'line-through', color: '#9ca3af' }}>{t.original}</span>
                      <span style={{ color: '#b45309', margin: '0 0.5rem', fontWeight: 600 }}>→</span>
                      <span style={{ color: '#047857', fontWeight: 600 }}>{t.suggested}</span>
                      <span style={{ color: '#6b7280', fontSize: '0.8rem', marginLeft: '0.5rem' }}>({t.reason})</span>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ marginBottom: '1.25rem' }}>
                <h4>Skills Section</h4>
                <div className="body-text">
                  <div style={{ marginBottom: '0.5rem' }}>
                    <span style={{ color: '#10b981', fontWeight: 600 }}>Front-load: </span>
                    {strategyResult.skills_strategy.front_load.join(', ') || 'None'}
                  </div>
                  <div style={{ marginBottom: '0.5rem' }}>
                    <span style={{ color: '#b45309', fontWeight: 600 }}>Add: </span>
                    {strategyResult.skills_strategy.add.join(', ') || 'None'}
                  </div>
                  <div style={{ marginBottom: '0.5rem' }}>
                    <span style={{ color: '#3b82f6', fontWeight: 600 }}>Keep: </span>
                    {strategyResult.skills_strategy.keep.join(', ') || 'None'}
                  </div>
                  <div>
                    <span style={{ color: '#6b7280', fontWeight: 600 }}>Deprioritize: </span>
                    {strategyResult.skills_strategy.deprioritize.join(', ') || 'None'}
                  </div>
                </div>
              </div>

              <div>
                <h4>Selected Experiences</h4>
                {strategyResult.experiences.filter(e => e.should_include).map((exp, i) => (
                  <div key={i} style={{ marginBottom: '1rem', padding: '0.75rem', background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e5e7eb' }}>
                    <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: '0.25rem' }}>{exp.title}</div>
                    <div className="meta" style={{ marginBottom: '0.5rem' }}>
                      Keywords: {exp.keywords_covered.join(', ')}
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.85rem', color: '#374151' }}>
                      {exp.dotjots.map((dot, j) => (
                        <li key={j} style={{ marginBottom: '0.25rem' }}>{dot}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}

          {resumeResult && (
            <div className="apply-result-panel apply-result-panel--amber">
              <h3>Generated Resume</h3>
              {(resumeResult.elapsed_seconds !== undefined || resumeResult.token_usage) && (
                <p className="meta">
                  {resumeResult.elapsed_seconds !== undefined && <span>{resumeResult.elapsed_seconds}s</span>}
                  {resumeResult.token_usage && (
                    <span> &middot; {resumeResult.token_usage.calls} LLM calls &middot; {resumeResult.token_usage.total_tokens} tokens</span>
                  )}
                </p>
              )}

              <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                <button
                  onClick={handleDownloadResumePDF}
                  className="btn-primary"
                  style={{ backgroundColor: '#f59e0b', minWidth: 180 }}
                >
                  Download PDF
                </button>
                <button
                  onClick={() => setShowLatexSource(!showLatexSource)}
                  className="btn-secondary"
                  style={{ minWidth: 180 }}
                >
                  {showLatexSource ? 'Hide LaTeX' : 'View LaTeX Source'}
                </button>
              </div>

              {showLatexSource && (
                <div style={{ position: 'relative' }}>
                  <button
                    onClick={handleCopyLatex}
                    style={{
                      position: 'absolute',
                      top: '0.5rem',
                      right: '0.5rem',
                      padding: '0.25rem 0.75rem',
                      fontSize: '0.8rem',
                      background: '#374151',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.25rem',
                      cursor: 'pointer'
                    }}
                  >
                    Copy
                  </button>
                  <pre style={{
                    background: '#1f2937',
                    padding: '1rem',
                    borderRadius: '0.5rem',
                    fontSize: '0.8rem',
                    overflow: 'auto',
                    maxHeight: '300px',
                    color: '#d1d5db',
                    margin: 0
                  }}>
                    <code>{resumeResult.latex_source}</code>
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {showModal && result && (
        <div className="modal-overlay">
          <div className="modal-content result-column" style={{ maxWidth: '800px', width: '90%' }}>
            <div className="modal-header">
              <h2>Your Cover Letter</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>

            <div
              className="modal-body"
              style={{
                maxHeight: '50vh',
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
              {result.coverLetter}
            </div>

            <div className="modal-footer">
              <button 
                className="btn-secondary" 
                onClick={() => handleCopy(result.coverLetter!, 'coverLetter')}
                style={{ marginRight: '0.5rem' }}
              >
                {copied.coverLetter ? 'Copied!' : 'Copy'}
              </button>
              <button 
                className="btn-secondary" 
                onClick={() => handleDownloadPDF(result.coverLetter!, 'cover_letter.pdf')}
                style={{ marginRight: '0.5rem' }}
              >
                Download PDF
              </button>
              <button className="btn-primary" onClick={() => setShowModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </BackgroundStars>
  );
};

export default ApplyPage;
