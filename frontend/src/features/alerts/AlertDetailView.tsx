import { useState } from "react";
import { AlertWithExplanation } from "../../lib/parseAlert";
import { ChildAccountResponse } from "../../apis";
import ConversationViewer from "./ConversationViewer";
import AiAnalysisPanel from "./AiAnalysisPanel";
import { NewlyDetectedStage } from "../../apis/models/NewlyDetectedStage";
import { 
  ArrowLeft, 
  MessageSquare, 
  Sparkles, 
  Check, 
  ShieldCheck
} from "lucide-react";

interface AlertDetailViewProps {
  alert: AlertWithExplanation;
  children: ChildAccountResponse[];
  onBack: () => void;
  onAcknowledge: (alertId: number) => Promise<void>;
  onUpdateAlert: (updatedAlert: AlertWithExplanation) => void;
}

export default function AlertDetailView({
  alert,
  children,
  onBack,
  onAcknowledge,
  onUpdateAlert,
}: AlertDetailViewProps) {
  const [activeTab, setActiveTab] = useState<"chat" | "analysis">("chat");

  // Find child display name
  const kid = children.find((c) => c.id === alert.childAccountId);
  const childName = kid ? (kid.displayName || kid.platformUserId) : `Child #${alert.childAccountId}`;

  // Local helper to append newly detected stages to this alert
  const handleAnalysisUpdated = (newStages: NewlyDetectedStage[]) => {
    // Deduplicate stages and merge
    const existingStages = [...alert.detectedStages];
    newStages.forEach((newS) => {
      const exists = existingStages.some((exS) => exS.stage.toLowerCase() === newS.stage.toLowerCase());
      if (!exists) {
        existingStages.push(newS);
      }
    });

    onUpdateAlert({
      ...alert,
      detectedStages: existingStages,
    });
  };

  return (
    <div className="space-y-4">
      {/* Top Navigation / Breadcrumbs */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <button
          onClick={onBack}
          className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          Back to Alerts
        </button>

        <div className="flex items-center gap-2">
          {!alert.acknowledged ? (
            <button
              onClick={async () => {
                await onAcknowledge(alert.id);
                onBack(); // go back after acknowledging
              }}
              className="px-3 py-1.5 text-xs font-semibold text-emerald-400 border border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10 rounded-lg transition-all flex items-center gap-1.5 active:scale-[0.98]"
            >
              <Check className="w-3.5 h-3.5" />
              Acknowledge Alert
            </button>
          ) : (
            <span className="text-xs text-slate-500 bg-slate-900 border border-slate-850 px-3 py-1.5 rounded-lg flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
              Alert Acknowledged
            </span>
          )}
        </div>
      </div>

      {/* Profile Bar info */}
      <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between flex-wrap gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-white">Monitoring: {childName}</h2>
            <span className="text-[10px] text-slate-500">•</span>
            <span className="text-[10px] text-slate-400 uppercase font-mono">{alert.platform}</span>
          </div>
          <p className="text-[11px] text-slate-500">
            Server ID: <code className="font-mono text-slate-400">{alert.serverId}</code>
          </p>
        </div>
        <div className="text-xs text-slate-400">
          Detected: <strong className="text-slate-350">{new Date(alert.createdAt).toLocaleString()}</strong>
        </div>
      </div>

      {/* Tabs for Mobile/Tablet layout */}
      <div className="flex lg:hidden bg-slate-900/60 p-1 rounded-lg border border-slate-800">
        <button
          onClick={() => setActiveTab("chat")}
          className={`flex-1 py-2 text-xs font-medium rounded-md flex items-center justify-center gap-1.5 transition-all ${
            activeTab === "chat" 
              ? "bg-slate-800 text-white shadow-sm" 
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          Chat Conversation
        </button>
        <button
          onClick={() => setActiveTab("analysis")}
          className={`flex-1 py-2 text-xs font-medium rounded-md flex items-center justify-center gap-1.5 transition-all ${
            activeTab === "analysis" 
              ? "bg-slate-800 text-white shadow-sm" 
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          AI Analysis Panel
        </button>
      </div>

      {/* Split Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Chat Conversation Viewer */}
        <div className={`lg:col-span-2 ${activeTab === "chat" ? "block" : "hidden lg:block"}`}>
          <ConversationViewer
            messages={alert.messages ?? []}
            detectedStages={alert.detectedStages}
            childName={alert.platform === "discord" ? childName : alert.serverId} // simple check or map sender names
          />
        </div>

        {/* AI Analysis Panel */}
        <div className={`${activeTab === "analysis" ? "block" : "hidden lg:block"}`}>
          <AiAnalysisPanel
            alert={alert}
            messages={alert.messages ?? []}
            onAnalysisUpdated={handleAnalysisUpdated}
          />
        </div>

      </div>
    </div>
  );
}
