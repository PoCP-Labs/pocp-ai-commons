import { createContext, useCallback, useContext, useMemo, useState } from "react";
import en from "./locales/en.json";
import zh from "./locales/zh.json";

const STORAGE_KEY = "pocp_locale";
const PACKS = { en, zh };

let currentAcceptLanguage = "en-US,en;q=0.9";

export function getAcceptLanguage() {
  return currentAcceptLanguage;
}

export function detectLocale() {
  if (typeof window === "undefined") return "en";
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("lang") || params.get("locale");
  if (fromQuery) {
    const norm = fromQuery.toLowerCase().startsWith("zh") ? "zh" : "en";
    localStorage.setItem(STORAGE_KEY, norm);
    return norm;
  }
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "en" || saved === "zh") return saved;
  const nav = (navigator.language || "en").toLowerCase();
  return nav.startsWith("zh") ? "zh" : "en";
}

function interpolate(template, vars) {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, key) =>
    vars[key] !== undefined && vars[key] !== null ? String(vars[key]) : `{${key}}`
  );
}

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(detectLocale);

  const setLocale = useCallback((next) => {
    const norm = next === "zh" ? "zh" : "en";
    localStorage.setItem(STORAGE_KEY, norm);
    setLocaleState(norm);
    document.documentElement.lang = norm === "zh" ? "zh-CN" : "en";
  }, []);

  const t = useCallback(
    (key, vars) => {
      const pack = PACKS[locale] || PACKS.en;
      const raw = pack[key] ?? PACKS.en[key] ?? key;
      return interpolate(raw, vars);
    },
    [locale]
  );

  const acceptLanguage = locale === "zh" ? "zh-CN,zh;q=0.9,en;q=0.8" : "en-US,en;q=0.9";
  currentAcceptLanguage = acceptLanguage;

  const value = useMemo(
    () => ({ locale, setLocale, t, acceptLanguage }),
    [locale, setLocale, t, acceptLanguage]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

/** Pick API field with optional *_zh sibling (entity ontology, intelligence payloads). */
export function pickLocalized(record, field, locale) {
  if (!record || locale !== "zh") return record?.[field];
  const zh = record[`${field}_zh`];
  return zh != null && zh !== "" ? zh : record[field];
}

export function LocaleSwitcher({ className = "" }) {
  const { locale, setLocale, t } = useI18n();
  return (
    <select
      className={className || "auth-persona-select"}
      value={locale}
      onChange={(e) => setLocale(e.target.value)}
      aria-label="Interface language"
      title="Interface language"
    >
      <option value="en">{t("lang.en")}</option>
      <option value="zh">{t("lang.zh")}</option>
    </select>
  );
}
