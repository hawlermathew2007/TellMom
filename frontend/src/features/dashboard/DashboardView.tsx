import { AlertWithExplanation } from "../../lib/parseAlert";
import { ChildAccountResponse } from "../../apis";
import { 
  Users, 
  MessageSquare, 
  AlertTriangle, 
  ShieldAlert, 
  ArrowRight,
  TrendingUp,
  Activity
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface DashboardViewProps {
  children: ChildAccountResponse[];
  alerts: AlertWithExplanation[];
  onNavigateToAlert: (alertId: number) => void;
  onNavigateToChildren: () => void;
  onNavigateToAlertsList: () => void;
}

export default function DashboardView({
  children,
  alerts,
  onNavigateToAlert,
  onNavigateToChildren,
  onNavigateToAlertsList,
}: DashboardViewProps) {
  const totalMonitoredKids = children.length;
  
  // Calculate unique conversation servers
  const uniqueConversations = new Set(
    alerts.map((a) => `${a.platform}-${a.serverId}`)
  ).size;

  const activeAlerts = alerts.filter((a) => !a.acknowledged);
  const activeAlertsCount = activeAlerts.length;

  const highRiskAlertsCount = alerts.filter(
    (a) => !a.acknowledged && a.probability! >= 0.5
  ).length;

  // Let's assume an alert has pending messages to be analyzed if there are messages and we haven't continued analysis
  const pendingAnalysesCount = alerts.filter(
    (a) => !a.acknowledged && a.probability! > 0.3
  ).length;

  const recentAlerts = alerts.slice(0, 5);

  // Group alerts by day for a trend chart (last 7 days)
  const getAlertsTrendData = () => {
    const counts: Record<string, number> = {};
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    
    // Initialize last 7 days
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dayName = days[d.getDay()];
      counts[dayName] = 0;
    }

    alerts.forEach((alert) => {
      const date = new Date(alert.createdAt);
      const dayName = days[date.getDay()];
      if (dayName in counts) {
        counts[dayName]++;
      }
    });

    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  };

  const trendData = getAlertsTrendData();
  const maxTrendValue = Math.max(...trendData.map((d) => d.value), 1);

  // Helper for alert risk tag
  const getRiskLabel = (probability: number) => {
    if (probability >= 0.75) return { text: "Critical", bg: "bg-red-500/10 text-red-400 border-red-500/20" };
    if (probability >= 0.5) return { text: "High", bg: "bg-orange-500/10 text-orange-400 border-orange-500/20" };
    if (probability >= 0.25) return { text: "Medium", bg: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20" };
    return { text: "Low", bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" };
  };

  // Helper to find child display name
  const getChildName = (childId: number) => {
    const kid = children.find((c) => c.id === childId);
    return kid ? (kid.displayName || kid.platformUserId) : `Child #${childId}`;
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Dashboard</h1>
        <p className="text-slate-400 text-sm">Real-time status overview of child online monitoring</p>
      </div>

      {/* Grid Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Monitored Kids */}
        <div 
          onClick={onNavigateToChildren}
          className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 hover:border-slate-700/80 transition-all cursor-pointer group hover:bg-slate-900/80"
        >
          <div className="flex justify-between items-start">
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Monitored Kids</p>
              <h3 className="text-3xl font-bold text-white group-hover:text-violet-400 transition-colors">
                {totalMonitoredKids}
              </h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center text-violet-400">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs text-slate-500">
            <span>Manage accounts</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>

        {/* Conversations */}
        <div 
          onClick={onNavigateToAlertsList}
          className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 hover:border-slate-700/80 transition-all cursor-pointer group hover:bg-slate-900/80"
        >
          <div className="flex justify-between items-start">
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Monitored Servers</p>
              <h3 className="text-3xl font-bold text-white group-hover:text-blue-400 transition-colors">
                {uniqueConversations}
              </h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
              <MessageSquare className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs text-slate-500">
            <span>View all monitored chat rooms</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>

        {/* Active Alerts */}
        <div 
          onClick={onNavigateToAlertsList}
          className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 hover:border-slate-700/80 transition-all cursor-pointer group hover:bg-slate-900/80"
        >
          <div className="flex justify-between items-start">
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Alerts</p>
              <h3 className="text-3xl font-bold text-white group-hover:text-amber-400 transition-colors">
                {activeAlertsCount}
              </h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs text-slate-500">
            <span>Requires review</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>

        {/* High Risk Alerts */}
        <div 
          onClick={onNavigateToAlertsList}
          className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 hover:border-slate-700/80 transition-all cursor-pointer group hover:bg-slate-900/80"
        >
          <div className="flex justify-between items-start">
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Threats</p>
              <h3 className="text-3xl font-bold text-white group-hover:text-red-400 transition-colors">
                {highRiskAlertsCount}
              </h3>
            </div>
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${highRiskAlertsCount > 0 ? "bg-red-500/20 text-red-400 animate-pulse" : "bg-red-500/10 text-red-400"}`}>
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs text-slate-500">
            <span>High/Critical level events</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>

      {/* Main Grid Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left/Middle Column (Alert Trend Chart & Recent Alerts) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Trend Chart */}
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-5">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-violet-400" />
                <h3 className="text-sm font-semibold text-slate-200">Alert Detection Trend</h3>
              </div>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wide">Last 7 Days</span>
            </div>
            
            {/* Custom SVG Bar Chart */}
            <div className="h-48 flex items-end gap-2 px-2 relative">
              {trendData.map((d, index) => {
                const percent = (d.value / maxTrendValue) * 100;
                return (
                  <div key={index} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
                    {/* Tooltip */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute top-0 bg-slate-950/90 text-white text-[10px] py-1 px-2 rounded border border-slate-800 shadow-md">
                      {d.value} alert{d.value !== 1 ? "s" : ""}
                    </div>
                    {/* Bar */}
                    <div 
                      style={{ height: `${percent}%` }}
                      className="w-full bg-gradient-to-t from-violet-600 to-indigo-400 rounded-md hover:brightness-125 transition-all cursor-pointer min-h-[4px]"
                    />
                    {/* Label */}
                    <span className="text-[10px] font-medium text-slate-500">{d.name}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recent Alerts List */}
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-5">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold text-slate-200">Recent Detections</h3>
              <button 
                onClick={onNavigateToAlertsList}
                className="text-xs text-violet-400 hover:text-violet-300 font-medium flex items-center gap-1 hover:underline"
              >
                View all alerts
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {recentAlerts.length === 0 ? (
              <div className="text-center py-8 border border-dashed border-slate-800 rounded-lg">
                <p className="text-slate-500 text-sm">No alerts detected yet.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {recentAlerts.map((alert) => {
                  const risk = getRiskLabel(alert.probability!);
                  return (
                    <div 
                      key={alert.id} 
                      onClick={() => onNavigateToAlert(alert.id)}
                      className="py-3.5 flex items-start justify-between gap-4 cursor-pointer hover:bg-slate-900/30 px-2 rounded-lg transition-colors group"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-semibold text-slate-300 group-hover:text-violet-400 transition-colors">
                            {getChildName(alert.childAccountId)}
                          </span>
                          <span className="text-[10px] text-slate-500">•</span>
                          <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded capitalize">
                            {alert.platform}
                          </span>
                          <span className="text-[10px] text-slate-500">•</span>
                          <span className="text-[10px] text-slate-500">
                            Server: {alert.serverId}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 truncate max-w-md">
                          "{alert.messagePreview}"
                        </p>
                        <span className="text-[10px] text-slate-500 block">
                          Detected {formatDistanceToNow(new Date(alert.createdAt), { addSuffix: true })}
                        </span>
                      </div>
                      <div className="flex flex-col items-end gap-1.5 shrink-0">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${risk.bg}`}>
                          {risk.text}
                        </span>
                        {alert.acknowledged ? (
                          <span className="text-[9px] text-slate-500">Acknowledged</span>
                        ) : (
                          <span className="text-[9px] text-amber-500 animate-pulse font-medium">Action Required</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (Security Overview & Stats circular gauges) */}
        <div className="space-y-6">
          {/* Security Status Card */}
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-4 h-4 text-violet-400" />
              <h3 className="text-sm font-semibold text-slate-200">System Activity</h3>
            </div>
            
            <div className="space-y-4">
              {/* Circular Gauge */}
              <div className="flex flex-col items-center justify-center py-3">
                <div className="relative w-28 h-28 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle 
                      cx="50" cy="50" r="40" 
                      className="stroke-slate-800" 
                      strokeWidth="8" fill="transparent" 
                    />
                    <circle 
                      cx="50" cy="50" r="40" 
                      className="stroke-violet-600" 
                      strokeWidth="8" fill="transparent" 
                      strokeDasharray={251.2}
                      strokeDashoffset={251.2 - (251.2 * (activeAlertsCount > 0 ? Math.max(0, 100 - activeAlertsCount * 10) : 100)) / 100}
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center">
                    <span className="text-xl font-bold text-white">
                      {activeAlertsCount > 0 ? `${Math.max(10, 100 - activeAlertsCount * 10)}%` : "100%"}
                    </span>
                    <span className="text-[8px] uppercase tracking-wider text-slate-500">Safety Score</span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Total System Ingests</span>
                  <span className="font-semibold text-slate-200">Active</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">AI Classifier Link</span>
                  <span className="font-semibold text-emerald-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                    Connected
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Unprocessed Analysis Queue</span>
                  <span className="font-semibold text-slate-200">{pendingAnalysesCount} convo{pendingAnalysesCount !== 1 ? "s" : ""}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Connected Children Platform Overview */}
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Monitored Platforms</h3>
            {children.length === 0 ? (
              <div className="text-center py-4">
                <p className="text-xs text-slate-500">No platforms monitored.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {Array.from(new Set(children.map((c) => c.platform))).map((plat) => {
                  const kidsOnPlat = children.filter((c) => c.platform === plat);
                  const alertsOnPlat = alerts.filter((a) => a.platform === plat && !a.acknowledged).length;
                  return (
                    <div key={plat} className="flex justify-between items-center p-2 rounded-lg bg-slate-900/30 border border-slate-800/40">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                        <span className="text-xs font-semibold text-slate-300 capitalize">{plat}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] text-slate-500">
                          {kidsOnPlat.length} account{kidsOnPlat.length !== 1 ? "s" : ""}
                        </span>
                        {alertsOnPlat > 0 ? (
                          <span className="bg-red-500/10 text-red-400 text-[9px] px-1.5 py-0.5 rounded font-bold border border-red-500/20">
                            {alertsOnPlat} Active
                          </span>
                        ) : (
                          <span className="bg-emerald-500/10 text-emerald-400 text-[9px] px-1.5 py-0.5 rounded font-bold border border-emerald-500/20">
                            Safe
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
        
      </div>
    </div>
  );
}
