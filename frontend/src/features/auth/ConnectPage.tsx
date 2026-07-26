import React, { useState } from "react";
import { Server, Key, Loader2, ArrowRight } from "lucide-react";
import { customFetch, setSessionId } from "../../apis/client";
import { 
    generateDhPrivateKey, 
    deriveDhPublicKey, 
    intToB64Url, 
    b64UrlToInt, 
    deriveSharedSecret, 
    deriveSessionKeys,
    bytesToBase64
} from "../../lib/security";

interface ConnectPageProps {
  onSuccess: (sessionId: string) => void;
}

export default function ConnectPage({ onSuccess }: ConnectPageProps) {
  const [serverId, setServerId] = useState("");
  const [passwordCode, setPasswordCode] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState<"connect" | "key-exchange">("connect");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const clientId = "web-client-" + Math.random().toString(36).substring(2, 9);
      
      setStep("connect");
      const assocRes = await customFetch("/session/associate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          server_id: serverId,
          password_code: passwordCode,
          client_id: clientId,
        }),
      }, false);

      if (!assocRes.ok) {
        let errStr = "Failed to associate with server";
        try {
            const errObj = await assocRes.json();
            if (errObj.detail) errStr = errObj.detail;
        } catch {}
        throw new Error(errStr);
      }

      const assocData = await assocRes.json();
      if (assocData.status !== "SUCCESS") {
        throw new Error(assocData.reason || "Association failed");
      }
      
      const sid = assocData.session_id;

      // Key exchange
      setStep("key-exchange");
      const privKey = generateDhPrivateKey();
      const pubKey = deriveDhPublicKey(privKey);
      const pubKeyB64 = intToB64Url(pubKey);

      const dhRes = await customFetch("/session/key-exchange", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sid,
          client_dh_pubkey: pubKeyB64,
        }),
      }, false);

      if (!dhRes.ok) {
        let errStr = "Failed to negotiate keys";
        try {
            const errObj = await dhRes.json();
            if (errObj.detail) errStr = errObj.detail;
        } catch {}
        throw new Error(errStr);
      }

      const dhData = await dhRes.json();
      const serverPubB64 = dhData.server_dh_pubkey;
      const serverPub = b64UrlToInt(serverPubB64);

      const sharedSecret = await deriveSharedSecret(privKey, serverPub);
      const { aesKey, nonceBase } = await deriveSessionKeys(sharedSecret);

      // Save keys
      localStorage.setItem("tellmom_aes_key", bytesToBase64(aesKey));
      localStorage.setItem("tellmom_nonce_base", bytesToBase64(nonceBase));

      setSessionId(sid);
      onSuccess(sid);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-cyan-900/20 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-blue-900/20 blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md glass border border-slate-800/80 rounded-2xl p-8 shadow-2xl relative z-10">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-cyan-600 flex items-center justify-center mb-3 shadow-lg shadow-cyan-500/20">
            <Server className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 via-blue-200 to-white bg-clip-text text-transparent">
            Connect Server
          </h1>
          <p className="text-slate-400 text-sm mt-1 text-center">
            Link your TellMom server via proxy
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
              Server ID
            </label>
            <div className="relative">
              <Server className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                required
                value={serverId}
                onChange={(e) => setServerId(e.target.value)}
                placeholder="integration-server"
                className="w-full bg-slate-900/50 border border-slate-800 rounded-xl py-3 pl-10 pr-4 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500 transition-all text-sm"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
              Password Code
            </label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="password"
                required
                value={passwordCode}
                onChange={(e) => setPasswordCode(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-900/50 border border-slate-800 rounded-xl py-3 pl-10 pr-4 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500 transition-all text-sm"
              />
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-950/30 border border-red-800/50 text-red-400 text-xs rounded-lg">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white py-3 px-4 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-cyan-500/10 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                {step === "connect" ? "Associating..." : "Negotiating Keys..."}
              </span>
            ) : (
              <>
                Connect
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
