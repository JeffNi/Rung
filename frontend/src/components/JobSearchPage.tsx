import React, { useState, useEffect } from 'react';
import { auth, db } from '../firebase';
import { doc, getDoc, getDocFromServer } from 'firebase/firestore';
import type { User } from 'firebase/auth';
import type { UserProfile } from './ProfileModal';
import BackgroundStars from './BackgroundStars';
import {
  getSeenJobIds,
  upsertDiscoveredJobs,
  stashApplyJobContext,
  type RawJobFromApi,
} from '../lib/jobPostings';
import { cleanJobDescription } from '../lib/cleanDescription';
import { isProfileUpdated, clearProfileUpdated } from '../lib/profileRefresh';
import '../styles/components/JobSearchPage.css';

interface JobListing {
  job_id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  description_full?: string;
  salary: string | null;
  apply_url: string | null;
  posted_date: string | null;
  relevance_score: number;
  tier?: string;
  skill_score?: number;
  experience_score?: number;
  value_score?: number;
  years_required?: number | null;
  user_years?: number | null;
  search_term?: string | null;
}

interface SearchResult {
  jobs: JobListing[];
  query: string;
  total_returned: number;
  batch_size?: number;
  total_from_api?: number;
  total_skipped_seen?: number;
  api_calls?: number;
  has_more?: boolean;
}

type DatePostedFilter = 'week' | 'month' | 'all';

const JobSearchPage: React.FC<{ setCurrentPage: (page: string) => void }> = ({ setCurrentPage }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState('');
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [searchMeta, setSearchMeta] = useState<SearchResult | null>(null);
  const [datePosted, setDatePosted] = useState<DatePostedFilter>('week');
  const [seenCount, setSeenCount] = useState(0);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((u) => setUser(u));
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    if (user) {
      loadProfile(user.uid);
      refreshSeenCount(user.uid);
    }
  }, [user]);

  const loadProfile = async (userId: string) => {
    setIsLoading(true);
    try {
      const profileRef = doc(db, 'userProfiles', userId);
      const profileDoc = isProfileUpdated()
        ? await getDocFromServer(profileRef)
        : await getDoc(profileRef);
      if (profileDoc.exists()) {
        setUserProfile(profileDoc.data() as UserProfile);
        clearProfileUpdated();
      }
    } catch (err) {
      console.error('Error loading profile:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshSeenCount = async (userId: string) => {
    try {
      const ids = await getSeenJobIds(userId);
      setSeenCount(ids.size);
    } catch (err) {
      console.warn('Could not load seen job count:', err);
    }
  };

  const hasSearchTitles = Boolean(
    userProfile?.searchTitles?.some((t) => (t || '').trim()),
  );

  const runSearch = async (reset: boolean) => {
    if (!userProfile || !user) return;

    if (!hasSearchTitles) {
      setError('Add at least one job search title on your Profile (e.g. ML Engineer).');
      return;
    }

    setIsSearching(true);
    setError('');

    if (reset) {
      setJobs([]);
      setSearchMeta(null);
    }

    try {
      const seenIds = await getSeenJobIds(user.uid);
      const baseApi = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

      const response = await fetch(`${baseApi}/search-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_profile: userProfile,
          user_id: user.uid,
          location: '',
          date_posted: datePosted,
          reset,
          seen_job_ids: Array.from(seenIds),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to search jobs.');
        return;
      }

      const data: SearchResult = await response.json();
      const mergedJobs = reset ? data.jobs : [...jobs, ...data.jobs];
      setJobs(mergedJobs);
      setSearchMeta({
        ...data,
        total_returned: mergedJobs.length,
      });

      const archiveJobs: RawJobFromApi[] = data.jobs.map((j) => ({
        job_id: j.job_id,
        title: j.title,
        company: j.company,
        location: j.location,
        description: j.description,
        description_full: j.description_full || j.description,
        salary: j.salary,
        apply_url: j.apply_url,
        posted_date: j.posted_date,
        search_term: j.search_term,
        tier: j.tier,
        relevance_score: j.relevance_score,
        skill_score: j.skill_score,
        experience_score: j.experience_score,
        value_score: j.value_score,
        years_required: j.years_required,
        user_years: j.user_years,
      }));
      await upsertDiscoveredJobs(user.uid, archiveJobs);
      await refreshSeenCount(user.uid);
    } catch (err) {
      console.error(err);
      setError('Unable to connect to the server. Please check if the API is running.');
    } finally {
      setIsSearching(false);
    }
  };

  const handlePrepareApplication = (job: JobListing) => {
    stashApplyJobContext({
      job_id: job.job_id,
      title: job.title,
      company: job.company,
      description: cleanJobDescription(job.description_full || job.description),
      apply_url: job.apply_url,
    });
    setCurrentPage('apply');
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Recently';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

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

  if (isLoading) {
    return (
      <BackgroundStars>
        <div className="loading-container">
          <div className="loading">Loading profile...</div>
        </div>
      </BackgroundStars>
    );
  }

  return (
    <BackgroundStars>
      <div className="job-search-layout">
        <div className="page-header">
          <h1>Find Jobs</h1>
          <p>Search by your job titles and profile keywords — ~100 new listings per batch</p>
        </div>

        {!userProfile ? (
          <div className="form-section">
            <div className="placeholder">
              <p>Please complete your profile first to search for jobs.</p>
              <button className="btn-primary" onClick={() => setCurrentPage('profile')}>
                Go to Profile
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="form-section search-controls">
              <div className="search-info">
                <p><strong>Search titles:</strong></p>
                {hasSearchTitles ? (
                  <ul>
                    {userProfile.searchTitles!.filter((t) => t.trim()).map((t) => (
                      <li key={t}><em>{t}</em></li>
                    ))}
                  </ul>
                ) : (
                  <p className="search-warning">No search titles yet — add them on Profile.</p>
                )}
                {userProfile.llmSearchTerms && userProfile.llmSearchTerms.length > 0 && (
                  <p className="search-hint">
                    + {userProfile.llmSearchTerms.length} hidden AI-suggested terms on last save
                  </p>
                )}
                <p className="search-hint">{seenCount} jobs in your archive — <button type="button" className="link-btn" onClick={() => setCurrentPage('savedjobs')}>view saved jobs</button></p>
              </div>

              <div className="search-filters">
                <label htmlFor="date-posted">Posted within</label>
                <select
                  id="date-posted"
                  value={datePosted}
                  onChange={(e) => setDatePosted(e.target.value as DatePostedFilter)}
                  disabled={isSearching}
                >
                  <option value="week">Past week</option>
                  <option value="month">Past month</option>
                  <option value="all">All time</option>
                </select>
              </div>

              <div className="form-actions">
                <button
                  className="btn-primary"
                  onClick={() => runSearch(true)}
                  disabled={isSearching || !hasSearchTitles}
                >
                  {isSearching && jobs.length === 0 ? 'Searching...' : 'Find Jobs'}
                </button>
              </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            {searchMeta && (
              <div className="results-section">
                <div className="results-header">
                  <h3>Searching: {searchMeta.query}</h3>
                  <span className="results-count">
                    Showing {jobs.length} job{jobs.length === 1 ? '' : 's'}
                  </span>
                </div>

                {searchMeta.api_calls != null && (
                  <div className="search-stats">
                    <span>API calls this batch: {searchMeta.api_calls}</span>
                    {searchMeta.total_skipped_seen != null && (
                      <span>Skipped (already archived): {searchMeta.total_skipped_seen}</span>
                    )}
                    {searchMeta.total_from_api != null && (
                      <span>Raw listings scanned: {searchMeta.total_from_api}</span>
                    )}
                  </div>
                )}

                {jobs.length === 0 ? (
                  <div className="placeholder">
                    <p>
                      No new jobs found. Try Load More, widen the date filter, or add more search titles.
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="job-cards">
                      {jobs.map((job) => (
                        <div key={job.job_id} className="job-card">
                          <div className="job-card-header">
                            <h4 className="job-title">{job.title}</h4>
                            <div className="job-score-badges">
                              <span className={`tier-badge tier-${job.tier || 'D'}`}>
                                {job.tier || 'D'}
                              </span>
                              <span className="relevance-badge" title={tierLabel(job.tier)}>
                                {job.relevance_score}% match
                              </span>
                            </div>
                          </div>
                          <div className="job-meta">
                            <span className="job-company">{job.company}</span>
                            <span className="job-location">{job.location}</span>
                            <span className="job-date">{formatDate(job.posted_date)}</span>
                          </div>
                          {(job.skill_score != null || job.experience_score != null) && (
                            <div className="score-breakdown">
                              <span>Skills {job.skill_score ?? '—'}%</span>
                              <span>Experience {job.experience_score ?? '—'}%</span>
                              <span>Values {job.value_score ?? '—'}%</span>
                              {job.years_required != null && (
                                <span>
                                  Req {job.years_required}+ yrs
                                  {job.user_years != null ? ` · You ~${job.user_years} yrs` : ''}
                                </span>
                              )}
                            </div>
                          )}
                          <p className="job-description">{cleanJobDescription(job.description)}</p>
                          <div className="job-actions">
                            <button
                              type="button"
                              className="btn-primary btn-small"
                              onClick={() => handlePrepareApplication(job)}
                            >
                              Prepare application
                            </button>
                            {job.apply_url ? (
                              <a
                                href={job.apply_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn-secondary btn-small"
                              >
                                Open apply link
                              </a>
                            ) : (
                              <span className="no-link">No apply link</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {searchMeta.has_more && (
                      <div className="load-more-actions">
                        <button
                          className="btn-secondary"
                          onClick={() => runSearch(false)}
                          disabled={isSearching}
                        >
                          {isSearching ? 'Loading...' : 'Load More'}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </BackgroundStars>
  );
};

export default JobSearchPage;
