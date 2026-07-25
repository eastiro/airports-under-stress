import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const incomingHeaders = await headers();
  const host =
    incomingHeaders.get("x-forwarded-host") ?? incomingHeaders.get("host") ?? "localhost:3000";
  const protocol =
    incomingHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;
  const description =
    "An evidence-first exploration of how aircraft delays propagate and recover across the U.S. aviation network.";
  const imageUrl = `${origin}/og.png`;

  return {
    metadataBase: new URL(origin),
    title: "Airports Under Stress — U.S. Delay Propagation Lab",
    description,
    keywords: [
      "aviation analytics",
      "flight delays",
      "network resilience",
      "BTS data",
      "data visualization",
    ],
    openGraph: {
      title: "Airports Under Stress",
      description,
      url: origin,
      siteName: "Airports Under Stress",
      type: "website",
      images: [{ url: imageUrl, width: 1732, height: 908, alt: "Airports Under Stress" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Airports Under Stress",
      description,
      images: [imageUrl],
    },
    icons: {},
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
