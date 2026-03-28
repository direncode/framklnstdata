import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Franklin Street Panopticon",
  description: "Surveillance-grade intelligence platform for Franklin Street, UNC Chapel Hill",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-[#0a0b0f] text-[#e2e4e9]" style={{ fontFamily: "'Inter', system-ui, -apple-system, sans-serif" }}>{children}</body>
    </html>
  );
}
