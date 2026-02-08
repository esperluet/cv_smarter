import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

import { request } from "../../shared/api/http";
import { enrichArtifactsWithDownloadPath, resolveArtifactDownloadPath } from "../cv/artifactDownload";
import { normalizeError } from "./errorUtils";
import { binaryRequest, parseFilenameFromDisposition } from "./httpUtils";
import { requestWithRefresh } from "./requestWithRefresh";
import { clearRefreshToken, readRefreshToken, writeRefreshToken } from "./sessionStore";

const AuthContext = createContext(null);

function fallbackFilenameFromArtifact(artifact) {
  if (!artifact?.storage_path || typeof artifact.storage_path !== "string") {
    return "artifact";
  }
  const chunks = artifact.storage_path.split("/");
  return chunks[chunks.length - 1] || "artifact";
}

function buildSignUpPayload(values) {
  return {
    email: values.email,
    password: values.password,
    first_name: values.first_name || undefined,
    last_name: values.last_name || undefined,
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isReady, setIsReady] = useState(false);
  const [accessToken, setAccessToken] = useState("");

  const refreshTokenRef = useRef(readRefreshToken());
  const accessTokenRef = useRef("");

  useEffect(() => {
    accessTokenRef.current = accessToken;
  }, [accessToken]);

  function hasRefreshToken() {
    return Boolean(refreshTokenRef.current);
  }

  function clearSession() {
    setUser(null);
    setAccessToken("");
    accessTokenRef.current = "";
    refreshTokenRef.current = "";
    clearRefreshToken();
  }

  async function refreshSession() {
    if (!hasRefreshToken()) {
      return false;
    }

    try {
      const payload = await request("/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshTokenRef.current }),
      });

      setAccessToken(payload.access_token);
      accessTokenRef.current = payload.access_token;
      refreshTokenRef.current = payload.refresh_token;
      writeRefreshToken(payload.refresh_token);
      setUser(payload.user);
      return true;
    } catch {
      clearSession();
      return false;
    }
  }

  async function initSession() {
    if (!hasRefreshToken()) {
      setIsReady(true);
      return;
    }

    await refreshSession();
    setIsReady(true);
  }

  useEffect(() => {
    initSession();
  }, []);

  async function authRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (accessTokenRef.current) {
      headers.set("Authorization", `Bearer ${accessTokenRef.current}`);
    }

    return requestWithRefresh({
      execute: () => request(path, { ...options, headers }),
      hasRefreshToken,
      refreshSession,
    });
  }

  async function authBinaryRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (accessTokenRef.current) {
      headers.set("Authorization", `Bearer ${accessTokenRef.current}`);
    }

    return requestWithRefresh({
      execute: () => binaryRequest(path, { ...options, headers }),
      hasRefreshToken,
      refreshSession,
    });
  }

  async function signUp(form) {
    try {
      const payload = await request("/v1/auth/sign-up", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildSignUpPayload(form)),
      });

      setUser(payload.user);
      setAccessToken(payload.access_token);
      accessTokenRef.current = payload.access_token;
      refreshTokenRef.current = payload.refresh_token;
      writeRefreshToken(payload.refresh_token);
      return { ok: true };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  async function signIn(form) {
    try {
      const payload = await request("/v1/auth/sign-in", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      setUser(payload.user);
      setAccessToken(payload.access_token);
      accessTokenRef.current = payload.access_token;
      refreshTokenRef.current = payload.refresh_token;
      writeRefreshToken(payload.refresh_token);
      return { ok: true };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  async function signOut() {
    if (hasRefreshToken()) {
      try {
        await request("/v1/auth/sign-out", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshTokenRef.current }),
        });
      } catch {
        // Keep logout resilient if the API call fails.
      }
    }

    clearSession();
  }

  async function fetchMe() {
    try {
      const payload = await authRequest("/v1/account/me", { method: "GET" });
      setUser(payload.user);
      return { ok: true, user: payload.user };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  async function updateMe(updates) {
    try {
      const payload = await authRequest("/v1/account/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      setUser(payload.user);
      return { ok: true, user: payload.user };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  async function uploadCv(file) {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const payload = await authRequest("/v1/cv/upload", {
        method: "POST",
        body: formData,
      });
      return { ok: true, payload: enrichArtifactsWithDownloadPath(payload) };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  async function downloadArtifact(artifact) {
    const downloadPath = resolveArtifactDownloadPath(artifact);
    if (!downloadPath) {
      return { ok: false, message: "Artifact download is unavailable." };
    }

    try {
      const response = await authBinaryRequest(downloadPath, { method: "GET" });
      const blob = await response.blob();
      const filename =
        parseFilenameFromDisposition(response.headers.get("content-disposition")) ||
        fallbackFilenameFromArtifact(artifact);
      return { ok: true, blob, filename };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  async function createGroundSource({ name, file }) {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("file", file);

    try {
      const payload = await authRequest("/v1/sources", {
        method: "POST",
        body: formData,
      });
      return { ok: true, payload };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  async function listGroundSources() {
    try {
      const payload = await authRequest("/v1/sources", {
        method: "GET",
      });
      return { ok: true, items: payload.items || [] };
    } catch (error) {
      return { ok: false, message: normalizeError(error), items: [] };
    }
  }

  async function deleteGroundSource(sourceId) {
    try {
      await authRequest(`/v1/sources/${sourceId}`, {
        method: "DELETE",
      });
      return { ok: true };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  async function generateCvFromSource({ sourceId, jobDescription, graphId }) {
    const formData = new FormData();
    formData.append("source_id", sourceId);
    formData.append("job_description", jobDescription);
    if (graphId) {
      formData.append("graph_id", graphId);
    }

    try {
      const payload = await authRequest("/v1/cv/generate-from-source", {
        method: "POST",
        body: formData,
      });
      return { ok: true, payload };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  async function generateCvPdfFromSource({ sourceId, jobDescription, graphId, formatHint }) {
    const formData = new FormData();
    formData.append("source_id", sourceId);
    formData.append("job_description", jobDescription);
    if (graphId) {
      formData.append("graph_id", graphId);
    }
    if (formatHint) {
      formData.append("format_hint", formatHint);
    }

    try {
      const response = await authBinaryRequest("/v1/cv/generate-from-source/pdf", {
        method: "POST",
        body: formData,
      });
      const blob = await response.blob();
      const filename = parseFilenameFromDisposition(response.headers.get("content-disposition")) || "cv_export.pdf";
      const runId = response.headers.get("x-cv-run-id") || "";
      return { ok: true, blob, filename, runId };
    } catch (error) {
      return { ok: false, message: normalizeError(error) };
    }
  }

  const value = useMemo(
    () => ({
      user,
      isReady,
      isAuthenticated: Boolean(user && accessToken),
      signIn,
      signUp,
      signOut,
      fetchMe,
      updateMe,
      uploadCv,
      downloadArtifact,
      createGroundSource,
      listGroundSources,
      deleteGroundSource,
      generateCvFromSource,
      generateCvPdfFromSource,
    }),
    [user, isReady, accessToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
