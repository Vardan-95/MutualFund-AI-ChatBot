export type UserGender = "male" | "female" | "other";

export type UserProfile = {
  name: string;
  gender: UserGender;
  email: string;
  profession: string;
  updatedAt: string;
};

export const USER_PROFILE_KEY = "wealthai_user_profile_v1";

export function loadUserProfile(): UserProfile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(USER_PROFILE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as UserProfile;
    if (!parsed?.name || !parsed?.gender) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveUserProfile(profile: UserProfile): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(USER_PROFILE_KEY, JSON.stringify(profile));
}

export function clearUserProfile(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(USER_PROFILE_KEY);
}

