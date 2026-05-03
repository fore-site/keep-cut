"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { decideOpenGame, type Item, type OpenStartResponse } from "@/lib/api";
import { ArrowLeft, Loader2 } from "lucide-react";
import { motion } from "motion/react";

type Decision = "keep" | "cut";

export default function OpenGamePage() {
  const router = useRouter();
  const [session, setSession] = useState<OpenStartResponse | null>(null);
  const [decisions, setDecisions] = useState<Record<number, Decision>>({});
  const [pendingItemId, setPendingItemId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showEnding, setShowEnding] = useState<null | { action: Decision; edition: string }>(null);

  useEffect(() => {
    const saved = localStorage.getItem("open_session");
    if (!saved) {
      router.replace("/choose-edition");
      return;
    }
    const sessionData: OpenStartResponse = JSON.parse(saved);
    setSession(sessionData);

    const edition = sessionData.items?.[0]?.edition;
    if (edition) localStorage.setItem("edition", edition);
    localStorage.setItem("mode", "open");
  }, [router]);

  const undecidedCount = useMemo(() => {
    if (!session) return 0;
    return session.items.filter((i) => decisions[i.id] == null).length;
  }, [session, decisions]);

  async function handleDecision(item: Item, action: Decision) {
    if (!session || pendingItemId != null) return;
    if (decisions[item.id]) return;

    setPendingItemId(item.id);
    setError(null);

    try {
      const data = await decideOpenGame(session.session_id, item.id, action);
      setDecisions((prev) => ({ ...prev, [item.id]: action }));

      if (data.round_complete === true) {
        setShowEnding({ action, edition: item.edition });
        localStorage.setItem(
          "results",
          JSON.stringify({ kept: data.kept_items, cut: data.cut_items }),
        );
        setTimeout(() => router.push("/results"), 2000);
      }
    } catch (err) {
      setError("This session is completed. Kindly start over.");
    } finally {
      setPendingItemId(null);
    }
  }

  if (!session) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-10 h-10 animate-spin text-terracotta" />
      </div>
    );
  }

  if (showEnding) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-10 h-10 animate-spin text-terracotta" />
        <div className="text-lg font-bold text-center mt-4">
          You have {showEnding.action === "keep" ? "kept" : "cut"} 4 {showEnding.edition}. Game ending...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-20">
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.back()}
          className="p-2 hover:bg-white rounded-full transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div className="text-center">
          <div className="text-xs font-black uppercase tracking-widest opacity-40">Open Game</div>
          <div className="text-lg font-bold">
            {session.items.length - undecidedCount} of {session.items.length} decided
          </div>
        </div>
        <div className="w-10" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {session.items.map((item, idx) => {
          const decided = decisions[item.id];
          const isPending = pendingItemId === item.id;
          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(idx * 0.05, 0.3) }}
              className={`card p-2 space-y-2 ${decided ? "opacity-75" : ""}`}
            >
              <div className="aspect-[2/3] w-full bg-peach rounded-lg overflow-hidden relative">
                <img
                  src={item.image_url}
                  alt={item.name}
                  className="w-full h-full object-cover"
                  referrerPolicy="no-referrer"
                />
                {isPending && (
                  <div className="absolute inset-0 bg-white/40 backdrop-blur-sm flex items-center justify-center">
                    <Loader2 className="w-8 h-8 animate-spin text-terracotta" />
                  </div>
                )}
                {decided && (
                  <div
                    className={`absolute top-2 left-2 px-2 py-1 rounded-full text-xs font-black uppercase tracking-wider ${
                      decided === "keep" ? "bg-teal text-white" : "bg-coral text-white"
                    }`}
                  >
                    {decided}
                  </div>
                )}
              </div>

              <div className="text-center">
                <div className="text-sm font-bold whitespace-normal break-words leading-snug px-1">{item.name}</div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleDecision(item, "keep")}
                  disabled={!!decided || pendingItemId != null}
                  className="btn-keep flex items-center justify-center text-center py-2 text-sm leading-none shadow-none disabled:opacity-50"
                >
                  KEEP
                </button>
                <button
                  onClick={() => handleDecision(item, "cut")}
                  disabled={!!decided || pendingItemId != null}
                  className="btn-cut flex items-center justify-center text-center py-2 text-sm leading-none shadow-none disabled:opacity-50"
                >
                  CUT
                </button>
              </div>
            </motion.div>
          );
        })}
      </div>

      {error && (
        <div className="p-4 bg-coral/10 text-coral rounded-xl text-center font-bold animate-bounce">
          {error}
        </div>
      )}
    </div>
  );
}
