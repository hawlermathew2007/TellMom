import { useState, useEffect, useRef, useMemo } from "react";
import { ChatMessageResponse } from "../../apis";
import { NewlyDetectedStage } from "../../apis/models/NewlyDetectedStage";
import { format } from "date-fns";
import { 
  Search, 
  ShieldAlert, 
  CheckCircle,
  AlertCircle
} from "lucide-react";

interface ConversationViewerProps {
  messages: ChatMessageResponse[];
  detectedStages: NewlyDetectedStage[];
  childName: string;
}

const PARTICIPANT_COLORS = [
  "bg-blue-600/15 border-blue-500/30 text-blue-200",
  "bg-emerald-600/15 border-emerald-500/30 text-emerald-200",
  "bg-violet-600/15 border-violet-500/30 text-violet-200",
  "bg-amber-600/15 border-amber-500/30 text-amber-200",
  "bg-rose-600/15 border-rose-500/30 text-rose-200",
  "bg-cyan-600/15 border-cyan-500/30 text-cyan-200",
];

// Hash function to map unique user IDs to a consistent color style index
function getUserColorClass(userId: string): string {
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = userId.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % PARTICIPANT_COLORS.length;
  return PARTICIPANT_COLORS[index];
}

export default function ConversationViewer({
  messages,
  detectedStages,
  childName,
}: ConversationViewerProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageRefs = useRef<Record<number, HTMLDivElement | null>>({});

  // Auto-scroll to bottom on mount or messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Map messages to their evidence stage if any
  const messageIdToStageMap = useMemo(() => {
    const map: Record<number, NewlyDetectedStage> = {};
    detectedStages.forEach((stage) => {
      map[stage.messageId] = stage;
    });
    return map;
  }, [detectedStages]);

  // Jump to specific message
  const jumpToMessage = (messageId: number) => {
    const el = messageRefs.current[messageId];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("ring-2", "ring-violet-500", "scale-[1.01]");
      setTimeout(() => {
        el.classList.remove("ring-2", "ring-violet-500", "scale-[1.01]");
      }, 2000);
    }
  };

  // Find Timeline Jump targets
  const jumpTargets = useMemo(() => {
    const suspiciousIds = detectedStages.map(s => s.messageId).filter(id => id > 0);
    const sortedSuspiciousIds = [...suspiciousIds].sort((a, b) => a - b);
    
    // Find highest risk target based on stage ordering
    const stageOrder = [
      "Victim Selection",
      "Access and Relationship Building",
      "Trust Development",
      "Isolation",
      "Boundary Testing",
      "Desensitization",
      "Maintaining Control"
    ];
    let highestRiskMsgId: number | null = null;
    let highestRiskIndex = -1;

    detectedStages.forEach(s => {
      const idx = stageOrder.indexOf(s.stage);
      if (idx > highestRiskIndex) {
        highestRiskIndex = idx;
        highestRiskMsgId = s.messageId;
      }
    });

    return {
      firstSuspicious: sortedSuspiciousIds[0] || null,
      newest: messages[messages.length - 1]?.id || null,
      oldest: messages[0]?.id || null,
      highestRisk: highestRiskMsgId,
    };
  }, [messages, detectedStages]);

  // Helper to format sticky date
  const getMessageDateString = (date: Date) => {
    return format(new Date(date), "MMMM d, yyyy");
  };

  // Helper to highlight matching text in message
  const renderHighlightedContent = (content: string, search: string) => {
    if (!search.trim()) return content;
    const parts = content.split(new RegExp(`(${search})`, "gi"));
    return (
      <>
        {parts.map((part, i) => 
          part.toLowerCase() === search.toLowerCase() ? (
            <mark key={i} className="bg-yellow-500/35 text-white font-semibold rounded px-0.5">
              {part}
            </mark>
          ) : (
            part
          )
        )}
      </>
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-inner">
      {/* Top Search & Jump Bar */}
      <div className="p-3 bg-slate-900/60 border-b border-slate-800 flex flex-col sm:flex-row gap-3 items-center justify-between">
        
        {/* Chat Search */}
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search conversation..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder:text-slate-700 focus:outline-none focus:ring-1 focus:ring-violet-500/40"
          />
        </div>

        {/* Jump Controls */}
        <div className="flex items-center gap-1.5 flex-wrap self-end sm:self-center">
          <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mr-1">Jump to:</span>
          {jumpTargets.oldest && (
            <button
              onClick={() => jumpToMessage(jumpTargets.oldest!)}
              className="px-2 py-1 bg-slate-900 border border-slate-850 hover:bg-slate-800 rounded text-[10px] font-medium text-slate-300"
            >
              Oldest
            </button>
          )}
          {jumpTargets.firstSuspicious && (
            <button
              onClick={() => jumpToMessage(jumpTargets.firstSuspicious!)}
              className="px-2 py-1 bg-rose-950/20 border border-rose-900/35 hover:bg-rose-950/45 text-rose-300 rounded text-[10px] font-semibold flex items-center gap-1"
            >
              <ShieldAlert className="w-3 h-3 text-rose-400" />
              1st Flagged
            </button>
          )}
          {jumpTargets.highestRisk && (
            <button
              onClick={() => jumpToMessage(jumpTargets.highestRisk!)}
              className="px-2 py-1 bg-red-950/20 border border-red-900/35 hover:bg-red-950/45 text-red-300 rounded text-[10px] font-semibold flex items-center gap-1"
            >
              <AlertCircle className="w-3 h-3 text-red-400" />
              Highest Risk
            </button>
          )}
          {jumpTargets.newest && (
            <button
              onClick={() => jumpToMessage(jumpTargets.newest!)}
              className="px-2 py-1 bg-slate-900 border border-slate-850 hover:bg-slate-800 rounded text-[10px] font-medium text-slate-300"
            >
              Newest
            </button>
          )}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600 text-xs">
            No messages found in this stream.
          </div>
        ) : (
          messages.map((msg, index) => {
            const isSuspicious = messageIdToStageMap[msg.id] !== undefined;
            const suspiciousStage = messageIdToStageMap[msg.id];
            
            // Check if search matches
            const isMatched = searchTerm.trim() && msg.content.toLowerCase().includes(searchTerm.toLowerCase());

            // Sticky date separator logic
            const showDateSeparator = 
              index === 0 || 
              getMessageDateString(messages[index - 1].createdAt) !== getMessageDateString(msg.createdAt);

            const senderColorClass = getUserColorClass(msg.senderPlatformUserId);
            
            // Highlight styling if suspicious or matched search
            const highlightClass = isSuspicious 
              ? "ring-2 ring-red-500/40 bg-red-950/10 border-red-900/20" 
              : isMatched 
                ? "ring-1 ring-yellow-500/50 bg-yellow-950/10 border-yellow-900/20"
                : "";

            // Message processing indicator (all historical messages in database are already processed by definition)
            // const isProcessed = true; // In alerts view, they are all processed database alerts

            return (
              <div key={msg.id} className="space-y-2">
                {/* Date separator */}
                {showDateSeparator && (
                  <div className="flex items-center justify-center my-4">
                    <span className="text-[10px] font-bold text-slate-500 bg-slate-900 border border-slate-850 px-3 py-1 rounded-full shadow-sm sticky top-0 z-10">
                      {getMessageDateString(msg.createdAt)}
                    </span>
                  </div>
                )}

                {/* Chat Bubble container */}
                <div 
                  ref={(el) => { messageRefs.current[msg.id] = el; }}
                  className={`flex flex-col gap-1 p-2.5 rounded-xl border border-transparent transition-all max-w-[85%] ${
                    msg.senderPlatformUserId === childName 
                      ? "ml-auto items-end bg-slate-900/35" 
                      : "mr-auto items-start bg-slate-900/75"
                  } ${highlightClass}`}
                >
                  {/* Sender & Timestamp */}
                  <div className="flex items-center gap-2 text-[10px] text-slate-400">
                    <span className="font-semibold text-slate-300">{msg.senderPlatformUserId}</span>
                    <span>•</span>
                    <span>{format(new Date(msg.createdAt), "h:mm a")}</span>
                    
                    {/* Message processed Badge */}
                    <div className="relative group/badge">
                      <span className="text-emerald-500 cursor-help" title="Processed by AI analysis">
                        <CheckCircle className="w-3 h-3 inline-block" />
                      </span>
                    </div>
                  </div>

                  {/* Bubble content */}
                  <div className={`mt-1 p-3 rounded-lg border text-sm select-text whitespace-pre-wrap break-words w-full ${senderColorClass}`}>
                    {renderHighlightedContent(msg.content, searchTerm)}
                  </div>

                  {/* Suspicious Stage tag inside bubble */}
                  {isSuspicious && suspiciousStage && (
                    <div className="mt-2 flex items-center gap-1 bg-red-950/40 border border-red-900/30 text-red-400 text-[10px] font-semibold py-1 px-2.5 rounded-lg">
                      <ShieldAlert className="w-3.5 h-3.5 shrink-0 text-red-500 animate-pulse" />
                      <span>Grooming Trigger: {suspiciousStage.stage} ({suspiciousStage.confidence} Confidence)</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
