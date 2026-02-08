import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import CvGenerationSection from "./CvGenerationSection";
import SourceLibrarySection from "./SourceLibrarySection";

export default function CvSection() {
  const { t } = useTranslation();
  const { listGroundSources, createGroundSource, deleteGroundSource, generateCvPdfFromSource } = useAuth();
  const [sources, setSources] = useState([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [isLoadingSources, setIsLoadingSources] = useState(true);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    void refreshSources();
  }, []);

  async function refreshSources(preferredSourceId = "") {
    setIsLoadingSources(true);
    setLoadError("");

    const result = await listGroundSources();
    setIsLoadingSources(false);
    if (!result.ok) {
      setLoadError(result.message || t("cv.sources.loadError"));
      return { ok: false, message: result.message };
    }

    const nextSources = result.items || [];
    setSources(nextSources);

    const containsPreferred = preferredSourceId && nextSources.some((item) => item.id === preferredSourceId);
    if (containsPreferred) {
      setSelectedSourceId(preferredSourceId);
      return { ok: true };
    }

    setSelectedSourceId((currentSourceId) => {
      if (currentSourceId && nextSources.some((item) => item.id === currentSourceId)) {
        return currentSourceId;
      }
      return nextSources[0]?.id || "";
    });

    return { ok: true };
  }

  async function handleCreateSource({ name, file }) {
    const result = await createGroundSource({ name, file });
    if (!result.ok) {
      return result;
    }
    await refreshSources(result.payload?.id || "");
    return result;
  }

  async function handleDeleteSource(sourceId) {
    const result = await deleteGroundSource(sourceId);
    if (!result.ok) {
      return result;
    }
    await refreshSources();
    return result;
  }

  return (
    <div className="cv-panels">
      <SourceLibrarySection
        sources={sources}
        selectedSourceId={selectedSourceId}
        isLoading={isLoadingSources}
        loadError={loadError}
        onSelectSource={setSelectedSourceId}
        onCreateSource={handleCreateSource}
        onDeleteSource={handleDeleteSource}
      />

      <CvGenerationSection
        sources={sources}
        selectedSourceId={selectedSourceId}
        onSelectSource={setSelectedSourceId}
        onGeneratePdf={generateCvPdfFromSource}
      />
    </div>
  );
}
