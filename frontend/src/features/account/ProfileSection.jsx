import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import Button from "../../shared/ui/Button";
import Card from "../../shared/ui/Card";
import TextField from "../../shared/ui/TextField";

export default function ProfileSection() {
  const { t } = useTranslation();
  const { user, updateMe } = useAuth();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm({
    defaultValues: {
      first_name: user?.first_name || "",
      last_name: user?.last_name || "",
    },
  });

  async function onSubmit(values) {
    setMessage("");
    setError("");

    const updates = {};
    if (values.first_name !== (user?.first_name || "")) {
      updates.first_name = values.first_name || null;
    }
    if (values.last_name !== (user?.last_name || "")) {
      updates.last_name = values.last_name || null;
    }

    const result = await updateMe(updates);
    if (!result.ok) {
      setError(result.message || t("errors.generic"));
      return;
    }

    setMessage(t("profile.success"));
  }

  return (
    <Card title={t("profile.title")} description={t("profile.description")}>
      <div className="profile-meta">
        <span>{user?.email}</span>
        <span>{user?.role}</span>
      </div>

      <form className="form" onSubmit={handleSubmit(onSubmit)}>
        <TextField label={t("auth.firstName")} type="text" {...register("first_name")} />
        <TextField label={t("auth.lastName")} type="text" {...register("last_name")} />

        {error ? <p className="error-text">{error}</p> : null}
        {message ? <p className="success-text">{message}</p> : null}

        <Button type="submit" disabled={isSubmitting}>
          {t("profile.save")}
        </Button>
      </form>
    </Card>
  );
}
