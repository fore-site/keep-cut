"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { type Item } from "@/lib/api";
import { Share2, RotateCcw, Home } from "lucide-react";
import { motion } from "motion/react";

export default function ResultsPage() {
  const router = useRouter();
  const [results, setResults] = useState<{ kept: Item[], cut: Item[] } | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("results");
    if (!saved) {
      router.replace("/choose-edition");
      return;
    }
    setResults(JSON.parse(saved));
  }, [router]);

  function handleShare() {
    if (!results) return;
    const keptNames = results.kept.map(i => i.name).join(", ");
    const text = `I played Keep/Cut! I kept: ${keptNames}. What are your favorites?`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!results) return null;

  return (
    <div className="space-y-12 animate-in fade-in zoom-in-95 duration-500">
      <div className="text-center space-y-4">
        <h1 className="text-5xl font-black">Final Verdict</h1>
        <p className="opacity-60">You've made your choices. Here is your split.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <ResultColumn title="Your Kept" items={results.kept} accent="teal" />
        <ResultColumn title="Your Cut" items={results.cut} accent="coral" />
      </div>

      <div className="flex flex-col md:flex-row items-center justify-center gap-4 pt-10">
        <button 
          onClick={() => router.push("/choose-edition")}
          className="btn-primary w-full md:w-auto flex items-center justify-center gap-2"
        >
          <RotateCcw className="w-5 h-5" />
          Play Again
        </button>
        <button 
          onClick={handleShare}
          className="bg-white border border-[#e2e1de] text-body px-8 py-4 rounded-xl font-bold transition-all hover:bg-peach active:scale-95 w-full md:w-auto flex items-center justify-center gap-2"
        >
          <Share2 className={`w-5 h-5 ${copied ? "text-teal" : ""}`} />
          {copied ? "Copied Summary!" : "Share Results"}
        </button>
        <button 
          onClick={() => router.push("/")}
          className="text-body/40 hover:text-body transition-colors p-4 flex items-center gap-2"
        >
          <Home className="w-5 h-5" />
          Home
        </button>
      </div>
    </div>
  );
}

function ResultColumn({ title, items, accent }: { title: string, items: Item[], accent: string }) {
  return (
    <div className="space-y-6">
      <h2 className={`text-2xl font-black text-center text-${accent}`}>{title} ({items.length})</h2>
      <div className="grid grid-cols-2 gap-4">
        {items.map((item, idx) => (
          <motion.div 
            key={item.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="card p-2 space-y-2 group"
          >
            <div className="aspect-[2/3] w-full rounded-lg overflow-hidden bg-peach">
              <img 
                src={item.image_url} 
                alt={item.name}
                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                referrerPolicy="no-referrer"
              />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold truncate px-1">{item.name}</div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
