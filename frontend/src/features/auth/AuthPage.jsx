import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";

import { useAuth } from "./AuthContext";
import Button from "../../shared/ui/Button";
import Card from "../../shared/ui/Card";
import LanguageSwitcher from "../../shared/ui/LanguageSwitcher";
import TextField from "../../shared/ui/TextField";

export default function AuthPage() {
  const [mode, setMode] = useState("signin");
  const [apiError, setApiError] = useState("");
  const { t } = useTranslation();
  const { signIn, signUp, isAuthenticated, isReady } = useAuth();

  const {
    register,
    handleSubmit,
    watch,
    resetField,
    formState: { errors, isSubmitting },
  } = useForm({ shouldUnregister: true });
  const passwordValue = watch("password");

  useEffect(() => {
    setApiError("");
    if (mode === "signin") {
      resetField("confirm_password");
    }
  }, [mode, resetField]);

  if (isReady && isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  async function onSubmit(values) {
    setApiError("");

    const action = mode === "signin" ? signIn : signUp;
    const payload =
      mode === "signin"
        ? { email: values.email, password: values.password }
        : {
            email: values.email,
            password: values.password,
            first_name: values.first_name,
            last_name: values.last_name,
          };
    const result = await action(payload);

    if (!result.ok) {
      setApiError(result.message || t("errors.generic"));
    }
  }

  return (
    <main className="page auth-page">
      <header className="page-header">
        <h1>{t("appName")}</h1>
        <LanguageSwitcher />
      </header>

      <Card title={t("auth.title")} description={t("auth.subtitle")} className="auth-card">
        <div className="tabs" role="tablist" aria-label="auth-modes">
          <button
            className={`tab ${mode === "signin" ? "tab-active" : ""}`.trim()}
            onClick={() => setMode("signin")}
            type="button"
          >
            {t("auth.signinTab")}
          </button>
          <button
            className={`tab ${mode === "signup" ? "tab-active" : ""}`.trim()}
            onClick={() => setMode("signup")}
            type="button"
          >
            {t("auth.signupTab")}
          </button>
        </div>

        <form className="form" onSubmit={handleSubmit(onSubmit)}>
          <TextField
            label={t("auth.email")}
            type="email"
            autoComplete="email"
            {...register("email", { required: t("errors.required") })}
            error={errors.email?.message}
          />
          <TextField
            label={t("auth.password")}
            type="password"
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            {...register("password", { required: t("errors.required") })}
            error={errors.password?.message}
          />

          {mode === "signup" ? (
            <>
              <TextField
                label={t("auth.confirmPassword")}
                type="password"
                autoComplete="new-password"
                {...register("confirm_password", {
                  required: t("errors.required"),
                  validate: (value) => value === passwordValue || t("errors.passwordMismatch"),
                })}
                error={errors.confirm_password?.message}
              />
              <TextField label={t("auth.firstName")} type="text" {...register("first_name")} />
              <TextField label={t("auth.lastName")} type="text" {...register("last_name")} />
            </>
          ) : null}

          {apiError ? <p className="error-text">{apiError}</p> : null}

          <Button type="submit" disabled={isSubmitting}>
            {mode === "signin" ? t("auth.signin") : t("auth.signup")}
          </Button>
        </form>
      </Card>
    </main>
  );
}
