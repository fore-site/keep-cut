"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { makeDecision, type Item, type StartResponse, type DecisionContinueResponse } from "@/lib/api";
import { Loader2, ArrowLeft } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";


export default function GamePage() {
  const router = useRouter();
  const [session, setSession] = useState<StartResponse | null>(null);
  const [round, setRound] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEnding, setShowEnding] = useState<null | { action: "keep" | "cut"; edition: string }>(null);

  useEffect(() => {
    const saved = localStorage.getItem("current_session");
    if (!saved) {
      router.replace("/choose-edition");
      return;
    }
    const sessionData = JSON.parse(saved);
    setSession(sessionData);

    // Set or override the edition in localStorage every time this page is visited
    if (sessionData && sessionData.item && sessionData.item.edition) {
      localStorage.setItem("edition", sessionData.item.edition);
    }
  }, [router]);

  async function handleDecision(action: "keep" | "cut") {
    if (!session || loading) return;
    setLoading(true);
    setError(null);

    try {
      const data = await makeDecision(session.session_id, session.item.id, action);
      if (data.round_complete === true) {
        // Show ending message before navigating
        setShowEnding({ action, edition: session.item.edition });
        localStorage.setItem("results", JSON.stringify({
          session_id: session.session_id,
          kept: data.kept_items,
          cut: data.cut_items
        }));
        setTimeout(() => {
          router.push("/results");
        }, 2000); // Show message for 2 seconds
      } else {
        // data.round_complete is false here
        const nextData = data as DecisionContinueResponse;
        setSession({
          ...session,
          item: nextData.next_item,
          remaining: nextData.remaining
        });
        setRound(prev => prev + 1);
      }
    } catch (err) {
      setError("This session is completed. Kindly start over.");
    } finally {
      setLoading(false);
    }
  }


  if (!session) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <Loader2 className="w-10 h-10 animate-spin text-terracotta" />
    </div>
  );

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
    <div className="max-w-md mx-auto space-y-8 pb-20">
      <div className="flex items-center justify-between">
        <button 
          onClick={() => router.back()} 
          className="p-2 hover:bg-white rounded-full transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div className="text-center">
          <div className="text-xs font-black uppercase tracking-widest opacity-40">Sequential Game</div>
          <div className="text-lg font-bold">Round {round} of 8</div>
        </div>
        <div className="w-10" />
      </div>

      <div className="w-full bg-white/50 h-2 rounded-full overflow-hidden">
        <motion.div 
          className="h-full bg-terracotta"
          initial={{ width: "0%" }}
          animate={{ width: `${(round / 8) * 100}%` }}
        />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={session.item.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
          className="space-y-8"
        >
          <div className="card p-4 space-y-4">
            <div className="aspect-[2/3] w-full bg-peach rounded-xl overflow-hidden relative group">
              <img 
                src={session.item.image_url} 
                alt={session.item.name}
                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                referrerPolicy="no-referrer"
              />
              {loading && (
                <div className="absolute inset-0 bg-white/40 backdrop-blur-sm flex items-center justify-center">
                  <Loader2 className="w-10 h-10 animate-spin text-terracotta" />
                </div>
              )}
            </div>
            <div className="text-center space-y-1">
              <div className="text-sm uppercase font-bold text-terracotta tracking-tight opacity-70">
                {session.item.edition}
              </div>
              <h2 className="text-2xl font-black">{session.item.name}</h2>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => handleDecision("keep")}
              disabled={loading}
              className="btn-keep py-6 text-xl shadow-none hover:brightness-95 disabled:opacity-50"
            >
              KEEP
            </button>
            <button
              onClick={() => handleDecision("cut")}
              disabled={loading}
              className="btn-cut py-6 text-xl shadow-none hover:brightness-95 disabled:opacity-50"
            >
              CUT
            </button>
          </div>
        </motion.div>
      </AnimatePresence>

      {error && (
        <div className="p-4 bg-coral/10 text-coral rounded-xl text-center font-bold animate-bounce">
          {error}
        </div>
      )}
    </div>
  );
}
