import { getApiBaseUrl } from "../../shared/api/http";

export function parseFilenameFromDisposition(disposition) {
  if (!disposition) {
    return "";
  }

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]).trim();
    } catch {
      return utf8Match[1].trim();
    }
  }

  const basicMatch = disposition.match(/filename="?([^"]+)"?/i);
  return basicMatch?.[1]?.trim() || "";
}

export async function binaryRequest(path, options = {}) {
  const response = await fetch(`${getApiBaseUrl()}${path}`, options);
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const payload = await response.json();
      detail = payload?.detail || detail;
    } catch {
      // Keep default detail when body is not JSON.
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return response;
}
