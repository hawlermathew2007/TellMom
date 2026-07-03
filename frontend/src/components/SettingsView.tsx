import React from "react";
import { AppSettings } from "../hooks/useSettings";
import { playAlertSound } from "../lib/sound";
import { 
  Volume2, 
  VolumeX, 
  Sun, 
  Moon, 
  Clock, 
  Bell, 
  BellOff, 
  Settings,
  RefreshCw
} from "lucide-react";

interface SettingsViewProps {
  settings: AppSettings;
  onUpdateSetting: <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => void;
}

export default function SettingsView({ settings, onUpdateSetting }: SettingsViewProps) {
  
  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    onUpdateSetting("soundVolume", value);
    // Play sound on adjustment so the parent can hear the volume level
    if (settings.soundEnabled) {
      playAlertSound(value);
    }
  };

  const requestDesktopNotificationPermission = async () => {
    if (!("Notification" in window)) {
      alert("This browser does not support desktop notifications.");
      return;
    }

    if (Notification.permission === "granted") {
      onUpdateSetting("desktopNotifications", !settings.desktopNotifications);
      return;
    }

    if (Notification.permission !== "denied") {
      const permission = await Notification.requestPermission();
      if (permission === "granted") {
        onUpdateSetting("desktopNotifications", true);
        new Notification("TellMom Activated", {
          body: "Desktop notifications have been successfully enabled.",
          icon: "/favicon.ico"
        });
      }
    } else {
      alert("Notification permissions have been denied. Please reset permissions in your browser address bar settings.");
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Top Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">System Settings</h1>
        <p className="text-slate-400 text-sm">Configure parent monitoring dashboard alerts, notifications, and visual styling</p>
      </div>

      <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl divide-y divide-slate-800/60 overflow-hidden">
        
        {/* Theme Settings */}
        <div className="p-5 flex items-center justify-between gap-4">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-slate-200">Dashboard Theme</h3>
            <p className="text-xs text-slate-500">Toggle between dark-mode first Slack/Discord layout and light-mode layout.</p>
          </div>
          <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800">
            <button
              onClick={() => onUpdateSetting("theme", "light")}
              className={`p-2 rounded flex items-center gap-1.5 text-xs font-semibold transition-all ${
                settings.theme === "light"
                  ? "bg-slate-800 text-violet-400"
                  : "text-slate-500 hover:text-slate-350"
              }`}
            >
              <Sun className="w-3.5 h-3.5" />
              Light
            </button>
            <button
              onClick={() => onUpdateSetting("theme", "dark")}
              className={`p-2 rounded flex items-center gap-1.5 text-xs font-semibold transition-all ${
                settings.theme === "dark"
                  ? "bg-slate-800 text-violet-400"
                  : "text-slate-500 hover:text-slate-350"
              }`}
            >
              <Moon className="w-3.5 h-3.5" />
              Dark
            </button>
          </div>
        </div>

        {/* Notification Sound Toggle */}
        <div className="p-5 flex items-center justify-between gap-4">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-slate-200">Audio Alert Sound</h3>
            <p className="text-xs text-slate-500">Play an electronic ping tone instantly when a new security threat is ingested.</p>
          </div>
          <button
            onClick={() => onUpdateSetting("soundEnabled", !settings.soundEnabled)}
            className={`w-12 h-6 rounded-full p-0.5 transition-all focus:outline-none ${
              settings.soundEnabled ? "bg-violet-600 flex justify-end" : "bg-slate-800 flex justify-start"
            }`}
          >
            <span className="w-5 h-5 rounded-full bg-white shadow-sm block" />
          </button>
        </div>

        {/* Volume Slider */}
        {settings.soundEnabled && (
          <div className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-slate-200">Alert Volume</h3>
              <p className="text-xs text-slate-500">Adjust the volume of synthetic notification tones.</p>
            </div>
            <div className="flex items-center gap-3 w-full sm:w-64">
              {settings.soundVolume === 0 ? (
                <VolumeX className="w-4 h-4 text-slate-500" />
              ) : (
                <Volume2 className="w-4 h-4 text-violet-400" />
              )}
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.soundVolume}
                onChange={handleVolumeChange}
                className="w-full h-1.5 bg-slate-950 border border-slate-800 rounded-lg appearance-none cursor-pointer accent-violet-600"
              />
              <span className="text-[10px] font-bold text-slate-500 font-mono w-8 text-right">
                {Math.round(settings.soundVolume * 100)}%
              </span>
            </div>
          </div>
        )}

        {/* Desktop Notification Toggle */}
        <div className="p-5 flex items-center justify-between gap-4">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-slate-200">Desktop Push Notifications</h3>
            <p className="text-xs text-slate-500">Show system overlay notification banners even when the monitoring app is in the background.</p>
          </div>
          <button
            onClick={requestDesktopNotificationPermission}
            className={`w-12 h-6 rounded-full p-0.5 transition-all focus:outline-none ${
              settings.desktopNotifications ? "bg-violet-600 flex justify-end" : "bg-slate-800 flex justify-start"
            }`}
          >
            <span className="w-5 h-5 rounded-full bg-white shadow-sm block" />
          </button>
        </div>

        {/* Polling/Refresh Interval */}
        <div className="p-5 flex items-center justify-between gap-4">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-slate-200">Auto-Refresh Interval</h3>
            <p className="text-xs text-slate-500">Frequency for querying the backend for new alert logs (polling fallback if socket disconnects).</p>
          </div>
          <select
            value={settings.autoRefreshInterval}
            onChange={(e) => onUpdateSetting("autoRefreshInterval", parseInt(e.target.value))}
            className="bg-slate-950 border border-slate-800 rounded-lg py-2 px-3 text-xs text-slate-350 focus:outline-none"
          >
            <option value="10">Every 10 Seconds</option>
            <option value="30">Every 30 Seconds</option>
            <option value="60">Every 1 Minute</option>
            <option value="180">Every 3 Minutes</option>
            <option value="0">Manual Refresh Only</option>
          </select>
        </div>

      </div>
    </div>
  );
}
