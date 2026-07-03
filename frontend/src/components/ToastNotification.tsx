import { useEffect } from "react";
import { X, ShieldAlert, AlertTriangle, Info, CheckCircle2 } from "lucide-react";

export interface ToastItem {
  id: string;
  type: "success" | "error" | "info" | "alert";
  title: string;
  message: string;
  alertId?: number; // link to detail page
}

interface ToastNotificationProps {
  toasts: ToastItem[];
  onClose: (id: string) => void;
  onNavigateToAlert?: (alertId: number) => void;
}

export default function ToastNotification({
  toasts,
  onClose,
  onNavigateToAlert,
}: ToastNotificationProps) {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        return (
          <ToastCard
            key={toast.id}
            toast={toast}
            onClose={() => onClose(toast.id)}
            onNavigate={onNavigateToAlert}
          />
        );
      })}
    </div>
  );
}

function ToastCard({
  toast,
  onClose,
  onNavigate,
}: {
  toast: ToastItem;
  onClose: () => void;
  onNavigate?: (alertId: number) => void;
}) {
  // Auto-dismiss after 6 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 6000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const handleCardClick = () => {
    if (toast.alertId && onNavigate) {
      onNavigate(toast.alertId);
      onClose();
    }
  };

  const getToastIcon = () => {
    switch (toast.type) {
      case "alert":
        return <ShieldAlert className="w-5 h-5 text-red-400 shrink-0" />;
      case "error":
        return <AlertTriangle className="w-5 h-5 text-orange-400 shrink-0" />;
      case "success":
        return <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />;
      default:
        return <Info className="w-5 h-5 text-blue-400 shrink-0" />;
    }
  };

  const borderClass = toast.type === "alert" 
    ? "border-red-500/25 bg-slate-900/90 text-slate-100" 
    : toast.type === "error"
      ? "border-orange-500/25 bg-slate-900/90 text-slate-100"
      : toast.type === "success"
        ? "border-emerald-500/25 bg-slate-900/90 text-slate-100"
        : "border-blue-500/25 bg-slate-900/90 text-slate-100";

  return (
    <div
      onClick={handleCardClick}
      className={`p-4 border rounded-xl shadow-2xl glass flex gap-3 items-start cursor-pointer hover:scale-[1.01] hover:brightness-110 active:scale-[0.99] transition-all pointer-events-auto ${borderClass} ${
        toast.alertId ? "cursor-pointer" : "cursor-default"
      }`}
    >
      <div className="mt-0.5">{getToastIcon()}</div>
      
      <div className="flex-1 space-y-1">
        <h4 className="text-xs font-bold text-slate-200">{toast.title}</h4>
        <p className="text-[11px] text-slate-400 leading-relaxed">{toast.message}</p>
        {toast.alertId && (
          <span className="text-[9px] font-semibold text-violet-400 hover:text-violet-300 block mt-1 hover:underline">
            Click here to view analysis details &rarr;
          </span>
        )}
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        className="text-slate-500 hover:text-slate-300 transition-colors p-0.5 rounded-md"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
