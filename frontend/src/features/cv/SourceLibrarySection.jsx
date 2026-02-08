import { useState } from "react";
import { useTranslation } from "react-i18next";

import Button from "../../shared/ui/Button";
import Card from "../../shared/ui/Card";
import TextField from "../../shared/ui/TextField";

export default function SourceLibrarySection({
  sources,
  selectedSourceId,
  isLoading,
  loadError,
  onSelectSource,
  onCreateSource,
  onDeleteSource,
}) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [deletingId, setDeletingId] = useState("");
  const [fileInputKey, setFileInputKey] = useState(0);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!name.trim()) {
      setError(t("errors.required"));
      return;
    }
    if (!file) {
      setError(t("cv.sources.fileRequired"));
      return;
    }

    setError("");
    setMessage("");
    setIsCreating(true);

    const result = await onCreateSource({ name: name.trim(), file });
    setIsCreating(false);

    if (!result.ok) {
      setError(result.message || t("errors.generic"));
      return;
    }

    setName("");
    setFile(null);
    setFileInputKey((current) => current + 1);
    setMessage(t("cv.sources.uploadSuccess"));
  }

  async function handleDelete(sourceId) {
    setDeletingId(sourceId);
    setError("");
    setMessage("");

    const result = await onDeleteSource(sourceId);
    setDeletingId("");
    if (!result.ok) {
      setError(result.message || t("errors.generic"));
      return;
    }

    setMessage(t("cv.sources.deleteSuccess"));
  }

  return (
    <Card title={t("cv.sources.title")} description={t("cv.sources.description")}>
      <form className="form" onSubmit={handleSubmit}>
        <TextField
          label={t("cv.sources.nameLabel")}
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder={t("cv.sources.namePlaceholder")}
        />

        <label className="field">
          <span className="field-label">{t("cv.sources.fileLabel")}</span>
          <input
            key={fileInputKey}
            className="file-input"
            type="file"
            accept=".pdf,.txt,.doc,.docx"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </label>

        {error ? <p className="error-text">{error}</p> : null}
        {message ? <p className="success-text">{message}</p> : null}

        <Button type="submit" disabled={isCreating}>
          {isCreating ? t("cv.sources.uploading") : t("cv.sources.uploadAction")}
        </Button>
      </form>

      <div className="sources-list-block">
        <h3 className="subsection-title">{t("cv.sources.listTitle")}</h3>
        {isLoading ? <p className="helper-text">{t("cv.sources.loading")}</p> : null}
        {loadError ? <p className="error-text">{loadError}</p> : null}

        {!isLoading && !loadError && sources.length === 0 ? (
          <p className="helper-text">{t("cv.sources.empty")}</p>
        ) : null}

        {sources.length > 0 ? (
          <ul className="sources-list">
            {sources.map((source) => {
              const isSelected = selectedSourceId === source.id;
              const isDeleting = deletingId === source.id;
              return (
                <li key={source.id} className={`source-item ${isSelected ? "source-item-selected" : ""}`.trim()}>
                  <button
                    type="button"
                    className="source-item-main"
                    onClick={() => onSelectSource(source.id)}
                    title={source.original_filename}
                  >
                    <span className="source-item-name">{source.name}</span>
                    <span className="source-item-meta">{source.original_filename}</span>
                  </button>

                  <Button
                    variant="ghost"
                    onClick={() => handleDelete(source.id)}
                    disabled={isDeleting || isCreating}
                  >
                    {isDeleting ? t("cv.sources.deleting") : t("cv.sources.deleteAction")}
                  </Button>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>
    </Card>
  );
}
