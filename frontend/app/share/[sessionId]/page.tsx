import type { Metadata } from "next";

function siteUrl(): string {
  const raw =
    process.env.NEXT_PUBLIC_SITE_URL ||
    process.env.NEXT_PUBLIC_APP_URL ||
    process.env.SITE_URL ||
    "https://keep-cut.vercel.app";
  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
  return `https://${raw}`;
}

export async function generateMetadata(
  { params }: { params: { sessionId: string } },
): Promise<Metadata> {
  const { sessionId } = params;
  const baseUrl = siteUrl();

  const pageUrl = `${baseUrl}/share/${sessionId}`;
  const imageUrl = `${baseUrl}/api/results-image/${sessionId}`;

  return {
    title: "Keep / Cut — Results",
    description: "My Keep/Cut results.",
    openGraph: {
      title: "Keep / Cut — Results",
      description: "My Keep/Cut results.",
      type: "website",
      url: pageUrl,
      images: [{ url: imageUrl, width: 1200, height: 630, alt: "Keep/Cut results" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Keep / Cut — Results",
      description: "My Keep/Cut results.",
      images: [imageUrl],
    },
  };
}

export default async function SharePage(
  { params }: { params: { sessionId: string } },
) {
  const { sessionId } = params;
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-4xl font-black">Share Card</h1>
        <p className="opacity-60">If you can see this page, the preview image should work on X/WhatsApp.</p>
      </div>

      <div className="card p-6 space-y-4">
        <div className="text-sm font-bold opacity-60">Session</div>
        <div className="font-mono break-all">{sessionId}</div>
      </div>

      <div className="card p-4">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/api/results-image/${sessionId}`}
          alt="Keep/Cut results image"
          className="w-full rounded-xl border border-[#e2e1de]"
        />
      </div>
    </div>
  );
}
