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

export interface OpenStartResponse {
  session_id: string;
  items: Item[];
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

export type OpenDecisionResponse =
  | { round_complete: false; remaining: number; next_item: null }
  | { round_complete: true; kept_items: Item[]; cut_items: Item[] };

export interface LeaderboardItem extends Item {
  count: number;
}

function requireApiBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new Error("NEXT_PUBLIC_API_URL is not set");
  }
  return API_BASE_URL;
}

async function postJson<T>(paths: string[], body: unknown): Promise<T> {
  const baseUrl = requireApiBaseUrl();
  let lastError: unknown = null;

  for (const path of paths) {
    const response = await fetch(`${baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (response.ok) return response.json();

    // Allow back-compat fallbacks (e.g. old routes) on 404 only.
    if (response.status === 404) {
      lastError = new Error(`Endpoint not found: ${path}`);
      continue;
    }

    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      message = typeof data?.detail === "string" ? data.detail : message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  throw (lastError instanceof Error ? lastError : new Error("Request failed"));
}

export async function startBlindGame(edition: string): Promise<StartResponse> {
  // Prefer new blind-mode endpoints; fall back to legacy paths if needed.
  return postJson<StartResponse>(
    ["/keep-cut/blind/start", "/keep-cut/start"],
    { edition },
  );
}

// Back-compat alias (existing blind-mode UI uses this name).
export async function startGame(edition: string): Promise<StartResponse> {
  return startBlindGame(edition);
}

export async function makeBlindDecision(
  sessionId: string,
  itemId: number,
  action: "keep" | "cut",
): Promise<DecisionResponse> {
  return postJson<DecisionResponse>(
    ["/keep-cut/blind/decide", "/keep-cut/decide"],
    { session_id: sessionId, item_id: itemId, action },
  );
}

// Back-compat alias (existing blind-mode UI uses this name).
export async function makeDecision(
  sessionId: string,
  itemId: number,
  action: "keep" | "cut",
): Promise<DecisionResponse> {
  return makeBlindDecision(sessionId, itemId, action);
}

export async function startOpenGame(edition: string): Promise<OpenStartResponse> {
  return postJson<OpenStartResponse>(["/keep-cut/open/start"], { edition });
}

export async function decideOpenGame(
  sessionId: string,
  itemId: number,
  action: "keep" | "cut",
): Promise<OpenDecisionResponse> {
  return postJson<OpenDecisionResponse>(
    ["/keep-cut/open/decide"],
    { session_id: sessionId, item_id: itemId, action },
  );
}

export async function getLeaderboard(type: 'kept' | 'cut', edition: string, limit: number = 5): Promise<LeaderboardItem[]> {
  const baseUrl = requireApiBaseUrl();
  const response = await fetch(`${baseUrl}/votes/leaderboard/${type}?edition=${edition}&limit=${limit}`);
  if (!response.ok) return [];
  const data = await response.json();
  // Use the correct count field based on the endpoint type
  return data.map((item: any) => ({
    id: item.item_id ?? item.id,
    name: item.name,
    image_url: item.image_url,
    edition,
    count: type === "kept"
      ? item.keep_count ?? 0
      : item.cut_count ?? 0,
  }));
}

export async function fetchResultsCardPng(args: {
  edition: string;
  mode: string;
  keepImages: string[];
  cutImages: string[];
  width?: number;
}): Promise<Blob> {
  const baseUrl = requireApiBaseUrl();
  const response = await fetch(`${baseUrl}/images/results-card`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      edition: args.edition,
      mode: args.mode,
      keep_images: args.keepImages,
      cut_images: args.cutImages,
      width: args.width,
    }),
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      message = typeof data?.detail === "string" ? data.detail : message;
    } catch {
      // ignore non-json
    }
    throw new Error(message);
  }
  return response.blob()
}
