import { useTranslation } from "react-i18next";

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  function onChange(event) {
    i18n.changeLanguage(event.target.value);
  }

  return (
    <label className="lang-switcher">
      <span>Lang</span>
      <select value={i18n.language} onChange={onChange}>
        <option value="en">EN</option>
        <option value="fr">FR</option>
      </select>
    </label>
  );
}
