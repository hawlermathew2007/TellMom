import { AlertCircle, RefreshCw, Archive } from "lucide-react";

// Standard Shimmer effect skeleton
export function SkeletonCard() {
  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 space-y-4 animate-pulse">
      <div className="flex justify-between items-start">
        <div className="space-y-3 w-2/3">
          <div className="h-3.5 bg-slate-800 rounded w-1/2" />
          <div className="h-7 bg-slate-800 rounded w-1/3" />
        </div>
        <div className="w-10 h-10 rounded bg-slate-800" />
      </div>
      <div className="h-3 bg-slate-800 rounded w-2/3 mt-2" />
    </div>
  );
}

export function SkeletonTable() {
  return (
    <div className="space-y-3 animate-pulse">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="p-4 bg-slate-950/40 border border-slate-900 rounded-xl flex items-center justify-between">
          <div className="space-y-2 flex-1">
            <div className="h-4 bg-slate-900 rounded w-1/4" />
            <div className="h-3 bg-slate-900 rounded w-1/2" />
          </div>
          <div className="h-6 bg-slate-900 rounded w-16" />
        </div>
      ))}
    </div>
  );
}

export function LoadingSpinner() {
  return (
    <div className="min-h-[300px] flex flex-col items-center justify-center space-y-2">
      <RefreshCw className="w-8 h-8 text-violet-500 animate-spin" />
      <p className="text-slate-500 text-xs font-semibold">Loading data...</p>
    </div>
  );
}

// Error state helper with retry action
export function ErrorFallback({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="min-h-[300px] flex flex-col items-center justify-center p-8 bg-red-950/10 border border-red-900/30 rounded-xl text-center space-y-4 max-w-md mx-auto my-12">
      <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center text-red-400">
        <AlertCircle className="w-6 h-6" />
      </div>
      <div className="space-y-1">
        <h4 className="text-sm font-bold text-slate-200">Request Failed</h4>
        <p className="text-xs text-slate-400 leading-relaxed">{message}</p>
      </div>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 active:scale-[0.98] mx-auto"
      >
        <RefreshCw className="w-3.5 h-3.5" />
        Retry Connection
      </button>
    </div>
  );
}

// Custom Empty states
export function EmptyState({ 
  title = "No items found", 
  description = "No items matched the current logs.",
  icon = <Archive className="w-5 h-5" />
}) {
  return (
    <div className="p-16 border border-dashed border-slate-800 rounded-xl text-center space-y-3">
      <div className="w-12 h-12 rounded-full bg-slate-900/80 border border-slate-850 flex items-center justify-center mx-auto text-slate-500">
        {icon}
      </div>
      <h4 className="text-slate-400 text-sm font-semibold">{title}</h4>
      <p className="text-slate-650 text-xs max-w-sm mx-auto leading-relaxed">{description}</p>
    </div>
  );
}
