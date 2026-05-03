"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { type Item } from "@/lib/api";
import { Share2, RotateCcw, Home } from "lucide-react";
import { motion } from "motion/react";

export default function ResultsPage() {
  const router = useRouter();
  const [results, setResults] = useState<{ kept: Item[], cut: Item[] } | null>(null);
  const [copied, setCopied] = useState(false);
  const [showShareOptions, setShowShareOptions] = useState(false);
  const shareBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem("results");
    if (!saved) {
      router.replace("/choose-edition");
      return;
    }
    setResults(JSON.parse(saved));
  }, [router]);

  function getShareText() {
    if (!results) return '';
    // Get edition from localStorage (fallback to 'Unknown Edition' if not found)
    const edition = localStorage.getItem("edition") || "unknown";
    const mode = localStorage.getItem("mode") || "unknown";
    const keptList = results.kept.length
      ? results.kept.map(i => `• ${i.name}`).join("\n")
      : 'None';
    const cutList = results.cut.length
      ? results.cut.map(i => `• ${i.name}`).join("\n")
      : 'None';
    return (
      `I played Keep/Cut! (${edition} edition - ${mode} mode)\n\n` +
      `Kept:\n${keptList}\n\n` +
      `Cut:\n${cutList}\n\n` +
      `Try it yourself: https://keep-cut.vercel.app`
    );
  }

  function handleCopy() {
    const text = getShareText();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleShareTwitter() {
    const text = getShareText();
    const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
  }

  function handleShareWhatsApp() {
    const text = getShareText();
    const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
  }

  function handleShare() {
    setShowShareOptions((v) => !v);
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
        <div className="relative">
          <button
            ref={shareBtnRef}
            onClick={handleShare}
            className="bg-white border border-[#e2e1de] text-body px-8 py-4 rounded-xl font-bold transition-all hover:bg-peach active:scale-95 w-full md:w-auto flex items-center justify-center gap-2"
          >
            <Share2 className={`w-5 h-5 ${copied ? "text-teal" : ""}`} />
            Share Results
          </button>
          {showShareOptions && (
            <div className="absolute left-0 mt-2 z-10 bg-white border border-[#e2e1de] rounded-xl shadow-lg p-4 flex flex-col gap-2 min-w-[180px]">
              <button
                onClick={() => {
                  handleCopy();
                  setShowShareOptions(false);
                }}
                className="w-full text-left px-2 py-2 rounded hover:bg-peach"
              >
                {copied ? "Copied!" : "Copy to Clipboard"}
              </button>
              <button
                onClick={() => {
                  handleShareTwitter();
                  setShowShareOptions(false);
                }}
                className="w-full text-left px-2 py-2 rounded hover:bg-peach"
              >
                <span className="inline-flex items-center gap-2">
                  {/* X (Twitter) logo SVG */}
                  <svg viewBox="0 0 1200 1227" fill="currentColor" className="w-4 h-4"><path d="M1199.61 0H950.94L599.8 465.9 299.06 0H.39l399.7 610.13L0 1227h249.06l368.6-511.2 299.06 511.2h248.89L817.5 610.13 1199.61 0Zm-212.2 1130.1-285.7-488.6-71.91-122.9-71.91 122.9-285.7 488.6H137.5l362.3-557.1-362.3-553.2h142.59l285.7 438.2 71.91 110.2 71.91-110.2 285.7-438.2h142.59l-362.3 553.2 362.3 557.1h-142.59Z"/></svg>
                  Share on X
                </span>
              </button>
              <button
                onClick={() => {
                  handleShareWhatsApp();
                  setShowShareOptions(false);
                }}
                className="w-full text-left px-2 py-2 rounded hover:bg-peach"
              >
                <span className="inline-flex items-center gap-2">
                  <svg viewBox="0 0 32 32" fill="currentColor" className="w-4 h-4"><path d="M16.003 3.2c-7.067 0-12.8 5.733-12.8 12.8 0 2.26.6 4.467 1.733 6.4l-1.8 6.533a1.067 1.067 0 0 0 1.307 1.307l6.533-1.8a12.73 12.73 0 0 0 6.027 1.547h.013c7.067 0 12.8-5.733 12.8-12.8 0-3.413-1.333-6.627-3.76-9.053C22.63 4.533 19.417 3.2 16.003 3.2zm0 23.467c-1.92 0-3.84-.507-5.493-1.467a1.067 1.067 0 0 0-.64-.12l-5.013 1.387 1.387-5.013a1.067 1.067 0 0 0-.12-.64A10.66 10.66 0 0 1 5.337 16c0-5.893 4.773-10.667 10.667-10.667 2.84 0 5.507 1.107 7.52 3.12a10.62 10.62 0 0 1 3.147 7.547c0 5.893-4.773 10.667-10.667 10.667zm5.44-7.36c-.293-.147-1.733-.867-2-1.013-.267-.147-.467-.213-.667.147-.2.36-.76 1.013-.933 1.213-.173.2-.347.227-.64.08-.293-.147-1.24-.457-2.36-1.453-.872-.777-1.46-1.733-1.633-2.027-.173-.293-.018-.453.13-.6.133-.133.293-.347.44-.52.147-.173.2-.293.3-.493.1-.2.05-.373-.025-.52-.08-.147-.667-1.6-.92-2.2-.24-.58-.48-.5-.667-.507l-.56-.01c-.2 0-.52.073-.793.367-.273.293-1.04 1.017-1.04 2.48 0 1.46 1.067 2.873 1.213 3.067.147.2 2.1 3.213 5.093 4.373.713.307 1.267.49 1.7.627.713.227 1.36.193 1.873.117.573-.087 1.733-.707 1.98-1.387.247-.68.247-1.267.173-1.387-.073-.12-.267-.193-.56-.34z"/></svg>
                  Share on WhatsApp
                </span>
              </button>
            </div>
          )}
        </div>
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
              <div className="text-sm font-bold whitespace-normal break-words leading-snug px-1">{item.name}</div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
