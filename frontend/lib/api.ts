const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export interface Item {
  id: number;
  name: string;
  image_url: string;
  edition: string;
}

export interface StartResponse {
  session_id: string;
  item: Item;
  remaining: number;
}

export interface DecisionContinueResponse {
  round_complete: false;
  remaining: number;
  next_item: Item;
}

export interface DecisionFinalResponse {
  round_complete: true;
  kept_items: Item[];
  cut_items: Item[];
}

export type DecisionResponse = DecisionContinueResponse | DecisionFinalResponse;

export interface LeaderboardItem extends Item {
  count: number;
}

export async function startGame(edition: string): Promise<StartResponse> {
  const response = await fetch(`${API_BASE_URL}/keep-cut/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ edition }),
  });
  if (!response.ok) throw new Error('Failed to start game');
  return response.json();
}

export async function makeDecision(sessionId: string, itemId: number, action: 'keep' | 'cut'): Promise<DecisionResponse> {
  const response = await fetch(`${API_BASE_URL}/keep-cut/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, item_id: itemId, action }),
  });
  if (!response.ok) throw new Error('Failed to make decision');
  return response.json();
}

export async function getLeaderboard(type: 'kept' | 'cut', edition: string, limit: number = 5): Promise<LeaderboardItem[]> {
  const response = await fetch(`${API_BASE_URL}/votes/leaderboard/${type}?edition=${edition}&limit=${limit}`);
  if (!response.ok) return [];
  const data = await response.json();
  // Use the correct count field based on the endpoint type
  return data.map((item: any) => ({
    ...item,
    count: type === "kept"
      ? item.keep_count ?? 0
      : item.cut_count ?? 0,
  }));
}
