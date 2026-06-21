/** Strip HTML entities/tags from JSearch descriptions for display. */
export function cleanJobDescription(text: string): string {
  if (!text) return '';

  let cleaned = text
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");

  cleaned = cleaned.replace(/<br\s*\/?>/gi, '\n');
  cleaned = cleaned.replace(/<\/p\s*>/gi, '\n');
  cleaned = cleaned.replace(/<\/div\s*>/gi, '\n');
  cleaned = cleaned.replace(/<\/li\s*>/gi, '\n');
  cleaned = cleaned.replace(/<li[^>]*>/gi, '- ');
  cleaned = cleaned.replace(/<[^>]+>/g, '');
  cleaned = cleaned.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  cleaned = cleaned.replace(/[ \t]+\n/g, '\n');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  cleaned = cleaned.replace(/[ \t]{2,}/g, ' ');

  return cleaned.trim();
}
