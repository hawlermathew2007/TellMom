import React, { useState } from "react";
import { ChatPlatform, ChildAccountResponse } from "../../apis";
import { getApis } from "../../apis/client";
import {
    Send,
    Gamepad,
    Users,
    Loader2,
    CheckCircle,
    AlertCircle
} from "lucide-react";

interface TestChatRoomProps {
    children: ChildAccountResponse[];
}

interface LocalSimMessage {
    senderId: string;
    role: "child" | "suspect" | "other";
    content: string;
    timestamp: Date;
}

const PRESET_MESSAGES = [
    { label: "Friendly Greeting", text: "Hey! Nice avatar. Do you play Roblox a lot? I can give you some free Robux if you add me on Discord." },
    { label: "Encouraging Secrets", text: "You're really fun to talk to. Let's make this our secret friendship, okay? Don't tell your parents, they wouldn't understand." },
    { label: "Requesting Selfie", text: "Can you send me a picture of what you look like? Just a quick selfie so I know who I'm chatting with." },
    { label: "Escalating Topics", text: "Hey, are you alone in your room right now? Let's voice chat somewhere private where no one can hear us." },
    { label: "Coercive Control", text: "If you don't send me that picture, I won't buy you the game pass anymore. And I'll show our other chat messages to your friends." }
];

export default function TestChatRoom({ children }: TestChatRoomProps) {
    // Config
    const [selectedChildId, setSelectedChildId] = useState<string>("");
    const [serverId, setServerId] = useState("game-server-999");

    // Custom Senders
    const [senderRole, setSenderRole] = useState<"child" | "suspect" | "other">("suspect");
    const [suspectUserId, setSuspectUserId] = useState("Strangr_99");
    const [customUserId, setCustomUserId] = useState("User_X");

    // Message input
    const [message, setMessage] = useState("");
    const [localHistory, setLocalHistory] = useState<LocalSimMessage[]>([]);

    // Ref for autoscroll
    const chatEndRef = React.useRef<HTMLDivElement>(null);

    // Status
    const [isLoading, setIsLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState("");

    const selectedChild = children.find(c => String(c.id) === selectedChildId);

    // Resolve sender ID based on role
    const getSenderId = () => {
        if (senderRole === "child") {
            return selectedChild ? selectedChild.platformUserId : "ChildUser";
        }
        if (senderRole === "suspect") {
            return suspectUserId;
        }
        return customUserId;
    };

    const handleSend = async (textToSend: string) => {
        const text = textToSend.trim();
        if (!text) return;
        if (children.length === 0) {
            setError("Please register at least one child account first to simulate messages.");
            return;
        }
        if (!selectedChildId) {
            setError("Please select a target child account to simulate the chat.");
            return;
        }

        setIsLoading(true);
        setError("");
        setSuccess(false);

        const senderId = getSenderId();
        const platform = selectedChild ? selectedChild.platform : ChatPlatform.Roblox;

        try {
            // Direct ingest API POST to backend
            await getApis().ingests.ingestApiIngestPost({
                ingestRequest: {
                    platform,
                    userId: senderId,
                    serverId: serverId,
                    message: text
                }
            });

            // Add to local UI log
            const newMsg: LocalSimMessage = {
                senderId,
                role: senderRole,
                content: text,
                timestamp: new Date()
            };
            setLocalHistory(prev => [...prev, newMsg]);

            // Clear input
            setMessage("");
            setSuccess(true);
            setTimeout(() => setSuccess(false), 2000);

        } catch (err: unknown) {
            setError("Ingest call failed. Ensure backend API server is running.");
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    // Automatically select first child if registered
    React.useEffect(() => {
        if (children.length > 0 && !selectedChildId) {
            setSelectedChildId(String(children[0].id));
        }
    }, [children, selectedChildId]);

    // Automatically scroll to bottom when new messages arrive
    React.useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [localHistory]);

    // Keybindings to switch sender role
    React.useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            const activeEl = document.activeElement;
            if (
                activeEl &&
                (activeEl.tagName === "INPUT" ||
                    activeEl.tagName === "TEXTAREA" ||
                    activeEl.tagName === "SELECT" ||
                    (activeEl as HTMLElement).isContentEditable)
            ) {
                return;
            }

            if (e.key === "1") {
                setSenderRole("suspect");
            } else if (e.key === "2") {
                setSenderRole("child");
            } else if (e.key === "3") {
                setSenderRole("other");
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => {
            window.removeEventListener("keydown", handleKeyDown);
        };
    }, []);

    return (
        <div className="space-y-6">
            {/* Top Header */}
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">Test Chat Room</h1>
                <p className="text-slate-400 text-sm">Simulate chat conversations directly against the backend classifier models</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Left Panel: Simulator Configurations */}
                <div className="space-y-4 lg:col-span-1">
                    <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-5 space-y-4">
                        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                            <Gamepad className="w-4 h-4 text-violet-400" />
                            1. Targets & Server
                        </h3>

                        {/* Target Monitored Child */}
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                                Target Child Account
                            </label>
                            {children.length === 0 ? (
                                <div className="text-xs text-amber-400 p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                                    No children registered. Please register a child first!
                                </div>
                            ) : (
                                <select
                                    value={selectedChildId}
                                    onChange={(e) => setSelectedChildId(e.target.value)}
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 px-3 text-xs text-slate-350 focus:outline-none focus:ring-1 focus:ring-violet-500"
                                >
                                    {children.map((c) => (
                                        <option key={c.id} value={c.id}>
                                            {c.displayName || c.platformUserId} ({c.platform})
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>

                        {/* Server ID */}
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                                Server/Chatroom ID
                            </label>
                            <input
                                type="text"
                                value={serverId}
                                onChange={(e) => setServerId(e.target.value)}
                                placeholder="e.g. server-123"
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 px-3 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500"
                            />
                        </div>
                    </div>

                    {/* Senders Config */}
                    <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-5 space-y-4">
                        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                            <Users className="w-4 h-4 text-violet-400" />
                            2. Select Sender
                        </h3>

                        <div className="grid grid-cols-3 gap-2">
                            <button
                                type="button"
                                onClick={() => setSenderRole("suspect")}
                                className={`py-2 text-[10px] font-bold rounded-lg border uppercase transition-all ${senderRole === "suspect"
                                    ? "bg-red-500/10 border-red-500/30 text-red-400"
                                    : "bg-slate-950 border-slate-850 text-slate-500 hover:text-slate-400"
                                    }`}
                                title="Press key 1 to select Suspect role"
                            >
                                Suspect [1]
                            </button>
                            <button
                                type="button"
                                onClick={() => setSenderRole("child")}
                                className={`py-2 text-[10px] font-bold rounded-lg border uppercase transition-all ${senderRole === "child"
                                    ? "bg-blue-500/10 border-blue-500/30 text-blue-400"
                                    : "bg-slate-950 border-slate-850 text-slate-500 hover:text-slate-400"
                                    }`}
                                title="Press key 2 to select Target Child role"
                            >
                                Target Child [2]
                            </button>
                            <button
                                type="button"
                                onClick={() => setSenderRole("other")}
                                className={`py-2 text-[10px] font-bold rounded-lg border uppercase transition-all ${senderRole === "other"
                                    ? "bg-slate-800 border-slate-750 text-slate-350"
                                    : "bg-slate-950 border-slate-850 text-slate-500 hover:text-slate-400"
                                    }`}
                                title="Press key 3 to select Custom User role"
                            >
                                Custom User [3]
                            </button>
                        </div>

                        {/* Sender input fields */}
                        {senderRole === "suspect" && (
                            <div className="space-y-1.5">
                                <span className="text-[10px] text-slate-500">Suspect User ID</span>
                                <input
                                    type="text"
                                    value={suspectUserId}
                                    onChange={(e) => setSuspectUserId(e.target.value)}
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 px-3 text-xs text-slate-200 focus:outline-none"
                                />
                            </div>
                        )}

                        {senderRole === "child" && (
                            <div className="p-2 bg-slate-950 border border-slate-850 rounded-lg text-[10px] text-slate-400">
                                Will send as target child: <strong className="text-slate-300">{selectedChild ? selectedChild.platformUserId : "(None)"}</strong>
                            </div>
                        )}

                        {senderRole === "other" && (
                            <div className="space-y-1.5">
                                <span className="text-[10px] text-slate-500">Custom Participant User ID</span>
                                <input
                                    type="text"
                                    value={customUserId}
                                    onChange={(e) => setCustomUserId(e.target.value)}
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 px-3 text-xs text-slate-200 focus:outline-none"
                                />
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Panel: Chat Simulator Console */}
                <div className="lg:col-span-2 bg-slate-950 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-[calc(100vh-12rem)] shadow-inner">
                    {/* Header */}
                    <div className="p-3.5 bg-slate-900/60 border-b border-slate-800 flex justify-between items-center">
                        <span className="text-xs font-semibold text-slate-200">Conversation Simulation Logs</span>
                        <button
                            onClick={() => setLocalHistory([])}
                            className="text-[10px] text-slate-500 hover:text-slate-300 underline"
                        >
                            Clear Logs
                        </button>
                    </div>

                    {/* Logs Area */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
                        {localHistory.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center text-center space-y-2 p-8">
                                <div className="w-10 h-10 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-600">
                                    <Send className="w-4 h-4" />
                                </div>
                                <p className="text-slate-500 text-xs font-semibold">Simulation log is currently empty</p>
                                <p className="text-slate-650 text-[10px] max-w-xs leading-relaxed">
                                    Select a child, type a message or choose a preset below, and click Send. The message will trigger real-time backend alerts.
                                </p>
                            </div>
                        ) : (
                            localHistory.map((msg, idx) => (
                                <div
                                    key={idx}
                                    className={`flex flex-col gap-1 max-w-[80%] ${msg.role === "child" ? "ml-auto items-end" : "mr-auto items-start"
                                        }`}
                                >
                                    <div className="flex items-center gap-1.5 text-[9px] text-slate-500">
                                        <span className={`font-bold ${msg.role === "child" ? "text-blue-400" : msg.role === "suspect" ? "text-red-400" : "text-slate-400"}`}>
                                            {msg.senderId}
                                        </span>
                                        <span>•</span>
                                        <span>{msg.timestamp.toLocaleTimeString()}</span>
                                    </div>
                                    <div className={`p-2.5 rounded-lg border text-xs leading-relaxed ${msg.role === "child"
                                        ? "bg-blue-600/10 border-blue-500/20 text-blue-200"
                                        : msg.role === "suspect"
                                            ? "bg-red-500/10 border-red-500/20 text-red-200 animate-pulse-ring"
                                            : "bg-slate-900 border-slate-800 text-slate-300"
                                        }`}>
                                        {msg.content}
                                    </div>
                                </div>
                            ))
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    {/* Quick presets */}
                    <div className="p-3 bg-slate-900/30 border-t border-slate-850 flex gap-2 overflow-x-auto whitespace-nowrap">
                        {PRESET_MESSAGES.map((preset, index) => (
                            <button
                                key={index}
                                type="button"
                                onClick={() => setMessage(preset.text)}
                                className="px-2.5 py-1 bg-slate-900 hover:bg-slate-850 text-slate-400 hover:text-slate-200 text-[10px] rounded border border-slate-800/80 font-medium shrink-0 transition-colors"
                            >
                                {preset.label}
                            </button>
                        ))}
                    </div>

                    {/* Input Sender Bar */}
                    <div className="p-3 bg-slate-900/60 border-t border-slate-800 space-y-3">
                        {/* Status Info */}
                        {error && (
                            <div className="p-2.5 bg-red-950/20 border border-red-900/30 text-red-400 text-[10px] rounded-lg flex items-center gap-2">
                                <AlertCircle className="w-3.5 h-3.5 text-red-500" />
                                <span className="font-medium">{error}</span>
                            </div>
                        )}
                        {success && (
                            <div className="p-2 bg-emerald-950/20 border border-emerald-900/30 text-emerald-400 text-[10px] rounded-lg flex items-center gap-2">
                                <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                                <span>Message injected successfully! Alerts updated in real-time.</span>
                            </div>
                        )}

                        <form
                            onSubmit={(e) => { e.preventDefault(); handleSend(message); }}
                            className="flex gap-2"
                        >
                            <input
                                type="text"
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                placeholder={`Type a message as ${getSenderId()}...`}
                                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40"
                            />
                            <button
                                type="submit"
                                disabled={isLoading || !message.trim()}
                                className="bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:pointer-events-none text-white text-xs px-4 rounded-lg flex items-center justify-center gap-1.5 transition-all shadow-md active:scale-95"
                            >
                                {isLoading ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                    <>
                                        <Send className="w-3 h-3" />
                                        Send
                                    </>
                                )}
                            </button>
                        </form>
                    </div>
                </div>

            </div>
        </div>
    );
}
