const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

async function parseJsonOrNull(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const payload = await parseJsonOrNull(response);

  if (!response.ok) {
    const error = new Error(payload?.detail || "Request failed");
    error.status = response.status;
    throw error;
  }

  return payload;
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}
