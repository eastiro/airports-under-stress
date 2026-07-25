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
    "基于 611,735 条 BTS 逐航班记录，重建飞机轮转链，观察延误如何在美国航空网络中传播与被吸收。";
  const imageUrl = `${origin}/og.png`;

  return {
    metadataBase: new URL(origin),
    title: "Airports Under Stress — 航空延误传播与网络韧性实验室",
    description,
    keywords: [
      "aviation analytics",
      "flight delays",
      "network resilience",
      "BTS data",
      "data visualization",
      "航空延误",
      "延误传播",
      "航空网络韧性",
    ],
    openGraph: {
      title: "Airports Under Stress — 航空延误传播与网络韧性实验室",
      description,
      url: origin,
      siteName: "Airports Under Stress",
      type: "website",
      images: [{ url: imageUrl, width: 1732, height: 908, alt: "Airports Under Stress" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Airports Under Stress — 航空延误传播与网络韧性实验室",
      description,
      images: [imageUrl],
    },
    icons: {},
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
