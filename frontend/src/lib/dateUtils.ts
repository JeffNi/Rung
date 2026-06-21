/** Normalize profile dates for month pickers and backend parsing. */

const MONTH_NAMES: Record<string, number> = {
  jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6,
  jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12,
};

const SEASON_MONTH: Record<string, number> = {
  spring: 1, summer: 6, fall: 9, autumn: 9, winter: 12,
};

export function isPresentDate(value: string): boolean {
  const s = (value || '').trim().toLowerCase();
  return s === 'present' || s === 'current' || s === 'now' || s === 'ongoing';
}

/** Parse any stored date text to YYYY-MM-DD (internal). */
function toIsoDay(value: string): string {
  const s = (value || '').trim();
  if (!s || isPresentDate(s)) return '';

  const isoFull = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (isoFull) {
    return `${isoFull[1]}-${isoFull[2].padStart(2, '0')}-${isoFull[3].padStart(2, '0')}`;
  }

  const isoMonth = s.match(/^(\d{4})-(\d{1,2})$/);
  if (isoMonth) {
    return `${isoMonth[1]}-${isoMonth[2].padStart(2, '0')}-01`;
  }

  if (/^\d{4}$/.test(s)) return `${s}-01-01`;

  const slashMonthYear = s.match(/^(\d{1,2})[-/](\d{4})$/);
  if (slashMonthYear) {
    return `${slashMonthYear[2]}-${slashMonthYear[1].padStart(2, '0')}-01`;
  }

  const slashFull = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/);
  if (slashFull) {
    return `${slashFull[3]}-${slashFull[1].padStart(2, '0')}-${slashFull[2].padStart(2, '0')}`;
  }

  const named = s.match(/^([a-z]+)\s+(\d{4})$/i);
  if (named) {
    const month = MONTH_NAMES[named[1].slice(0, 3).toLowerCase()];
    if (month) return `${named[2]}-${String(month).padStart(2, '0')}-01`;
  }

  const season = s.match(/^(spring|summer|fall|autumn|winter)\s+(\d{4})$/i);
  if (season) {
    const month = SEASON_MONTH[season[1].toLowerCase()];
    return `${season[2]}-${String(month).padStart(2, '0')}-01`;
  }

  return '';
}

/** Convert stored date to YYYY-MM for <input type="month">. */
export function toMonthInputValue(value: string): string {
  const iso = toIsoDay(value);
  return iso ? iso.slice(0, 7) : '';
}

/** Normalize when loading profile — store YYYY-MM (or Present for end dates). */
export function normalizeProfileDate(value: string, isEnd = false): string {
  if (isEnd && isPresentDate(value)) return 'Present';
  const month = toMonthInputValue(value);
  return month || (value || '').trim();
}
