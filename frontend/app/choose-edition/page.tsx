"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { startGame, getLeaderboard, type Item, LeaderboardItem } from "@/lib/api";
import { Film, Tv, Scroll, Loader2 } from "lucide-react";

const editions = [
  { id: "anime", label: "Anime", icon: Scroll },
  { id: "movies", label: "Movies", icon: Film },
  { id: "tv_shows", label: "TV Shows", icon: Tv },
];

export default function ChooseEdition() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [activeEdition, setActiveEdition] = useState("anime");
  const [leaderboards, setLeaderboards] = useState<{ kept: LeaderboardItem[], cut: LeaderboardItem[] }>({ kept: [], cut: [] });
  const [fetchingLeaderboard, setFetchingLeaderboard] = useState(false);

  useEffect(() => {
    async function fetchBoards() {
      setFetchingLeaderboard(true);
      try {
        const [kept, cut] = await Promise.all([
          getLeaderboard("kept", activeEdition),
          getLeaderboard("cut", activeEdition)
        ]);
        setLeaderboards({ kept, cut });
      } catch (error) {
        console.error("Failed to fetch leaderboards", error);
      } finally {
        setFetchingLeaderboard(false);
      }
    }
    fetchBoards();
  }, [activeEdition]);

  async function handleStart(edition: string) {
    setLoading(true);
    try {
      const data = await startGame(edition);
      // Store in localStorage to pass to game page
      localStorage.setItem("current_session", JSON.stringify(data));
      router.push("/game");
    } catch (error) {
      alert("Failed to start game. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-12 animate-in slide-in-from-bottom-4 duration-500">
      <div className="text-center space-y-2">
        <h1 className="text-4xl font-black">Choose Your Edition</h1>
        <p className="opacity-60">Pick a category to begin your sequence.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {editions.map((edition) => (
          <button
            key={edition.id}
            onClick={() => handleStart(edition.id)}
            disabled={loading}
            className="flex flex-col items-center gap-4 p-8 bg-white border-2 border-transparent hover:border-terracotta rounded-3xl transition-all group active:scale-95 disabled:opacity-50"
          >
            <div className="p-4 bg-peach rounded-2xl group-hover:bg-terracotta group-hover:text-white transition-colors">
              <edition.icon className="w-10 h-10" />
            </div>
            <span className="text-xl font-bold">{edition.label}</span>
          </button>
        ))}
      </div>

      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#e2e1de] pb-4">
          <h2 className="text-2xl font-black">Leaderboards</h2>
          <div className="flex bg-white rounded-full p-1 border border-[#e2e1de]">
            {editions.map((e) => (
              <button
                key={e.id}
                onClick={() => setActiveEdition(e.id)}
                className={`px-4 py-2 rounded-full text-sm font-bold transition-all ${
                  activeEdition === e.id ? "bg-sky text-white" : "hover:bg-peach"
                }`}
              >
                {e.label}
              </button>
            ))}
          </div>
        </div>

        {fetchingLeaderboard ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-sky" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <LeaderboardColumn title="Most Kept" items={leaderboards.kept} />
            <LeaderboardColumn title="Most Cut" items={leaderboards.cut} />
          </div>
        )}
      </div>
    </div>
  );
}

function LeaderboardColumn({ title, items }: { title: string, items: { id: number, name: string, image_url: string, edition: string, count?: number }[] }) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold uppercase tracking-widest opacity-40">{title}</h3>
      <div className="space-y-2">
        {items.length === 0 ? (
          <div className="card text-center py-12 opacity-50 italic">
            No votes yet. Be the first to play!
          </div>
        ) : (
          items.map((item, index) => (
            <div key={item.id} className="card flex items-center gap-4 hover:border-sky transition-colors">
              <div className="text-2xl font-black text-sky w-6">{index + 1}</div>
              <img 
                src={item.image_url} 
                alt={item.name} 
                className="w-12 h-18 object-cover rounded-md bg-peach"
                referrerPolicy="no-referrer"
              />
              <div className="flex-1 min-w-0">
                <div className="font-bold truncate">{item.name}</div>
                {/* Votes count */}
                <div className="text-xs opacity-60">{item.count ?? 0} votes</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
