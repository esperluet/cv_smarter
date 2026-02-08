const REFRESH_TOKEN_KEY = "cv_optimizer_refresh_token";
const STORAGE_MODE = import.meta.env.VITE_REFRESH_TOKEN_STORAGE === "session" ? "session" : "local";

let inMemoryToken = "";

function resolveStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return STORAGE_MODE === "session" ? window.sessionStorage : window.localStorage;
  } catch {
    return null;
  }
}

export function readRefreshToken() {
  const storage = resolveStorage();
  if (!storage) {
    return inMemoryToken;
  }

  const token = storage.getItem(REFRESH_TOKEN_KEY) || "";
  inMemoryToken = token;
  return token;
}

export function writeRefreshToken(token) {
  const safeToken = token || "";
  inMemoryToken = safeToken;

  const storage = resolveStorage();
  if (!storage) {
    return;
  }
  storage.setItem(REFRESH_TOKEN_KEY, safeToken);
}

export function clearRefreshToken() {
  inMemoryToken = "";
  const storage = resolveStorage();
  if (!storage) {
    return;
  }
  storage.removeItem(REFRESH_TOKEN_KEY);
}

export function getRefreshTokenStorageMode() {
  return STORAGE_MODE;
}
