import React, { useState } from "react";
import { ChildAccountResponse, ChatPlatform } from "../../apis";
import { getApis } from "../../apis/client";
import { ResponseError } from "../../apis";
import { 
  UserPlus, 
  Trash2, 
  Edit2, 
  Check, 
  X, 
  Smartphone, 
  Gamepad2, 
  Compass, 
  User,
  Loader2,
  AlertTriangle
} from "lucide-react";

interface ChildrenManagementProps {
  children: ChildAccountResponse[];
  onRefresh: () => Promise<void>;
}

export default function ChildrenManagement({ children, onRefresh }: ChildrenManagementProps) {
  // Creation States
  const [platform, setPlatform] = useState<ChatPlatform>(ChatPlatform.Roblox);
  const [platformUserId, setPlatformUserId] = useState("");
  const [displayName, setDisplayName] = useState("");
  
  // Edit States
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editPlatformUserId, setEditPlatformUserId] = useState("");
  const [editDisplayName, setEditDisplayName] = useState("");

  // UI States
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!platformUserId.trim()) return;

    setError("");
    setIsLoading(true);

    try {
      await getApis().children.createChildApiChildrenPost({
        childAccountCreate: {
          platform,
          platformUserId: platformUserId.trim(),
          displayName: displayName.trim() || null,
        },
      });
      // Reset form
      setPlatformUserId("");
      setDisplayName("");
      await onRefresh();
    } catch (err: unknown) {
      if (err instanceof ResponseError) {
        try {
          const detail = await err.response.json();
          setError(detail.detail ?? "Failed to register child");
        } catch {
          setError(`Request failed (${err.response.status})`);
        }
      } else {
        setError("Failed to register child. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const startEdit = (child: ChildAccountResponse) => {
    setEditingId(child.id);
    setEditPlatformUserId(child.platformUserId);
    setEditDisplayName(child.displayName || "");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditPlatformUserId("");
    setEditDisplayName("");
  };

  const handleUpdate = async (childId: number) => {
    if (!editPlatformUserId.trim()) return;
    setIsLoading(true);
    setError("");

    try {
      await getApis().children.updateChildApiChildrenPut({
        childId,
        childAccountUpdate: {
          platformUserId: editPlatformUserId.trim(),
          displayName: editDisplayName.trim() || null,
        },
      });
      setEditingId(null);
      await onRefresh();
    } catch (err: unknown) {
      if (err instanceof ResponseError) {
        try {
          const detail = await err.response.json();
          setError(detail.detail ?? "Failed to update child");
        } catch {
          setError(`Request failed (${err.response.status})`);
        }
      } else {
        setError("Failed to update child");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (childId: number) => {
    setIsLoading(true);
    setError("");
    try {
      await getApis().children.deleteChildApiChildrenChildIdDelete({ childId });
      setDeleteConfirmId(null);
      await onRefresh();
    } catch (err: unknown) {
      setError("Failed to delete child account");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Helper for platform icons
  const getPlatformIcon = (plat: ChatPlatform) => {
    switch (plat) {
      case ChatPlatform.Roblox:
        return <Gamepad2 className="w-4 h-4 text-red-400" />;
      case ChatPlatform.Discord:
        return <Smartphone className="w-4 h-4 text-indigo-400" />;
      case ChatPlatform.Minecraft:
        return <Compass className="w-4 h-4 text-emerald-400" />;
      default:
        return <User className="w-4 h-4 text-slate-400" />;
    }
  };

  // Generate synthetic avatar based on child initials
  const getAvatarInitials = (child: ChildAccountResponse) => {
    const name = child.displayName || child.platformUserId;
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Children Accounts</h1>
        <p className="text-slate-400 text-sm">Register and manage children's platform accounts for active monitoring</p>
      </div>

      {/* Main Grid: Create form + Accounts list */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Register Account Form */}
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-5 h-fit">
          <div className="flex items-center gap-2 mb-4">
            <UserPlus className="w-4 h-4 text-violet-400" />
            <h3 className="text-sm font-semibold text-slate-200">Register New Child Account</h3>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Platform
              </label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value as ChatPlatform)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 px-3 text-slate-300 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500 transition-all text-sm capitalize"
              >
                <option value={ChatPlatform.Roblox}>Roblox</option>
                <option value={ChatPlatform.Discord}>Discord</option>
                <option value={ChatPlatform.Minecraft}>Minecraft</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Platform User ID
              </label>
              <input
                type="text"
                required
                value={platformUserId}
                onChange={(e) => setPlatformUserId(e.target.value)}
                placeholder="e.g. RobloxKid123"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 px-3 text-slate-200 placeholder:text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500 transition-all text-sm"
              />
              <p className="text-[10px] text-slate-500">The unique username or ID on the selected platform.</p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Display Name (Optional)
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Jake (Roblox)"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 px-3 text-slate-200 placeholder:text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500 transition-all text-sm"
              />
              <p className="text-[10px] text-slate-500">Friendly name to display on the dashboard.</p>
            </div>

            {error && (
              <div className="p-3 bg-red-950/30 border border-red-800/50 text-red-400 text-xs rounded-lg">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || !platformUserId}
              className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:pointer-events-none text-white py-2.5 px-4 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2 active:scale-[0.98]"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
                  Add to Monitored Accounts
                </>
              )}
            </button>
          </form>
        </div>

        {/* Registered Children List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Monitored Accounts List</h3>

            {children.length === 0 ? (
              <div className="text-center py-16 border border-dashed border-slate-800 rounded-lg space-y-2">
                <p className="text-slate-400 text-sm">No child accounts registered yet.</p>
                <p className="text-slate-500 text-xs">Fill out the registration form on the left to start monitoring.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {children.map((child) => {
                  const isEditing = editingId === child.id;
                  const isConfirmingDelete = deleteConfirmId === child.id;

                  return (
                    <div 
                      key={child.id}
                      className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 hover:bg-slate-950/70 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                      <div className="flex items-center gap-3.5 min-w-0">
                        {/* Avatar */}
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center font-bold text-sm text-white shrink-0 shadow-md">
                          {getAvatarInitials(child)}
                        </div>

                        {/* Details */}
                        {isEditing ? (
                          <div className="flex flex-col gap-2 w-full max-w-md">
                            <input
                              type="text"
                              required
                              value={editDisplayName}
                              onChange={(e) => setEditDisplayName(e.target.value)}
                              placeholder="Display name"
                              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-white placeholder:text-slate-700"
                            />
                            <input
                              type="text"
                              required
                              value={editPlatformUserId}
                              onChange={(e) => setEditPlatformUserId(e.target.value)}
                              placeholder="Platform user ID"
                              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-white placeholder:text-slate-700"
                            />
                          </div>
                        ) : (
                          <div className="min-w-0">
                            <h4 className="text-sm font-semibold text-slate-200 truncate">
                              {child.displayName || child.platformUserId}
                            </h4>
                            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                              <span className="text-[10px] text-slate-500 flex items-center gap-1 capitalize bg-slate-900 px-1.5 py-0.5 rounded border border-slate-850">
                                {getPlatformIcon(child.platform)}
                                {child.platform}
                              </span>
                              <span className="text-[10px] text-slate-500 font-mono">
                                ID: {child.platformUserId}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                        {isEditing ? (
                          <>
                            <button
                              onClick={() => handleUpdate(child.id)}
                              disabled={isLoading}
                              className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center hover:bg-emerald-500/20 transition-all"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={cancelEdit}
                              className="w-8 h-8 rounded-lg bg-slate-800 text-slate-400 flex items-center justify-center hover:bg-slate-700 transition-all"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </>
                        ) : isConfirmingDelete ? (
                          <div className="flex items-center gap-1 bg-red-950/20 border border-red-900/30 rounded-lg p-1">
                            <span className="text-[10px] text-red-400 font-semibold px-2">Are you sure?</span>
                            <button
                              onClick={() => handleDelete(child.id)}
                              disabled={isLoading}
                              className="px-2.5 py-1 rounded bg-red-600 hover:bg-red-500 text-white text-[10px] font-semibold transition-all"
                            >
                              Yes
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(null)}
                              className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 text-[10px] transition-all"
                            >
                              No
                            </button>
                          </div>
                        ) : (
                          <>
                            <span className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[9px] px-2 py-0.5 rounded-full font-bold uppercase mr-2 flex items-center gap-1 shadow-sm shadow-emerald-500/5">
                              <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
                              Monitoring
                            </span>
                            
                            <button
                              onClick={() => startEdit(child)}
                              className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 flex items-center justify-center hover:text-slate-200 hover:bg-slate-800 transition-all"
                              title="Edit account"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(child.id)}
                              className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-red-400 hover:bg-red-950/20 hover:border-red-900/20 flex items-center justify-center transition-all"
                              title="Delete account"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
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
