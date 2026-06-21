export const PROFILE_UPDATED_KEY = 'rung_profile_updated';

export function markProfileUpdated(): void {
  sessionStorage.setItem(PROFILE_UPDATED_KEY, String(Date.now()));
}

export function clearProfileUpdated(): void {
  sessionStorage.removeItem(PROFILE_UPDATED_KEY);
}

export function isProfileUpdated(): boolean {
  return sessionStorage.getItem(PROFILE_UPDATED_KEY) != null;
}
