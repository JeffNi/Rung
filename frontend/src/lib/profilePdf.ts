import { jsPDF } from 'jspdf';
import type { UserProfile, ExperienceEntry } from '../components/ProfileModal';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

type ExperienceRecord = Record<string, ExperienceEntry | string[]>;

function safeFilename(name: string, suffix: string) {
  const base = name.trim().replace(/\s+/g, '_').replace(/[^\w.-]/g, '') || 'profile';
  return `${base}_${suffix}.pdf`;
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function getEntryBullets(entry: ExperienceEntry | string[] | unknown): string[] {
  if (Array.isArray(entry)) {
    return entry.filter((b) => typeof b === 'string' && b.trim());
  }
  if (entry && typeof entry === 'object') {
    const e = entry as ExperienceEntry;
    const bullets = [...(e.bullets || []).filter((b) => b?.trim())];
    const aiBullets = e.ai_bullets || {};
    for (const jobBullets of Object.values(aiBullets)) {
      for (const bullet of jobBullets) {
        if (bullet?.trim()) bullets.push(bullet);
      }
    }
    return bullets;
  }
  return [];
}

function getEntryMeta(
  entry: ExperienceEntry | string[] | unknown,
  fallbackTitle = ''
): Pick<ExperienceEntry, 'title' | 'company' | 'location' | 'startDate' | 'endDate' | 'context'> {
  if (Array.isArray(entry)) {
    return {
      title: fallbackTitle,
      company: '',
      location: '',
      startDate: '',
      endDate: '',
      context: '',
    };
  }
  if (entry && typeof entry === 'object') {
    const e = entry as ExperienceEntry;
    return {
      title: e.title || fallbackTitle,
      company: e.company || '',
      location: e.location || '',
      startDate: e.startDate || '',
      endDate: e.endDate || '',
      context: e.context || '',
    };
  }
  return {
    title: fallbackTitle,
    company: '',
    location: '',
    startDate: '',
    endDate: '',
    context: '',
  };
}

export async function compileLatexToBlob(latexContent: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/compile-latex`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: latexContent }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err.slice(0, 300) || 'LaTeX compile failed');
  }
  return res.blob();
}

export async function downloadLatexResumePdf(latexContent: string, displayName?: string): Promise<void> {
  const blob = await compileLatexToBlob(latexContent);
  triggerBlobDownload(blob, safeFilename(displayName || 'resume', 'resume'));
}

export async function previewLatexResumePdf(latexContent: string): Promise<void> {
  const blob = await compileLatexToBlob(latexContent);
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
}

export function downloadProfileSummaryPdf(profile: UserProfile): void {
  const doc = new jsPDF();
  const margin = 15;
  const lineWidth = 180;
  const pageHeight = doc.internal.pageSize.getHeight();
  let y = 20;

  const ensureSpace = (needed: number) => {
    if (y + needed > pageHeight - 15) {
      doc.addPage();
      y = 20;
    }
  };

  const writeLines = (
    text: string,
    fontSize = 11,
    style: 'normal' | 'bold' = 'normal',
    indent = 0
  ) => {
    doc.setFontSize(fontSize);
    doc.setFont('helvetica', style);
    const lines = doc.splitTextToSize(text, lineWidth - indent);
    const lineHeight = fontSize * 0.45 + 3;
    for (const line of lines) {
      ensureSpace(lineHeight);
      doc.text(line, margin + indent, y);
      y += lineHeight;
    }
  };

  const section = (title: string) => {
    y += 4;
    ensureSpace(14);
    writeLines(title, 12, 'bold');
    y += 2;
  };

  writeLines(profile.name || 'Profile', 18, 'bold');
  if (profile.title) writeLines(profile.title, 12);
  const contactParts = [profile.contact?.email, profile.contact?.phone].filter(Boolean);
  if (contactParts.length) writeLines(contactParts.join(' · '), 10);
  y += 4;

  if (profile.skills?.length) {
    section('Skills');
    writeLines(profile.skills.join(', '));
  }
  if (profile.searchTitles?.length) {
    section('Target roles');
    writeLines(profile.searchTitles.join(', '));
  }
  if (profile.skillsToLearn?.length) {
    section('Skills to learn');
    writeLines(profile.skillsToLearn.join(', '));
  }
  if (profile.courses?.length) {
    section('Courses');
    writeLines(profile.courses.join(', '));
  }

  const writeExperienceBlock = (label: string, entries: ExperienceRecord) => {
    const items = Object.entries(entries || {}).filter(([key, entry]) => {
      const meta = getEntryMeta(entry, key);
      const bullets = getEntryBullets(entry);
      return meta.title.trim() || key.trim() || bullets.length > 0;
    });
    if (!items.length) return;
    section(label);
    for (const [key, entry] of items) {
      const meta = getEntryMeta(entry, key);
      const title = meta.title.trim() || key;
      const dates = [meta.startDate, meta.endDate].filter(Boolean).join(' – ');
      const subtitle = [meta.company, meta.location, dates].filter(Boolean).join(' · ');
      writeLines(title, 11, 'bold');
      if (subtitle) writeLines(subtitle, 10);
      for (const bullet of getEntryBullets(entry)) {
        writeLines(`• ${bullet}`, 10, 'normal', 4);
      }
      if (meta.context?.trim()) {
        writeLines(`Context: ${meta.context}`, 9, 'normal', 4);
      }
      y += 3;
    }
  };

  writeExperienceBlock('Experience', profile.experience || {});
  writeExperienceBlock('Projects', profile.projects || {});

  if (profile.goals?.length) {
    section('Goals');
    writeLines(profile.goals.join(', '));
  }
  if (profile.values?.length) {
    section('Values');
    writeLines(profile.values.join(', '));
  }
  if (profile.interests?.length) {
    section('Interests');
    writeLines(profile.interests.join(', '));
  }
  if (profile.writingSample?.trim()) {
    section('Writing sample');
    writeLines(profile.writingSample);
  }

  doc.save(safeFilename(profile.name || 'profile', 'summary'));
}
