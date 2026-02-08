import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enCommon from "./locales/en/common.json";
import frCommon from "./locales/fr/common.json";

const resources = {
  en: { common: enCommon },
  fr: { common: frCommon },
};

const defaultLanguage = localStorage.getItem("cv_optimizer_lang") || "en";

i18n.use(initReactI18next).init({
  resources,
  lng: defaultLanguage,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  defaultNS: "common",
});

i18n.on("languageChanged", (lang) => {
  localStorage.setItem("cv_optimizer_lang", lang);
});

export default i18n;
