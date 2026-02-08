import { useState } from "react";
import { useTranslation } from "react-i18next";

import Button from "../../shared/ui/Button";
import Card from "../../shared/ui/Card";
import TextField from "../../shared/ui/TextField";

function triggerBrowserDownload(blob, filename) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export default function CvGenerationSection({ sources, selectedSourceId, onSelectSource, onGeneratePdf }) {
  const { t } = useTranslation();
  const [jobDescription, setJobDescription] = useState("");
  const [graphId, setGraphId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!selectedSourceId) {
      setError(t("cv.generation.sourceRequired"));
      return;
    }
    if (!jobDescription.trim()) {
      setError(t("cv.generation.jobDescriptionRequired"));
      return;
    }

    setError("");
    setMessage("");
    setIsLoading(true);

    const generationResult = await onGeneratePdf({
      sourceId: selectedSourceId,
      jobDescription: jobDescription.trim(),
      graphId: graphId.trim() || undefined,
    });
    setIsLoading(false);

    if (!generationResult.ok) {
      setError(generationResult.message || t("errors.generic"));
      return;
    }

    triggerBrowserDownload(generationResult.blob, generationResult.filename || "cv_export.pdf");
    if (generationResult.runId) {
      setMessage(t("cv.generation.downloadStartedWithRun", { runId: generationResult.runId }));
      return;
    }
    setMessage(t("cv.generation.downloadStarted"));
  }

  return (
    <Card title={t("cv.generation.title")} description={t("cv.generation.description")}>
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field-label">{t("cv.generation.sourceLabel")}</span>
          <select
            className="field-input"
            value={selectedSourceId}
            onChange={(event) => onSelectSource(event.target.value)}
            disabled={sources.length === 0 || isLoading}
          >
            <option value="">{t("cv.generation.sourcePlaceholder")}</option>
            {sources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field-label">{t("cv.generation.jobDescriptionLabel")}</span>
          <textarea
            className="field-input field-textarea"
            rows={8}
            value={jobDescription}
            onChange={(event) => setJobDescription(event.target.value)}
            placeholder={t("cv.generation.jobDescriptionPlaceholder")}
          />
        </label>

        <TextField
          label={t("cv.generation.graphIdLabel")}
          type="text"
          value={graphId}
          onChange={(event) => setGraphId(event.target.value)}
          placeholder={t("cv.generation.graphIdPlaceholder")}
        />

        {error ? <p className="error-text">{error}</p> : null}
        {message ? <p className="success-text">{message}</p> : null}
        {!error && sources.length === 0 ? <p className="helper-text">{t("cv.generation.noSourceHint")}</p> : null}

        <Button type="submit" disabled={isLoading || sources.length === 0}>
          {isLoading ? t("cv.generation.processingPdf") : t("cv.generation.submitPdf")}
        </Button>
      </form>
    </Card>
  );
}
