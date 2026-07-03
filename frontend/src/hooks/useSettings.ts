import { useState, useEffect } from "react";

export interface AppSettings {
  theme: "light" | "dark";
  soundEnabled: boolean;
  soundVolume: number;
  desktopNotifications: boolean;
  autoRefreshInterval: number; // in seconds, 0 means manual
}

const DEFAULT_SETTINGS: AppSettings = {
  theme: "dark",
  soundEnabled: true,
  soundVolume: 0.5,
  desktopNotifications: false,
  autoRefreshInterval: 30,
};

export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(() => {
    const saved = localStorage.getItem("tellmom_settings");
    if (saved) {
      try {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
      } catch {
        return DEFAULT_SETTINGS;
      }
    }
    return DEFAULT_SETTINGS;
  });

  useEffect(() => {
    localStorage.setItem("tellmom_settings", JSON.stringify(settings));
    
    // Apply theme class to document element
    const root = window.document.documentElement;
    if (settings.theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [settings]);

  const updateSetting = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  return { settings, updateSetting };
}
