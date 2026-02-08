import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import CvSection from "../cv/CvSection";
import LanguageSwitcher from "../../shared/ui/LanguageSwitcher";
import ProfileSection from "./ProfileSection";
import Button from "../../shared/ui/Button";

export default function WorkspacePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { fetchMe, signOut, isAuthenticated } = useAuth();

  useEffect(() => {
    fetchMe();
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/auth", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  async function onSignOut() {
    await signOut();
    navigate("/auth", { replace: true });
  }

  return (
    <main className="page workspace-page">
      <header className="workspace-header">
        <div>
          <h1>{t("workspace.title")}</h1>
          <p>{t("workspace.subtitle")}</p>
        </div>

        <div className="workspace-actions">
          <LanguageSwitcher />
          <Button variant="ghost" onClick={onSignOut}>
            {t("workspace.signOut")}
          </Button>
        </div>
      </header>

      <div className="workspace-grid">
        <ProfileSection />
        <CvSection />
      </div>
    </main>
  );
}
