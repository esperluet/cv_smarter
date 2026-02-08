function normalizePath(path) {
  if (!path) {
    return "";
  }

  if (path.startsWith("/api/")) {
    return path.slice(4);
  }
  return path;
}

export function resolveArtifactDownloadPath(artifact) {
  if (!artifact || typeof artifact !== "object") {
    return "";
  }

  if (artifact.download_url) {
    try {
      const parsed = new URL(artifact.download_url, window.location.origin);
      return normalizePath(`${parsed.pathname}${parsed.search}`);
    } catch {
      if (typeof artifact.download_url === "string") {
        return normalizePath(artifact.download_url);
      }
    }
  }

  if (typeof artifact.storage_path === "string" && artifact.storage_path) {
    return `/v1/documents/artifacts/download?storage_path=${encodeURIComponent(artifact.storage_path)}`;
  }

  return "";
}

export function enrichArtifactsWithDownloadPath(payload) {
  if (!payload || typeof payload !== "object" || !Array.isArray(payload.artifacts)) {
    return payload;
  }

  return {
    ...payload,
    artifacts: payload.artifacts.map((artifact) => ({
      ...artifact,
      download_path: resolveArtifactDownloadPath(artifact),
    })),
  };
}
