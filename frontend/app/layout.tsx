import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "WealthAI",
  description: "Institutional-grade mutual fund intelligence"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
