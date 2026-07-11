import { useState, useEffect, useCallback, useRef } from "react";
import { getApis, getToken, clearToken, fetchAlerts, acknowledgeAlertWithExplanation } from "./apis/client";
import { ParentResponse, ChildAccountResponse } from "./apis";
import { AlertWithExplanation, parseAlert } from "./lib/parseAlert";
import { useSettings } from "./hooks/useSettings";
import { playAlertSound } from "./lib/sound";

// Component imports
import Sidebar from "./components/Sidebar";
import DashboardView from "./features/dashboard/DashboardView";
import AlertsPage from "./features/alerts/AlertsPage";
import AlertDetailView from "./features/alerts/AlertDetailView";
import ChildrenManagement from "./features/children/ChildrenManagement";
import TestChatRoom from "./features/debug/TestChatRoom";
import SettingsView from "./components/SettingsView";
import AuthPage from "./features/auth/AuthPage";
import ToastNotification, { ToastItem } from "./components/ToastNotification";
import { LoadingSpinner, ErrorFallback } from "./components/SkeletonLoader";

export default function App() {
    // Session & Authentication
    const [token, setTokenState] = useState<string | null>(getToken());
    const [parent, setParent] = useState<ParentResponse | null>(null);
    const [children, setChildren] = useState<ChildAccountResponse[]>([]);
    const [alerts, setAlerts] = useState<AlertWithExplanation[]>([]);

    // Navigation & UI States
    const [activeView, setActiveView] = useState<string>("dashboard"); // dashboard, alerts, children, debug, settings, or alert-{id}
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");

    // Custom Toasts array
    const [toasts, setToasts] = useState<ToastItem[]>([]);

    // Settings Context Hook
    const { settings, updateSetting } = useSettings();
    const socketRef = useRef<WebSocket | null>(null);

    // Helper to add toast notifications
    const addToast = useCallback((type: "success" | "error" | "info" | "alert", title: string, message: string, alertId?: number) => {
        setToasts((prev) => {
            const existingIndex = prev.findIndex((t) =>
                alertId !== undefined ? t.alertId === alertId : t.title === title
            );
            if (existingIndex > -1) {
                const updated = [...prev];
                updated[existingIndex] = {
                    ...updated[existingIndex],
                    type,
                    title,
                    message,
                    alertId
                };
                return updated;
            } else {
                const id = Math.random().toString(36).substring(2, 9);
                return [...prev, { id, type, title, message, alertId }];
            }
        });
    }, []);

    const closeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    // Fetch Dashboard core data from API
    const loadDashboardData = useCallback(async () => {
        if (!token) return;
        setIsLoading(true);
        setError("");

        try {
            const apis = getApis();
            const [me, kids, alertLogs] = await Promise.all([
                apis.auth.getMeApiAuthMeGet(),
                apis.children.listChildrenApiChildrenGet(),
                fetchAlerts(),
            ]);

            setParent(me);
            setChildren(kids);
            setAlerts(alertLogs);
        } catch (err: any) {
            setError("Failed to communicate with TellMom backend. Ensure backend is running.");
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    }, [token]);

    // Load profile/data on initial sign-in
    useEffect(() => {
        if (token) {
            loadDashboardData();
        }
    }, [token, loadDashboardData]);

    // Handle WebSocket Connection
    useEffect(() => {
        if (!token) return;
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        // const wsUrl = `${protocol}://${window.location.host}/api/alerts/ws?token=${encodeURIComponent(token)}`;
        const wsUrl = `${protocol}://45.151.155.170:8000/api/alerts/ws`;

        const connectSocket = () => {
            let hasAuthenticated = false
            const ws = new WebSocket(wsUrl);
            socketRef.current = ws;

            ws.onopen = () => {
                ws.send(JSON.stringify({ type: "auth", token }));
            }

            // First message will be used as "auth tag"
            ws.onmessage = (event) => {
                let data: any;
                try {
                    data = JSON.parse(event.data);
                } catch {
                    console.error("Failed to parse message", event.data);
                    return;
                }

                if (!hasAuthenticated) {
                    if (data.type === "auth_ok") {
                        hasAuthenticated = true;
                        console.log("WebSocket stream authenticated");
                    } else {
                        console.error("Expected auth_ok, got:", data);
                        ws.close();
                    }
                    return;
                }
            }

            ws.onmessage = (event) => {
                if (isCancelled) return;
                try {
                    const raw = JSON.parse(event.data);

                    // Check if payload is an alert notification
                    if (raw.type === "alert" || raw.id !== undefined) {
                        const newAlert = parseAlert(raw);

                        // Play notification audio ping
                        if (settings.soundEnabled) {
                            playAlertSound(settings.soundVolume);
                        }

                        // Find child display name
                        const kid = children.find(c => c.id === newAlert.childAccountId);
                        const kidName = kid ? (kid.displayName || kid.platformUserId) : `Child #${newAlert.childAccountId}`;

                        // Add Toast Alert banner (clicking opens alert details)
                        addToast(
                            "alert",
                            `Security Alert: ${kidName}`,
                            `Threat detected on ${newAlert.platform} server "${newAlert.serverId}": "${newAlert.messagePreview}"`,
                            newAlert.id
                        );

                        // Trigger OS Notification if enabled
                        if (settings.desktopNotifications && Notification.permission === "granted") {
                            const notification = new Notification(`TellMom: Alert on ${newAlert.platform}`, {
                                body: `Suspicious activity detected for ${kidName}: "${newAlert.messagePreview}"`,
                                icon: "/favicon.ico"
                            });
                            notification.onclick = () => {
                                window.focus();
                                handleNavigateToAlert(newAlert.id);
                            };
                        }

                        // Update local alerts log (prepend new alert or update if exists)
                        setAlerts((prev) => {
                            if (prev.some((a) => a.id === newAlert.id)) {
                                return prev.map((a) => (a.id === newAlert.id ? newAlert : a));
                            }
                            return [newAlert, ...prev];
                        });
                    }
                } catch (err) {
                    console.error("Failed to parse WebSocket alert payload", err);
                }
            };

            ws.onclose = () => {
                if (isCancelled) return;
                console.warn("TellMom WebSocket alert socket disconnected. Retrying in 5 seconds...");
                setTimeout(() => {
                    if (!isCancelled && getToken()) connectSocket();
                }, 5000);
            };

            ws.onerror = (err) => {
                console.error("WebSocket encountered an error", err);
            };
        };

        connectSocket();

        return () => {
            isCancelled = true;
            if (socketRef.current) {
                socketRef.current.close();
            }
        };
    }, [token, children, settings.soundEnabled, settings.soundVolume, settings.desktopNotifications, addToast]);

    // Fallback Polling Interval if enabled
    useEffect(() => {
        if (!token || settings.autoRefreshInterval <= 0) return;

        const interval = setInterval(async () => {
            try {
                const freshAlerts = await fetchAlerts();
                setAlerts(freshAlerts);
            } catch (err) {
                console.warn("Polling alerts failed:", err);
            }
        }, settings.autoRefreshInterval * 1000);

        return () => clearInterval(interval);
    }, [token, settings.autoRefreshInterval]);

    // Navigate actions
    const handleNavigateToAlert = (alertId: number) => {
        setActiveView(`alert-${alertId}`);
    };

    // Mark an alert as acknowledged
    const handleAcknowledgeAlert = async (alertId: number) => {
        try {
            const updated = await acknowledgeAlertWithExplanation(alertId);
            const parsedUpdated = {
                ...updated,
                detectedStages: alerts.find(a => a.id === alertId)?.detectedStages ?? []
            };
            setAlerts((prev) => prev.map((a) => (a.id === alertId ? parsedUpdated : a)));
            addToast("success", "Alert Acknowledged", "The security alert was successfully marked as reviewed.");
        } catch (err) {
            addToast("error", "Error Acknowledging Alert", "Failed to acknowledge the alert.");
            console.error(err);
        }
    };

    // Merge analysis stage updates
    const handleUpdateAlertDetail = (updatedAlert: AlertWithExplanation) => {
        setAlerts((prev) => prev.map((a) => (a.id === updatedAlert.id ? updatedAlert : a)));
    };

    const handleLogout = () => {
        clearToken();
        setTokenState(null);
        setParent(null);
        setChildren([]);
        setAlerts([]);
        setActiveView("dashboard");
        addToast("info", "Logged Out", "You have successfully signed out of the monitoring session.");
    };

    const handleAuthSuccess = (newToken: string) => {
        setTokenState(newToken);
        addToast("success", "Welcome to TellMom", "Parent dashboard session established successfully.");
    };

    // Unread badge count
    const unreadAlertsCount = alerts.filter((a) => !a.acknowledged).length;

    // Render the current view
    const renderCurrentView = () => {
        if (isLoading && alerts.length === 0) {
            return <LoadingSpinner />;
        }

        if (error && alerts.length === 0) {
            return <ErrorFallback message={error} onRetry={loadDashboardData} />;
        }

        if (activeView.startsWith("alert-")) {
            const alertId = parseInt(activeView.replace("alert-", ""));
            const targetAlert = alerts.find((a) => a.id === alertId);

            if (!targetAlert) {
                return <ErrorFallback message="Alert record not found." onRetry={() => setActiveView("alerts")} />;
            }

            return (
                <AlertDetailView
                    alert={targetAlert}
                    children={children}
                    onBack={() => setActiveView("alerts")}
                    onAcknowledge={handleAcknowledgeAlert}
                    onUpdateAlert={handleUpdateAlertDetail}
                />
            );
        }

        switch (activeView) {
            case "dashboard":
                return (
                    <DashboardView
                        children={children}
                        alerts={alerts}
                        onNavigateToAlert={handleNavigateToAlert}
                        onNavigateToChildren={() => setActiveView("children")}
                        onNavigateToAlertsList={() => setActiveView("alerts")}
                    />
                );
            case "alerts":
                return (
                    <AlertsPage
                        alerts={alerts}
                        children={children}
                        onSelectAlert={handleNavigateToAlert}
                        onAcknowledgeAlert={handleAcknowledgeAlert}
                    />
                );
            case "children":
                return (
                    <ChildrenManagement
                        children={children}
                        onRefresh={loadDashboardData}
                    />
                );
            case "debug":
                return (
                    <TestChatRoom
                        children={children}
                    />
                );
            case "settings":
                return (
                    <SettingsView
                        settings={settings}
                        onUpdateSetting={updateSetting}
                    />
                );
            default:
                return <LoadingSpinner />;
        }
    };

    // Render Authentication screen if session token is missing
    if (!token) {
        return (
            <>
                <AuthPage onSuccess={handleAuthSuccess} />
                <ToastNotification toasts={toasts} onClose={closeToast} />
            </>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col lg:flex-row relative">
            {/* Background Gradients */}
            <div className="absolute top-0 right-0 w-[50%] h-[50%] bg-violet-900/10 blur-[130px] rounded-full pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-[50%] h-[50%] bg-indigo-900/10 blur-[130px] rounded-full pointer-events-none" />

            {/* Sidebar Panel */}
            <Sidebar
                activeView={activeView}
                onNavigate={setActiveView}
                parent={parent}
                onLogout={handleLogout}
                unreadAlertsCount={unreadAlertsCount}
            />

            {/* Main Content Area */}
            <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto z-10 max-w-7xl mx-auto w-full">
                {renderCurrentView()}
            </main>

            {/* Notification Toast Layer */}
            <ToastNotification
                toasts={toasts}
                onClose={closeToast}
                onNavigateToAlert={handleNavigateToAlert}
            />
        </div>
    );
}
