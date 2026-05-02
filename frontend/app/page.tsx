import Link from "next/link";
import { Play } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] text-center space-y-8 animate-in fade-in duration-700">
      <div className="space-y-4">
        <h1 className="text-6xl md:text-8xl font-black tracking-tighter">
          KEEP <span className="opacity-30">/</span> CUT
        </h1>
        <p className="text-xl md:text-2xl font-medium max-w-lg mx-auto opacity-80">
          Play in blind (sequential) or open mode for anime, movies, and TV shows.
        </p>
      </div>

      <div className="card max-w-md mx-auto text-left relative overflow-hidden">
        <div className="absolute top-0 left-0 w-2 h-full bg-terracotta" />
        <h2 className="text-lg font-bold mb-2">How to Play</h2>
        <p className="text-sm leading-relaxed opacity-90">
          You’ll see 8 items one by one. For each, decide to <span className="font-bold text-teal">KEEP</span> or <span className="font-bold text-coral">CUT</span> without (or while) knowing what comes next. The game ends once you have kept or cut 4 items.
        </p>
      </div>

      <Link 
        href="/choose-edition" 
        className="btn-primary flex items-center gap-2 text-xl"
        id="play-now-btn"
      >
        <Play className="w-6 h-6 fill-current" />
        Play Now
      </Link>
    </div>
  );
}
