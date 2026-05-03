import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";

export const runtime = "edge";

type Item = {
  id: number;
  name: string;
  image_url?: string | null;
  edition: string;
};

type ResultsResponse = {
  session_id: string;
  edition: string;
  kept_items: Item[];
  cut_items: Item[];
};

const THEME = {
  peach: "#fff3e0",
  terracotta: "#e07a5f",
  teal: "#3d5a80",
  coral: "#ee6c4d",
  body: "#2d2d2d",
  border: "#e2e1de",
  white: "#ffffff",
};

function requireApiBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) throw new Error("NEXT_PUBLIC_API_URL is not set");
  return baseUrl;
}

function clampItems(items: Item[], max: number): Item[] {
  if (!Array.isArray(items)) return [];
  return items.slice(0, max);
}

function ItemCard({ item, accent, label }: { item: Item; accent: string; label: string }) {
  return (
    <div
      style={{
        background: THEME.white,
        border: `2px solid ${THEME.border}`,
        borderLeft: `10px solid ${accent}`,
        borderRadius: 18,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        width: 250,
        height: 238,
      }}
    >
      <div style={{ position: "relative", width: "100%", height: 170, background: THEME.peach }}>
        {item.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.image_url}
            alt={item.name}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : null}
        <div
          style={{
            position: "absolute",
            top: 10,
            left: 10,
            padding: "6px 10px",
            borderRadius: 999,
            background: accent,
            color: THEME.white,
            fontSize: 14,
            fontWeight: 800,
            letterSpacing: 1,
            textTransform: "uppercase",
          }}
        >
          {label}
        </div>
      </div>
      <div
        style={{
          padding: "10px 12px",
          color: THEME.body,
          fontSize: 18,
          fontWeight: 800,
          lineHeight: 1.15,
          display: "flex",
          alignItems: "center",
          height: 68,
          overflow: "hidden",
        }}
      >
        <span style={{ display: "block" }}>{item.name}</span>
      </div>
    </div>
  );
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> },
): Promise<Response> {
  const { sessionId } = await params;
  const apiBaseUrl = requireApiBaseUrl();

  let payload: ResultsResponse | null = null;
  try {
    const res = await fetch(`${apiBaseUrl}/keep-cut/results/${sessionId}`, {
      cache: "no-store",
    });
    if (res.ok) payload = (await res.json()) as ResultsResponse;
  } catch {
    // ignore and fall back to error card
  }

  if (!payload) {
    return new ImageResponse(
      (
        <div
          style={{
            width: "100%",
            height: "100%",
            background: THEME.peach,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto",
            padding: 60,
          }}
        >
          <div
            style={{
              background: THEME.white,
              border: `2px solid ${THEME.border}`,
              borderRadius: 24,
              padding: 36,
              width: "100%",
              maxWidth: 980,
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 56, fontWeight: 900, color: THEME.terracotta }}>
              Keep / Cut
            </div>
            <div style={{ marginTop: 12, fontSize: 24, color: THEME.body, opacity: 0.7 }}>
              Results not found (or expired).
            </div>
          </div>
        </div>
      ),
      { width: 1200, height: 630 },
    );
  }

  const kept = clampItems(payload.kept_items, 4);
  const cut = clampItems(payload.cut_items, 4);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: THEME.peach,
          display: "flex",
          flexDirection: "column",
          fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto",
          padding: 44,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 58, fontWeight: 900, color: THEME.terracotta, lineHeight: 1 }}>
              Final Verdict
            </div>
            <div style={{ marginTop: 10, fontSize: 22, color: THEME.body, opacity: 0.65 }}>
              {payload.edition.replaceAll("_", " ")}
            </div>
          </div>
          <div style={{ fontSize: 20, color: THEME.body, opacity: 0.6, fontWeight: 700 }}>
            keep-cut.vercel.app
          </div>
        </div>

        <div style={{ marginTop: 26, display: "flex", gap: 28, flex: 1 }}>
          <div
            style={{
              flex: 1,
              background: "rgba(255,255,255,0.55)",
              border: `2px solid ${THEME.border}`,
              borderRadius: 26,
              padding: 20,
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
              <div style={{ fontSize: 28, fontWeight: 900, color: THEME.teal }}>
                KEPT
              </div>
              <div style={{ fontSize: 20, fontWeight: 800, color: THEME.body, opacity: 0.6 }}>
                {kept.length}
              </div>
            </div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {kept.map((item) => (
                <ItemCard key={`kept-${item.id}`} item={item} accent={THEME.teal} label="Kept" />
              ))}
            </div>
          </div>

          <div
            style={{
              flex: 1,
              background: "rgba(255,255,255,0.55)",
              border: `2px solid ${THEME.border}`,
              borderRadius: 26,
              padding: 20,
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
              <div style={{ fontSize: 28, fontWeight: 900, color: THEME.coral }}>
                CUT
              </div>
              <div style={{ fontSize: 20, fontWeight: 800, color: THEME.body, opacity: 0.6 }}>
                {cut.length}
              </div>
            </div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {cut.map((item) => (
                <ItemCard key={`cut-${item.id}`} item={item} accent={THEME.coral} label="Cut" />
              ))}
            </div>
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
