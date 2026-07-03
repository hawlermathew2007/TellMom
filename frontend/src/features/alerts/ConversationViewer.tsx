import { useState, useEffect, useRef, useMemo } from "react";
import { ChatMessageResponse } from "../../apis";
import { NewlyDetectedStage } from "../../apis/models/NewlyDetectedStage";
import { format } from "date-fns";
import { 
  Search, 
  ShieldAlert, 
  CheckCircle,
  AlertCircle,
  ArrowDown
} from "lucide-react";

interface ConversationViewerProps {
  messages: ChatMessageResponse[];
  detectedStages: NewlyDetectedStage[];
  childName: string;
  activeTab?: "chat" | "analysis";
}


const PARTICIPANT_AVATAR_BG = [
  "bg-blue-500/20 text-blue-300 border-blue-500/30",
  "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  "bg-pink-500/20 text-pink-300 border-pink-500/30",
  "bg-amber-500/20 text-amber-300 border-amber-500/30",
  "bg-rose-500/20 text-rose-300 border-rose-500/30",
  "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
];

// Hash function to map unique user IDs to a consistent index
function getUserIndex(userId: string): number {
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = userId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash);
}

export default function ConversationViewer({
  messages,
  detectedStages,
  childName,
  activeTab,
}: ConversationViewerProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [showScrollButton, setShowScrollButton] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageRefs = useRef<Record<number, HTMLDivElement | null>>({});

  // Auto-scroll to bottom on mount, messages change, or tab active
  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    // Initial scroll on mount or when messages change
    scrollToBottom("auto");
  }, [messages]);

  useEffect(() => {
    if (activeTab === "chat") {
      const timer = setTimeout(() => {
        scrollToBottom("smooth");
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [activeTab]);

  // Track scroll position to show/hide the "Scroll to Bottom" button
  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    // Show button if user has scrolled up by more than 300px from the bottom
    const isScrolledUp = scrollHeight - scrollTop - clientHeight > 300;
    setShowScrollButton(isScrolledUp);
  };

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

  // Pre-calculate message groups
  const messageGroups = useMemo(() => {
    const groups: {
      isChild: boolean;
      sender: string;
      avatarText: string;
      avatarColorClass: string;
      messages: {
        id: number;
        content: string;
        createdAt: Date;
        isSuspicious: boolean;
        suspiciousStage?: NewlyDetectedStage;
        isMatched: boolean;
      }[];
    }[] = [];

    messages.forEach((msg, idx) => {
      const isChild = msg.senderPlatformUserId === childName;
      const isSuspicious = messageIdToStageMap[msg.id] !== undefined;
      const suspiciousStage = messageIdToStageMap[msg.id];
      const isMatched = !!searchTerm.trim() && msg.content.toLowerCase().includes(searchTerm.toLowerCase());

      const prevMsg = idx > 0 ? messages[idx - 1] : null;
      const isNewGroup = 
        !prevMsg || 
        prevMsg.senderPlatformUserId !== msg.senderPlatformUserId ||
        (new Date(msg.createdAt).getTime() - new Date(prevMsg.createdAt).getTime() > 3 * 60 * 1000) ||
        getMessageDateString(prevMsg.createdAt) !== getMessageDateString(msg.createdAt);

      const msgData = {
        id: msg.id,
        content: msg.content,
        createdAt: msg.createdAt,
        isSuspicious,
        suspiciousStage,
        isMatched,
      };

      if (isNewGroup) {
        const userIdx = getUserIndex(msg.senderPlatformUserId);
        const avatarColorClass = isChild 
          ? "bg-violet-500/20 text-violet-300 border-violet-500/30" 
          : PARTICIPANT_AVATAR_BG[userIdx % PARTICIPANT_AVATAR_BG.length];
        
        groups.push({
          isChild,
          sender: msg.senderPlatformUserId,
          avatarText: msg.senderPlatformUserId.substring(0, 2).toUpperCase(),
          avatarColorClass,
          messages: [msgData],
        });
      } else {
        groups[groups.length - 1].messages.push(msgData);
      }
    });

    return groups;
  }, [messages, childName, searchTerm, messageIdToStageMap]);

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-inner relative">
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
              className="px-2 py-1 bg-slate-900 border border-slate-850 hover:bg-slate-800 rounded text-[10px] font-medium text-slate-300 transition-colors"
            >
              Oldest
            </button>
          )}
          {jumpTargets.firstSuspicious && (
            <button
              onClick={() => jumpToMessage(jumpTargets.firstSuspicious!)}
              className="px-2 py-1 bg-rose-950/20 border border-rose-900/35 hover:bg-rose-950/45 text-rose-300 rounded text-[10px] font-semibold flex items-center gap-1 transition-colors"
            >
              <ShieldAlert className="w-3 h-3 text-rose-400" />
              1st Flagged
            </button>
          )}
          {jumpTargets.highestRisk && (
            <button
              onClick={() => jumpToMessage(jumpTargets.highestRisk!)}
              className="px-2 py-1 bg-red-950/20 border border-red-900/35 hover:bg-red-950/45 text-red-300 rounded text-[10px] font-semibold flex items-center gap-1 transition-colors"
            >
              <AlertCircle className="w-3 h-3 text-red-400" />
              Highest Risk
            </button>
          )}
          {jumpTargets.newest && (
            <button
              onClick={() => jumpToMessage(jumpTargets.newest!)}
              className="px-2 py-1 bg-slate-900 border border-slate-850 hover:bg-slate-800 rounded text-[10px] font-medium text-slate-300 transition-colors"
            >
              Newest
            </button>
          )}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div 
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent"
      >
        {messageGroups.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600 text-xs">
            No messages found in this stream.
          </div>
        ) : (
          messageGroups.map((group, groupIdx) => {
            const firstMsg = group.messages[0];
            const showDateSeparator = 
              groupIdx === 0 || 
              getMessageDateString(messageGroups[groupIdx - 1].messages[0].createdAt) !== getMessageDateString(firstMsg.createdAt);

            return (
              <div key={`group-${groupIdx}`} className="space-y-3">
                {/* Date separator */}
                {showDateSeparator && (
                  <div className="flex items-center justify-center my-6">
                    <span className="text-[10px] font-bold text-slate-400 bg-slate-900 border border-slate-800 px-3.5 py-1 rounded-full shadow-sm">
                      {getMessageDateString(firstMsg.createdAt)}
                    </span>
                  </div>
                )}

                {/* Message Group */}
                <div className={`flex gap-3 max-w-[85%] ${group.isChild ? "ml-auto flex-row-reverse" : "mr-auto"}`}>
                  {/* Avatar */}
                  <div className={`w-8 h-8 rounded-full border flex items-center justify-center text-[10px] font-bold shrink-0 self-end shadow-md ${group.avatarColorClass}`}>
                    {group.avatarText}
                  </div>

                  {/* Bubbles Stack */}
                  <div className={`flex flex-col gap-1.5 w-full ${group.isChild ? "items-end" : "items-start"}`}>
                    {/* Sender Name (only once per group) */}
                    <div className="flex items-center gap-2 px-1 text-[10px] text-slate-400">
                      <span className="font-semibold text-slate-300">{group.sender}</span>
                      {group.isChild && (
                        <span className="text-[9px] bg-violet-500/10 text-violet-400 border border-violet-500/20 px-1 py-0.2 rounded">
                          Monitored
                        </span>
                      )}
                    </div>

                    {group.messages.map((msg, msgIdx) => {
                      const isFirst = msgIdx === 0;
                      const isLast = msgIdx === group.messages.length - 1;
                      
                      // Dynamic rounding for speech bubbles
                      const roundingClass = group.isChild
                        ? `${isFirst ? "rounded-tl-2xl rounded-tr-2xl" : "rounded-tl-2xl"} ${isLast ? "rounded-bl-2xl rounded-br-sm" : "rounded-bl-2xl"} rounded-r-sm`
                        : `${isFirst ? "rounded-tl-2xl rounded-tr-2xl" : "rounded-tr-2xl"} ${isLast ? "rounded-br-2xl rounded-bl-sm" : "rounded-br-2xl"} rounded-l-sm`;

                      const highlightClass = msg.isSuspicious 
                        ? "ring-2 ring-red-500/50 bg-red-950/20 border-red-500/30" 
                        : msg.isMatched 
                          ? "ring-2 ring-yellow-500/50 bg-yellow-950/20 border-yellow-500/30"
                          : group.isChild
                            ? "bg-violet-600 text-white border-transparent hover:bg-violet-550"
                            : "bg-slate-900 text-slate-100 border-slate-800 hover:bg-slate-850";

                      return (
                        <div 
                          key={msg.id}
                          ref={(el) => { messageRefs.current[msg.id] = el; }}
                          className={`group/message relative flex flex-col max-w-full transition-all duration-200`}
                        >
                          <div className={`p-3 text-sm select-text whitespace-pre-wrap break-words border shadow-sm ${roundingClass} ${highlightClass}`}>
                            {renderHighlightedContent(msg.content, searchTerm)}
                            
                            {/* Timestamp overlay (shown on hover or subtle inline) */}
                            <div className={`text-[9px] mt-1 text-right block ${group.isChild ? "text-violet-200/70" : "text-slate-400/70"}`}>
                              {format(new Date(msg.createdAt), "h:mm a")}
                              <CheckCircle className="w-2.5 h-2.5 inline-block ml-1 opacity-70" />
                            </div>
                          </div>

                          {/* Suspicious Stage label directly under the flagged bubble */}
                          {msg.isSuspicious && msg.suspiciousStage && (
                            <div className="mt-1 flex items-center gap-1.5 bg-red-950/40 border border-red-900/30 text-red-400 text-[10px] font-semibold py-1 px-2.5 rounded-lg w-fit">
                              <ShieldAlert className="w-3.5 h-3.5 shrink-0 text-red-500 animate-pulse" />
                              <span>Grooming Trigger: {msg.suspiciousStage.stage} ({msg.suspiciousStage.confidence} Confidence)</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Floating Scroll to Bottom Button */}
      {showScrollButton && (
        <button
          onClick={() => scrollToBottom("smooth")}
          className="absolute bottom-4 right-4 p-2 bg-violet-600 hover:bg-violet-500 text-white rounded-full shadow-lg border border-violet-500/20 transition-all active:scale-95 animate-bounce z-20"
          title="Scroll to bottom"
        >
          <ArrowDown className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
