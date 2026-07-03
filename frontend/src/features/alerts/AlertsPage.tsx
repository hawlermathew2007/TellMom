import React, { useState, useMemo } from "react";
import { AlertWithExplanation } from "../../lib/parseAlert";
import { ChildAccountResponse } from "../../apis";
import { formatDistanceToNow, format } from "date-fns";
import { 
  Search, 
  Filter, 
  ChevronDown, 
  Check, 
  ChevronRight, 
  MessageSquare,
  Volume2,
  Bell,
  ArrowUpDown,
  AlertTriangle,
  ChevronLeft
} from "lucide-react";

interface AlertsPageProps {
  alerts: AlertWithExplanation[];
  children: ChildAccountResponse[];
  onSelectAlert: (alertId: number) => void;
  onAcknowledgeAlert: (alertId: number) => Promise<void>;
}

type SortField = "date" | "risk";
type SortOrder = "asc" | "desc";

export default function AlertsPage({
  alerts,
  children,
  onSelectAlert,
  onAcknowledgeAlert,
}: AlertsPageProps) {
  // Filters & Search
  const [searchTerm, setSearchTerm] = useState("");
  const [platformFilter, setPlatformFilter] = useState<string>("all");
  const [childFilter, setChildFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  
  // Sorting
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  // Resolve child display name
  const getChildName = (childId: number) => {
    const kid = children.find((c) => c.id === childId);
    return kid ? (kid.displayName || kid.platformUserId) : `Child #${childId}`;
  };

  // Helper for alert risk mapping
  const getRiskDetails = (probability: number) => {
    if (probability >= 0.75) {
      return { 
        text: "Critical", 
        colorClass: "bg-red-500/10 text-red-400 border-red-500/20",
        indicatorClass: "bg-red-500"
      };
    }
    if (probability >= 0.5) {
      return { 
        text: "High", 
        colorClass: "bg-orange-500/10 text-orange-400 border-orange-500/20",
        indicatorClass: "bg-orange-500"
      };
    }
    if (probability >= 0.25) {
      return { 
        text: "Medium", 
        colorClass: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
        indicatorClass: "bg-yellow-500"
      };
    }
    return { 
      text: "Low", 
      colorClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      indicatorClass: "bg-emerald-500"
    };
  };

  // Get risk severity category as string
  const getSeverityCategory = (probability: number) => {
    if (probability >= 0.75) return "critical";
    if (probability >= 0.5) return "high";
    if (probability >= 0.25) return "medium";
    return "low";
  };

  // Filtered & Sorted Alerts
  const processedAlerts = useMemo(() => {
    return alerts
      .filter((alert) => {
        // Search
        const childName = getChildName(alert.childAccountId).toLowerCase();
        const searchMatches = 
          alert.messagePreview.toLowerCase().includes(searchTerm.toLowerCase()) ||
          alert.serverId.toLowerCase().includes(searchTerm.toLowerCase()) ||
          childName.includes(searchTerm.toLowerCase());

        // Platform filter
        const platformMatches = platformFilter === "all" || alert.platform === platformFilter;

        // Child filter
        const childMatches = childFilter === "all" || String(alert.childAccountId) === childFilter;

        // Severity filter
        const severityMatches = severityFilter === "all" || getSeverityCategory(alert.probability) === severityFilter;

        // Status filter
        const statusMatches = 
          statusFilter === "all" || 
          (statusFilter === "acknowledged" && alert.acknowledged) ||
          (statusFilter === "active" && !alert.acknowledged);

        return searchMatches && platformMatches && childMatches && severityMatches && statusMatches;
      })
      .sort((a, b) => {
        let comparison = 0;
        if (sortField === "date") {
          comparison = new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        } else if (sortField === "risk") {
          comparison = b.probability - a.probability;
        }
        return sortOrder === "desc" ? comparison : -comparison;
      });
  }, [alerts, searchTerm, platformFilter, childFilter, severityFilter, statusFilter, sortField, sortOrder, children]);

  // Paginated Alerts
  const totalPages = Math.max(Math.ceil(processedAlerts.length / itemsPerPage), 1);
  
  // Adjust current page if filters shrink list below current index
  const safeCurrentPage = Math.min(currentPage, totalPages);
  
  const paginatedAlerts = useMemo(() => {
    const startIdx = (safeCurrentPage - 1) * itemsPerPage;
    return processedAlerts.slice(startIdx, startIdx + itemsPerPage);
  }, [processedAlerts, safeCurrentPage]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "desc" ? "asc" : "desc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Security Alerts</h1>
          <p className="text-slate-400 text-sm">Monitor flag events, view grooming analysis, and review conversations</p>
        </div>
        <div className="text-xs text-slate-500 font-medium">
          Showing {processedAlerts.length} filtered event{processedAlerts.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 bg-slate-900/40 border border-slate-800/80 rounded-xl p-4">
        {/* Search */}
        <div className="relative md:col-span-2">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search by child, message content, or server ID..."
            className="w-full bg-slate-950 border border-slate-850 rounded-lg py-2 pl-9 pr-4 text-xs text-slate-200 placeholder:text-slate-700 focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500 transition-all"
          />
        </div>

        {/* Platform Filter */}
        <div>
          <select
            value={platformFilter}
            onChange={(e) => {
              setPlatformFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full bg-slate-950 border border-slate-850 rounded-lg py-2 px-3 text-xs text-slate-400 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all capitalize"
          >
            <option value="all">All Platforms</option>
            <option value="roblox">Roblox</option>
            <option value="discord">Discord</option>
            <option value="minecraft">Minecraft</option>
          </select>
        </div>

        {/* Child Filter */}
        <div>
          <select
            value={childFilter}
            onChange={(e) => {
              setChildFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full bg-slate-950 border border-slate-850 rounded-lg py-2 px-3 text-xs text-slate-400 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all"
          >
            <option value="all">All Children</option>
            {children.map((c) => (
              <option key={c.id} value={c.id}>
                {c.displayName || c.platformUserId}
              </option>
            ))}
          </select>
        </div>

        {/* Severity Filter */}
        <div>
          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full bg-slate-950 border border-slate-850 rounded-lg py-2 px-3 text-xs text-slate-400 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Sort Buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => toggleSort("date")}
          className={`px-3 py-1.5 rounded-lg border text-xs flex items-center gap-1.5 transition-all ${
            sortField === "date"
              ? "bg-violet-600/10 text-violet-400 border-violet-500/30"
              : "bg-slate-900/30 text-slate-400 border-slate-800 hover:text-slate-200"
          }`}
        >
          Sort by Date {sortField === "date" && (sortOrder === "desc" ? "↓" : "↑")}
        </button>
        <button
          onClick={() => toggleSort("risk")}
          className={`px-3 py-1.5 rounded-lg border text-xs flex items-center gap-1.5 transition-all ${
            sortField === "risk"
              ? "bg-violet-600/10 text-violet-400 border-violet-500/30"
              : "bg-slate-900/30 text-slate-400 border-slate-800 hover:text-slate-200"
          }`}
        >
          Sort by Risk Score {sortField === "risk" && (sortOrder === "desc" ? "↓" : "↑")}
        </button>
        <button
          onClick={() => {
            setStatusFilter(statusFilter === "active" ? "all" : "active");
            setCurrentPage(1);
          }}
          className={`px-3 py-1.5 rounded-lg border text-xs flex items-center gap-1.5 transition-all ml-auto ${
            statusFilter === "active"
              ? "bg-amber-600/15 text-amber-400 border-amber-500/35"
              : "bg-slate-900/30 text-slate-400 border-slate-800 hover:text-slate-200"
          }`}
        >
          Show Active Only
        </button>
      </div>

      {/* Alerts Table / List */}
      {processedAlerts.length === 0 ? (
        <div className="bg-slate-900/20 border border-slate-800/80 rounded-xl p-16 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center mx-auto border border-slate-800 text-slate-600">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <p className="text-slate-400 text-sm font-semibold">No alerts found</p>
          <p className="text-slate-600 text-xs max-w-sm mx-auto">
            Try adjusting your search criteria, clearing filters, or checking other child accounts.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3">
            {paginatedAlerts.map((alert) => {
              const risk = getRiskDetails(alert.probability);
              const processedCount = alert.messages ? alert.messages.length : 0;
              const hasAnalysis = alert.detectedStages.length > 0;

              return (
                <div
                  key={alert.id}
                  className={`p-4 rounded-xl border bg-slate-950/40 hover:bg-slate-950/80 hover:border-slate-700/60 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer group ${
                    alert.acknowledged ? "border-slate-850 opacity-60" : "border-slate-800"
                  }`}
                  onClick={() => onSelectAlert(alert.id)}
                >
                  {/* Left Side: Child Name & Message preview */}
                  <div className="space-y-2 min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      {/* Risk colored indicator */}
                      <span className={`w-2 h-2 rounded-full ${risk.indicatorClass} shrink-0`} />
                      
                      <span className="text-sm font-semibold text-slate-200 group-hover:text-violet-400 transition-colors">
                        {getChildName(alert.childAccountId)}
                      </span>
                      
                      <span className="text-[10px] text-slate-600">•</span>
                      
                      <span className="text-[10px] text-slate-400 capitalize bg-slate-900 border border-slate-850 px-1.5 py-0.5 rounded font-mono">
                        {alert.platform}
                      </span>
                      
                      <span className="text-[10px] text-slate-600">•</span>
                      
                      <span className="text-[10px] text-slate-500 font-mono">
                        Server: {alert.serverId}
                      </span>

                      {hasAnalysis && (
                        <>
                          <span className="text-[10px] text-slate-600">•</span>
                          <span className="text-[9px] bg-violet-600/10 text-violet-400 border border-violet-500/20 px-1.5 py-0.5 rounded font-semibold">
                            AI Analyzed ({alert.detectedStages.length} stages)
                          </span>
                        </>
                      )}
                    </div>
                    
                    <p className="text-xs text-slate-400 italic line-clamp-2 max-w-2xl pr-4">
                      "{alert.messagePreview}"
                    </p>
                    
                    <div className="flex gap-4 text-[10px] text-slate-500">
                      <span>Detected {formatDistanceToNow(new Date(alert.createdAt), { addSuffix: true })}</span>
                      <span>•</span>
                      <span>Last updated {format(new Date(alert.createdAt), "MMM d, h:mm a")}</span>
                      <span>•</span>
                      <span>{processedCount} message{processedCount !== 1 ? "s" : ""} in stream</span>
                    </div>
                  </div>

                  {/* Right Side: Severity & Quick action */}
                  <div className="flex md:flex-col items-center md:items-end justify-between md:justify-center gap-3 shrink-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${risk.colorClass}`}>
                        {risk.text} ({Math.round(alert.probability * 100)}%)
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {!alert.acknowledged ? (
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            await onAcknowledgeAlert(alert.id);
                          }}
                          className="px-2.5 py-1 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10 rounded-lg transition-all flex items-center gap-1 active:scale-[0.98]"
                        >
                          <Check className="w-3 h-3" />
                          Acknowledge
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-500 font-medium px-2">Acknowledged</span>
                      )}

                      <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 group-hover:translate-x-0.5 transition-all" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center py-4 border-t border-slate-900 text-xs">
              <span className="text-slate-500">
                Page {safeCurrentPage} of {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={safeCurrentPage === 1}
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  className="p-2 border border-slate-800 rounded-lg hover:bg-slate-900 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
                >
                  <ChevronLeft className="w-4 h-4 text-slate-400" />
                </button>
                <button
                  disabled={safeCurrentPage === totalPages}
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  className="p-2 border border-slate-800 rounded-lg hover:bg-slate-900 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
                >
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
