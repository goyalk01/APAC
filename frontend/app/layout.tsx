import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Multi-Agent Productivity Assistant",
  description: "Google Cloud Gen AI hackathon demo UI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
