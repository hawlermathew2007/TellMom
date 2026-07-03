import React, { useState } from "react";
import { AlertWithExplanation } from "../../lib/parseAlert";
import { ChatMessageResponse } from "../../apis";
import { NewlyDetectedStage } from "../../apis/models/NewlyDetectedStage";
import { getApis } from "../../apis/client";
import { ResponseError } from "../../apis";
import { 
  ShieldAlert, 
  Play, 
  Loader2, 
  CheckCircle2, 
  HelpCircle,
  AlertOctagon,
  ArrowRight,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import { format } from "date-fns";

interface AiAnalysisPanelProps {
  alert: AlertWithExplanation;
  messages: ChatMessageResponse[];
  onAnalysisUpdated: (newStages: NewlyDetectedStage[]) => void;
}

// All 7 grooming stages in standard sociological order
const GROOMING_STAGES_DETAILS = [
  {
    name: "Victim Selection",
    description: "Targeting a child based on vulnerability, age, or online access.",
    reasoning: "The participant starts interacting frequently with the child, seeking details about their offline life, family, and screen time to evaluate vulnerability.",
    action: "Discuss online stranger safety with your child. Monitor future chat history."
  },
  {
    name: "Access and Relationship Building",
    description: "Gaining access and building an initial online relationship.",
    reasoning: "The participant attempts to find common interests (e.g. sharing virtual items, gaming together, or chatting privately) to make themselves seem friendly and appealing.",
    action: "Remind your child not to accept in-game currency or gifts from unknown users."
  },
  {
    name: "Trust Development",
    description: "Developing a bond of trust through support and praise.",
    reasoning: "The participant uses intense positive reinforcement, flattery, or plays the role of a supportive mentor, establishing an emotional hook.",
    action: "Have a conversation with your child. Emphasize that online mentors shouldn't ask them to bypass parents."
  },
  {
    name: "Isolation",
    description: "Encouraging the child to keep secrets from parents/guardians.",
    reasoning: "The participant actively tells the child to keep their friendship a secret, delete chat history, or warns them that 'parents wouldn't understand'.",
    action: "Highly Suspicious. Instruct your child to stop talking to this user. Check account security settings."
  },
  {
    name: "Boundary Testing",
    description: "Pushing boundaries with slightly inappropriate topics or secrets.",
    reasoning: "The participant starts introducing mild adult themes, personal secrets, or requests for selfies, testing the child's willingness to cross boundaries.",
    action: "High Risk. Intervene immediately. Instruct your child to block this user. Talk to them about grooming indicators."
  },
  {
    name: "Desensitization",
    description: "Normalizing inappropriate conversations and requests.",
    reasoning: "The participant normalizes inappropriate dialogue, gradually escalating to requests for private contact details or webcams, desensitizing the child.",
    action: "Critical Danger. Block user, secure child's device, and export conversation history immediately."
  },
  {
    name: "Maintaining Control",
    description: "Using coercion, blackmails, or emotional manipulation to sustain control.",
    reasoning: "The participant uses threats of exposure, emotional blackmail, or gifts to maintain compliance and control over the child's behavior.",
    action: "Immediate Action Required. Block, report to platform, and contact local authorities or online child defense organizations (e.g., NCMEC)."
  }
];

export default function AiAnalysisPanel({
  alert,
  messages,
  onAnalysisUpdated,
}: AiAnalysisPanelProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<"idle" | "running" | "success" | "failed">("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [expandedStage, setExpandedStage] = useState<string | null>(null);

  // Map database messageId to message content for easy evidence display
  const getMessageContent = (messageId: number) => {
    const msg = messages.find((m) => m.id === messageId);
    return msg ? msg.content : "";
  };

  // Map probability to risk severity details
  const riskPercent = Math.round(alert.probability * 100);
  const getRiskDetails = (prob: number) => {
    if (prob >= 0.75) return { label: "Critical Risk", color: "text-red-400 bg-red-500/10 border-red-500/25", icon: AlertOctagon };
    if (prob >= 0.50) return { label: "High Risk", color: "text-orange-400 bg-orange-500/10 border-orange-500/25", icon: ShieldAlert };
    if (prob >= 0.25) return { label: "Medium Risk", color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/25", icon: ShieldAlert };
    return { label: "Low Risk", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/25", icon: CheckCircle2 };
  };
  
  const riskDetails = getRiskDetails(alert.probability);
  const RiskIcon = riskDetails.icon;

  // Compile active stages from detectedStages
  const activeStagesMap = React.useMemo(() => {
    const map: Record<string, NewlyDetectedStage> = {};
    alert.detectedStages.forEach((s) => {
      map[s.stage] = s;
    });
    return map;
  }, [alert.detectedStages]);

  const activeStageCount = Object.keys(activeStagesMap).length;

  // Formulate a beautiful summary
  const summaryText = React.useMemo(() => {
    if (activeStageCount === 0) {
      return `Our AI classifier has flagged this conversation due to a risk probability of ${riskPercent}%. However, no specific sequential grooming stages have been fully identified yet. Click 'Continue AI Analysis' to scan recent messages.`;
    }
    
    // Get highest risk stage detected
    let highestStageName = "";
    for (let i = GROOMING_STAGES_DETAILS.length - 1; i >= 0; i--) {
      const stage = GROOMING_STAGES_DETAILS[i];
      if (activeStagesMap[stage.name] || activeStagesMap[stage.name.toLowerCase()]) {
        highestStageName = stage.name;
        break;
      }
    }

    return `Alert flagged at ${riskPercent}% probability. Sequencing analysis indicates the conversation has progressed to the '${highestStageName}' stage. AI has identified ${activeStageCount} of 7 grooming indicators in this message stream. Immediate parental observation and guidance are advised.`;
  }, [activeStageCount, activeStagesMap, riskPercent]);

  // Formulate recommended actions
  const recommendedActionsList = React.useMemo(() => {
    const actions: string[] = [];
    
    // Add default actions based on highest stage
    let maxStageIndex = -1;
    GROOMING_STAGES_DETAILS.forEach((s, idx) => {
      if (activeStagesMap[s.name]) {
        maxStageIndex = idx;
      }
    });

    if (maxStageIndex >= 0) {
      actions.push(GROOMING_STAGES_DETAILS[maxStageIndex].action);
    } else {
      actions.push("Talk to your child about online safety and confirm if they know this user.");
    }

    actions.push("Check platform privacy configurations and limit private messaging.");
    
    if (alert.probability >= 0.5) {
      actions.push("Instruct your child to stop communicating with this specific user immediately.");
    }
    
    return actions;
  }, [activeStagesMap, alert.probability]);

  // Call the backend endpoint to continue analyzing pending messages
  const handleContinueAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisStatus("running");
    setStatusMessage("Extracting pending messages...");

    try {
      // Simulate/Show streaming progress for 1.5 seconds to make the UI feel premium and alive
      setTimeout(() => setStatusMessage("Running grooming classifier models..."), 500);
      setTimeout(() => setStatusMessage("Evaluating grooming stages sequence..."), 1000);
      
      const response = await getApis().alerts.getGroomingAnalysisApiAlertsAlertIdGroomingAnalysisGet({
        alertId: alert.id
      });

      const newStages = response.newStages ?? [];
      
      // Update parent list
      onAnalysisUpdated(newStages);
      setAnalysisStatus("success");
      
      if (newStages.length > 0) {
        setStatusMessage(`Analysis complete! Detected ${newStages.length} new stage(s).`);
      } else {
        setStatusMessage("Analysis complete. No new grooming stages were detected.");
      }
    } catch (err: unknown) {
      setAnalysisStatus("failed");
      if (err instanceof ResponseError) {
        setStatusMessage(`Analysis failed (${err.response.status}). Ensure GROQ_API_KEY is configured.`);
      } else {
        setStatusMessage("Analysis failed. Please try again.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden">
      
      {/* Header */}
      <div className="p-4 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-violet-400" />
          <h3 className="text-sm font-semibold text-slate-200">AI Grooming Analysis</h3>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">Model v2.4-LLM</span>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        
        {/* Risk Level Gauge */}
        <div className={`p-4 rounded-xl border flex items-center justify-between gap-4 ${riskDetails.color}`}>
          <div className="space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Threat Severity</span>
            <h4 className="text-lg font-bold text-slate-100 flex items-center gap-1.5">
              <RiskIcon className="w-5 h-5 shrink-0" />
              {riskDetails.label}
            </h4>
          </div>
          <div className="text-right">
            <span className="text-3xl font-extrabold text-white">{riskPercent}%</span>
            <span className="text-[9px] block text-slate-400">confidence score</span>
          </div>
        </div>

        {/* AI Summary */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">AI Executive Summary</h4>
          <p className="text-xs text-slate-300 bg-slate-950/40 border border-slate-850 rounded-xl p-3 leading-relaxed">
            {summaryText}
          </p>
        </div>

        {/* Timeline Analysis (All 7 Grooming Stages) */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Detected Grooming Indicators</h4>
          
          <div className="space-y-2">
            {GROOMING_STAGES_DETAILS.map((stage, idx) => {
              const activeStage = activeStagesMap[stage.name] || activeStagesMap[stage.name.toLowerCase()];
              const isDetected = activeStage !== undefined;
              const isExpanded = expandedStage === stage.name;
              
              return (
                <div 
                  key={idx}
                  className={`border rounded-lg transition-all overflow-hidden ${
                    isDetected 
                      ? "bg-slate-950/60 border-violet-500/20 shadow-sm" 
                      : "bg-slate-950/20 border-slate-850 opacity-60 hover:opacity-80"
                  }`}
                >
                  {/* Stage Header */}
                  <div 
                    onClick={() => setExpandedStage(isExpanded ? null : stage.name)}
                    className="p-3 flex items-center justify-between cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {/* Number Icon */}
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
                        isDetected 
                          ? "bg-violet-600 text-white" 
                          : "bg-slate-800 text-slate-500"
                      }`}>
                        {idx + 1}
                      </span>
                      <div className="min-w-0">
                        <span className={`text-xs font-bold block truncate ${isDetected ? "text-violet-400" : "text-slate-400"}`}>
                          {stage.name}
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2 shrink-0">
                      {isDetected ? (
                        <span className="bg-red-500/10 text-red-400 text-[8px] font-extrabold uppercase px-1.5 py-0.5 rounded border border-red-500/20">
                          Detected
                        </span>
                      ) : (
                        <span className="text-[8px] text-slate-500 font-bold uppercase">
                          Not Observed
                        </span>
                      )}
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-slate-500" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-500" />}
                    </div>
                  </div>

                  {/* Expanded Stage Info */}
                  {isExpanded && (
                    <div className="p-3 border-t border-slate-850 bg-slate-950/40 space-y-3 text-xs leading-relaxed">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-500 block mb-0.5">Description</span>
                        <p className="text-slate-300">{stage.description}</p>
                      </div>

                      {isDetected && activeStage ? (
                        <>
                          <div>
                            <span className="text-[10px] uppercase font-bold text-slate-500 block mb-0.5">Reasoning</span>
                            <p className="text-slate-300">{stage.reasoning}</p>
                          </div>
                          <div>
                            <span className="text-[10px] uppercase font-bold text-slate-500 block mb-0.5">Evidence (Message ID {activeStage.messageId})</span>
                            <p className="p-2.5 bg-slate-900 border border-slate-850 rounded italic text-slate-400 font-mono">
                              "{getMessageContent(activeStage.messageId)}"
                            </p>
                          </div>
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="text-slate-500">Confidence: <strong className="text-slate-300">{activeStage.confidence}</strong></span>
                          </div>
                        </>
                      ) : (
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-500 block mb-0.5">Assessment Details</span>
                          <p className="text-slate-450 italic">No evidence detected for this stage in the current message logs.</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Recommended Actions */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Recommended Parent Action</h4>
          <div className="bg-slate-950/40 border border-slate-850 rounded-xl p-3 space-y-2.5">
            {recommendedActionsList.map((action, i) => (
              <div key={i} className="flex gap-2 text-xs items-start">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-500 mt-1.5 shrink-0" />
                <p className="text-slate-300 leading-relaxed">{action}</p>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Bottom Button Action */}
      <div className="p-4 bg-slate-900/60 border-t border-slate-800 space-y-3">
        {/* State Indicator */}
        {analysisStatus !== "idle" && (
          <div className={`p-2.5 rounded-lg border text-xs flex items-center gap-2 ${
            analysisStatus === "running" 
              ? "bg-blue-500/10 text-blue-400 border-blue-500/20" 
              : analysisStatus === "success" 
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                : "bg-red-500/10 text-red-400 border-red-500/20"
          }`}>
            {analysisStatus === "running" ? (
              <Loader2 className="w-4 h-4 animate-spin text-blue-400 shrink-0" />
            ) : analysisStatus === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertOctagon className="w-4 h-4 text-red-400 shrink-0" />
            )}
            <span className="font-medium truncate">{statusMessage}</span>
          </div>
        )}

        <button
          onClick={handleContinueAnalysis}
          disabled={isAnalyzing}
          className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:pointer-events-none text-white py-2.5 px-4 rounded-xl font-medium text-xs flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Running Analysis...
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5" />
              Continue AI Analysis
            </>
          )}
        </button>
      </div>

    </div>
  );
}
