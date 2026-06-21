import React, { useState, useEffect, useMemo } from 'react';
import { auth, db } from '../firebase';
import { doc, getDocFromServer } from 'firebase/firestore';
import type { User } from 'firebase/auth';
import type { UserProfile } from './ProfileModal';
import BackgroundStars from './BackgroundStars';
import {
  getAllJobPostings,
  clearAllJobPostings,
  stashApplyJobContext,
  mergeJobScores,
  type JobPostingDoc,
  type JobScoreResult,
  type JobStatus,
} from '../lib/jobPostings';
import { cleanJobDescription } from '../lib/cleanDescription';
import { clearProfileUpdated, isProfileUpdated } from '../lib/profileRefresh';
import '../styles/components/StoredJobsPage.css';

type StatusFilter = 'all' | JobStatus;

type SortOption =
  | 'match-desc'
  | 'match-asc'
  | 'tier'
  | 'date-desc'
  | 'date-asc'
  | 'title'
  | 'company';

const TIER_RANK: Record<string, number> = { S: 0, A: 1, B: 2, C: 3, D: 4 };

function sortJobs(list: JobPostingDoc[], sortBy: SortOption): JobPostingDoc[] {
  const copy = [...list];
  switch (sortBy) {
    case 'match-desc':
      return copy.sort((a, b) => (b.relevance_score ?? -1) - (a.relevance_score ?? -1));
    case 'match-asc':
      return copy.sort((a, b) => (a.relevance_score ?? -1) - (b.relevance_score ?? -1));
    case 'tier':
      return copy.sort((a, b) => {
        const ta = TIER_RANK[a.tier ?? ''] ?? 9;
        const tb = TIER_RANK[b.tier ?? ''] ?? 9;
        if (ta !== tb) return ta - tb;
        return (b.relevance_score ?? 0) - (a.relevance_score ?? 0);
      });
    case 'date-desc':
      return copy.sort((a, b) => (b.posted_date || '').localeCompare(a.posted_date || ''));
    case 'date-asc':
      return copy.sort((a, b) => (a.posted_date || '').localeCompare(b.posted_date || ''));
    case 'title':
      return copy.sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: 'base' }));
    case 'company':
      return copy.sort((a, b) => a.company.localeCompare(b.company, undefined, { sensitivity: 'base' }));
    default:
      return copy;
  }
}

const STATUS_LABELS: Record<JobStatus, string> = {
  discovered: 'Discovered',
  applied: 'Applied',
  interviewing: 'Interviewing',
  rejected: 'Rejected',
  offer: 'Offer',
  ghosted: 'Ghosted',
};

const StoredJobsPage: React.FC<{ setCurrentPage: (page: string) => void }> = ({ setCurrentPage }) => {
  const [user, setUser] = useState<User | null>(null);
  const [jobs, setJobs] = useState<JobPostingDoc[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isClearing, setIsClearing] = useState(false);
  const [clearMessage, setClearMessage] = useState('');
  const [isScoring, setIsScoring] = useState(false);
  const [sortBy, setSortBy] = useState<SortOption>('match-desc');
  const [scoreMeta, setScoreMeta] = useState<{
    user_months?: number;
    user_years?: number;
    experience_calc_version?: number;
  } | null>(null);
  const [scoreError, setScoreError] = useState('');

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((u) => setUser(u));
    return () => unsubscribe();
  }, []);

  const applyScoresToJobs = (
    list: JobPostingDoc[],
    scores: JobScoreResult[],
  ): JobPostingDoc[] => {
    const scoreMap = new Map(scores.map((s) => [s.job_id, s]));
    const merged = list.map((job) => {
      const s = scoreMap.get(job.job_id);
      if (!s) return job;
      return {
        ...job,
        tier: s.tier,
        relevance_score: s.relevance_score,
        skill_score: s.skill_score,
        experience_score: s.experience_score,
        value_score: s.value_score,
        years_required: s.years_required,
        user_years: s.user_years,
      };
    });
    return merged;
  };

  const rescoreJobs = async (userId: string, list: JobPostingDoc[]) => {
    if (list.length === 0) return list;
    const profileDoc = await getDocFromServer(doc(db, 'userProfiles', userId));
    if (!profileDoc.exists()) return list;

    const profile = profileDoc.data() as UserProfile;
    const baseApi = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

    setIsScoring(true);
    setScoreMeta(null);
    try {
      const response = await fetch(`${baseApi}/score-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_profile: profile,
          jobs: list.map((j) => ({
            job_id: j.job_id,
            title: j.title,
            description: j.description,
          })),
        }),
      });
      if (!response.ok) {
        const errText = await response.text();
        console.warn('Score jobs failed:', errText);
        setScoreError('Could not refresh scores — is the backend running?');
        return list;
      }
      const data = await response.json();
      const scores = (data.scores || []) as JobScoreResult[];
      setScoreMeta({
        user_months: data.user_months,
        user_years: scores[0]?.user_years,
        experience_calc_version: data.experience_calc_version,
      });
      setScoreError('');
      await mergeJobScores(userId, scores);
      clearProfileUpdated();
      return applyScoresToJobs(list, scores);
    } catch (err) {
      console.warn('Could not refresh match scores:', err);
      setScoreError('Could not reach scoring API. Restart the backend and click Refresh scores.');
      return list;
    } finally {
      setIsScoring(false);
    }
  };

  const loadJobs = async (userId: string) => {
    setIsLoading(true);
    setError('');
    try {
      const list = await getAllJobPostings(userId);
      const scored = await rescoreJobs(userId, list);
      setJobs(scored);
      setSelectedId(scored.length > 0 ? scored[0].job_id : null);
    } catch (err) {
      console.error(err);
      setError('Could not load saved jobs. Check Firestore rules for users/{uid}/jobPostings.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadJobs(user.uid);
    } else {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!user) return;
    const onFocus = () => {
      if (isProfileUpdated()) {
        loadJobs(user.uid);
      }
    };
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [user]);

  const filteredJobs = useMemo(() => jobs.filter((job) => {
    if (statusFilter !== 'all' && job.status !== statusFilter) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      job.title.toLowerCase().includes(q)
      || job.company.toLowerCase().includes(q)
      || job.location.toLowerCase().includes(q)
    );
  }), [jobs, statusFilter, searchQuery]);

  const sortedFilteredJobs = useMemo(
    () => sortJobs(filteredJobs, sortBy),
    [filteredJobs, sortBy],
  );

  const selectedJob = sortedFilteredJobs.find((j) => j.job_id === selectedId)
    ?? filteredJobs.find((j) => j.job_id === selectedId)
    ?? jobs.find((j) => j.job_id === selectedId);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Unknown date';
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return dateStr;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const hasScore = (job: JobPostingDoc) =>
    job.relevance_score != null && job.tier != null;

  const tierLabel = (tier?: string) => {
    switch (tier) {
      case 'S':
        return 'Tier S — top match';
      case 'A':
        return 'Tier A — strong fit';
      case 'B':
        return 'Tier B — good match';
      case 'C':
        return 'Tier C — stretch / practice';
      default:
        return 'Tier D — weak match';
    }
  };

  const handleClearAll = async () => {
    if (!user || jobs.length === 0) return;
    const confirmed = window.confirm(
      `Delete all ${jobs.length} saved jobs?\n\nYou can find them again with Find Jobs on the Jobs page. Applied materials saved here will be removed too.`,
    );
    if (!confirmed) return;

    setIsClearing(true);
    setError('');
    setClearMessage('');
    try {
      const deleted = await clearAllJobPostings(user.uid);
      setJobs([]);
      setSelectedId(null);
      setClearMessage(`Removed ${deleted} saved job${deleted === 1 ? '' : 's'}. Use Find Jobs to discover them again.`);
    } catch (err) {
      console.error(err);
      setError('Failed to clear saved jobs. Check Firestore delete permissions.');
    } finally {
      setIsClearing(false);
    }
  };

  const handlePrepare = (job: JobPostingDoc) => {
    stashApplyJobContext({
      job_id: job.job_id,
      title: job.title,
      company: job.company,
      description: cleanJobDescription(job.description),
      apply_url: job.apply_url,
    });
    setCurrentPage('apply');
  };

  if (!user) {
    return (
      <BackgroundStars>
        <div className="stored-jobs-layout">
          <div className="form-section placeholder-box">
            <p>Log in to view your saved jobs.</p>
            <button className="btn-primary" onClick={() => setCurrentPage('login')}>Log in</button>
          </div>
        </div>
      </BackgroundStars>
    );
  }

  return (
    <BackgroundStars>
      <div className="stored-jobs-layout">
        <div className="page-header">
          <h1>Saved Jobs</h1>
          <p>Every job we&apos;ve returned to you — full postings for interview prep</p>
        </div>

        <div className="stored-jobs-toolbar form-section">
          <input
            type="search"
            className="stored-jobs-search"
            placeholder="Search title, company, location…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <div className="status-filters">
            {(['all', 'discovered', 'applied', 'interviewing', 'rejected', 'offer'] as StatusFilter[]).map((s) => (
              <button
                key={s}
                type="button"
                className={`status-filter-btn ${statusFilter === s ? 'active' : ''}`}
                onClick={() => setStatusFilter(s)}
              >
                {s === 'all' ? 'All' : STATUS_LABELS[s as JobStatus]}
              </button>
            ))}
          </div>
          <label className="stored-jobs-sort">
            <span className="stored-jobs-sort-label">Sort</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              aria-label="Sort saved jobs"
            >
              <option value="match-desc">Match % (high → low)</option>
              <option value="match-asc">Match % (low → high)</option>
              <option value="tier">Tier (S → D)</option>
              <option value="date-desc">Date posted (newest)</option>
              <option value="date-asc">Date posted (oldest)</option>
              <option value="title">Title (A → Z)</option>
              <option value="company">Company (A → Z)</option>
            </select>
          </label>
          <button type="button" className="btn-secondary btn-small" onClick={() => loadJobs(user.uid)}>
            Refresh scores
          </button>
          {jobs.length > 0 && (
            <button
              type="button"
              className="btn-clear-all btn-small"
              onClick={handleClearAll}
              disabled={isClearing}
            >
              {isClearing ? 'Clearing…' : 'Clear all saved'}
            </button>
          )}
        </div>

        {clearMessage && <p className="clear-message">{clearMessage}</p>}
        {scoreMeta?.user_months != null && (
          <p className="score-meta">
            Your experience: ~{scoreMeta.user_years ?? Math.round((scoreMeta.user_months / 12) * 10) / 10} yrs
            ({scoreMeta.user_months} months counted)
            {scoreMeta.experience_calc_version != null && scoreMeta.experience_calc_version < 3
              ? ' — restart backend for latest calc'
              : ''}
          </p>
        )}
        {scoreError && <p className="score-error">{scoreError}</p>}

        {error && <div className="error-message">{error}</div>}

        {isLoading ? (
          <div className="loading-container">
            <div className="loading">
              {isScoring ? 'Loading saved jobs and computing match scores…' : 'Loading saved jobs…'}
            </div>
          </div>
        ) : jobs.length === 0 ? (
          <div className="form-section placeholder-box">
            <p>No saved jobs yet. Use <strong>Find Jobs</strong> to build your archive.</p>
            <button className="btn-primary" onClick={() => setCurrentPage('jobsearch')}>Go to Jobs</button>
          </div>
        ) : sortedFilteredJobs.length === 0 ? (
          <div className="form-section placeholder-box">
            <p>No jobs match this filter.</p>
          </div>
        ) : (
          <div className="stored-jobs-split">
            <div className="stored-jobs-list">
              <p className="list-count">{sortedFilteredJobs.length} job{sortedFilteredJobs.length === 1 ? '' : 's'}</p>
              {sortedFilteredJobs.map((job) => (
                <button
                  key={job.job_id}
                  type="button"
                  className={`stored-job-row ${selectedId === job.job_id ? 'selected' : ''}`}
                  onClick={() => setSelectedId(job.job_id)}
                >
                  <div className="stored-job-row-top">
                    <div className="stored-job-row-title">{job.title}</div>
                    {hasScore(job) && (
                      <div className="job-score-badges">
                        <span className={`tier-badge tier-${job.tier || 'D'}`}>
                          {job.tier || 'D'}
                        </span>
                        {job.relevance_score != null && (
                          <span className="relevance-badge">{job.relevance_score}%</span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="stored-job-row-meta">
                    {job.company} · {job.location}
                  </div>
                  <span className={`status-badge status-${job.status}`}>
                    {STATUS_LABELS[job.status] || job.status}
                  </span>
                </button>
              ))}
            </div>

            {selectedJob && (
              <div className="stored-job-detail form-section">
                <div className="detail-header">
                  <h2>{selectedJob.title}</h2>
                  <div className="detail-header-badges">
                    {hasScore(selectedJob) && (
                      <div className="job-score-badges">
                        <span
                          className={`tier-badge tier-${selectedJob.tier || 'D'}`}
                          title={tierLabel(selectedJob.tier)}
                        >
                          {selectedJob.tier || 'D'}
                        </span>
                        {selectedJob.relevance_score != null && (
                          <span className="relevance-badge" title={tierLabel(selectedJob.tier)}>
                            {selectedJob.relevance_score}% match
                          </span>
                        )}
                      </div>
                    )}
                    <span className={`status-badge status-${selectedJob.status}`}>
                      {STATUS_LABELS[selectedJob.status] || selectedJob.status}
                    </span>
                  </div>
                </div>
                {hasScore(selectedJob) && (
                  <div className="score-breakdown">
                    <span>Skills {selectedJob.skill_score ?? '—'}%</span>
                    <span>Experience {selectedJob.experience_score ?? '—'}%</span>
                    <span>Values {selectedJob.value_score ?? '—'}%</span>
                    {selectedJob.years_required != null && (
                      <span>
                        Req {selectedJob.years_required}+ yrs
                        {selectedJob.user_years != null ? ` · You ~${selectedJob.user_years} yrs` : ''}
                      </span>
                    )}
                  </div>
                )}
                <div className="detail-meta">
                  <span>{selectedJob.company}</span>
                  <span>{selectedJob.location}</span>
                  <span>Posted {formatDate(selectedJob.posted_date)}</span>
                  {selectedJob.salary && <span>{selectedJob.salary}</span>}
                  {selectedJob.search_term && <span>Found via: {selectedJob.search_term}</span>}
                </div>

                <div className="detail-description">{cleanJobDescription(selectedJob.description)}</div>

                {selectedJob.application?.cover_letter_text && (
                  <div className="detail-application">
                    <h3>Cover letter (saved)</h3>
                    <pre>{selectedJob.application.cover_letter_text}</pre>
                  </div>
                )}

                <div className="detail-actions">
                  <button type="button" className="btn-primary btn-small" onClick={() => handlePrepare(selectedJob)}>
                    Prepare application
                  </button>
                  {selectedJob.apply_url && (
                    <a
                      href={selectedJob.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-secondary btn-small"
                    >
                      Open apply link
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </BackgroundStars>
  );
};

export default StoredJobsPage;
