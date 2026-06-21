import { db } from '../firebase';
import {
  collection,
  doc,
  getDocs,
  setDoc,
  serverTimestamp,
  writeBatch,
} from 'firebase/firestore';

export type JobStatus = 'discovered' | 'applied' | 'interviewing' | 'rejected' | 'offer' | 'ghosted';

export interface JobPostingDoc {
  job_id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  salary: string | null;
  apply_url: string | null;
  posted_date: string | null;
  discovered_at?: unknown;
  search_term?: string | null;
  tier?: string;
  relevance_score?: number;
  skill_score?: number;
  experience_score?: number;
  value_score?: number;
  years_required?: number | null;
  user_years?: number | null;
  status: JobStatus;
  application?: {
    cover_letter_text?: string;
    resume_latex?: string;
    strategy_snapshot?: unknown;
    applied_at?: unknown;
  };
  outcome?: JobStatus;
  notes?: string;
}

export interface RawJobFromApi {
  job_id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  description_full: string;
  salary: string | null;
  apply_url: string | null;
  posted_date: string | null;
  search_term?: string | null;
  tier?: string;
  relevance_score?: number;
  skill_score?: number;
  experience_score?: number;
  value_score?: number;
  years_required?: number | null;
  user_years?: number | null;
}

export interface JobScoreResult {
  job_id: string;
  relevance_score: number;
  tier: string;
  skill_score: number;
  experience_score: number;
  value_score: number;
  years_required?: number | null;
  user_years?: number;
}

function jobPostingsCol(userId: string) {
  return collection(db, 'users', userId, 'jobPostings');
}

export async function mergeJobScores(
  userId: string,
  scores: JobScoreResult[],
): Promise<void> {
  if (scores.length === 0) return;
  const col = jobPostingsCol(userId);
  for (let i = 0; i < scores.length; i += 500) {
    const batch = writeBatch(db);
    const chunk = scores.slice(i, i + 500);
    chunk.forEach((s) => {
      batch.set(
        doc(col, s.job_id),
        {
          tier: s.tier,
          relevance_score: s.relevance_score,
          skill_score: s.skill_score,
          experience_score: s.experience_score,
          value_score: s.value_score,
          years_required: s.years_required ?? null,
          user_years: s.user_years ?? null,
        },
        { merge: true },
      );
    });
    await batch.commit();
  }
}

export async function getAllJobPostings(userId: string): Promise<JobPostingDoc[]> {
  const snap = await getDocs(jobPostingsCol(userId));
  const jobs: JobPostingDoc[] = [];
  snap.forEach((d) => {
    const data = d.data() as JobPostingDoc;
    jobs.push({ ...data, job_id: data.job_id || d.id });
  });
  jobs.sort((a, b) => {
    const aDate = a.posted_date || '';
    const bDate = b.posted_date || '';
    return bDate.localeCompare(aDate);
  });
  return jobs;
}

export async function getSeenJobIds(userId: string): Promise<Set<string>> {
  const snap = await getDocs(jobPostingsCol(userId));
  const ids = new Set<string>();
  snap.forEach((d) => ids.add(d.id));
  return ids;
}

/** Delete all saved job postings so they can appear again in search. */
export async function clearAllJobPostings(userId: string): Promise<number> {
  const snap = await getDocs(jobPostingsCol(userId));
  if (snap.empty) return 0;

  const docs = snap.docs;
  let deleted = 0;
  for (let i = 0; i < docs.length; i += 500) {
    const batch = writeBatch(db);
    const chunk = docs.slice(i, i + 500);
    chunk.forEach((d) => batch.delete(d.ref));
    await batch.commit();
    deleted += chunk.length;
  }
  return deleted;
}

export async function upsertDiscoveredJobs(
  userId: string,
  jobs: RawJobFromApi[],
): Promise<void> {
  const col = jobPostingsCol(userId);
  for (const job of jobs) {
    if (!job.job_id) continue;
    const ref = doc(col, job.job_id);
    await setDoc(
      ref,
      {
        job_id: job.job_id,
        title: job.title,
        company: job.company,
        location: job.location,
        description: job.description_full || job.description,
        salary: job.salary,
        apply_url: job.apply_url,
        posted_date: job.posted_date,
        discovered_at: serverTimestamp(),
        search_term: job.search_term || null,
        tier: job.tier || null,
        relevance_score: job.relevance_score ?? null,
        skill_score: job.skill_score ?? null,
        experience_score: job.experience_score ?? null,
        value_score: job.value_score ?? null,
        years_required: job.years_required ?? null,
        user_years: job.user_years ?? null,
        status: 'discovered',
      },
      { merge: true },
    );
  }
}

export async function saveApplicationSnapshot(
  userId: string,
  jobId: string,
  application: JobPostingDoc['application'],
): Promise<void> {
  const ref = doc(jobPostingsCol(userId), jobId);
  await setDoc(
    ref,
    {
      status: 'applied',
      application: {
        ...application,
        applied_at: serverTimestamp(),
      },
    },
    { merge: true },
  );
}

export const APPLY_JOB_STORAGE_KEY = 'rung_apply_job';

export interface ApplyJobContext {
  job_id: string;
  title: string;
  company: string;
  description: string;
  apply_url: string | null;
}

export function stashApplyJobContext(job: ApplyJobContext): void {
  sessionStorage.setItem(APPLY_JOB_STORAGE_KEY, JSON.stringify(job));
}

export function readApplyJobContext(): ApplyJobContext | null {
  const raw = sessionStorage.getItem(APPLY_JOB_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ApplyJobContext;
  } catch {
    return null;
  }
}

export function clearApplyJobContext(): void {
  sessionStorage.removeItem(APPLY_JOB_STORAGE_KEY);
}
