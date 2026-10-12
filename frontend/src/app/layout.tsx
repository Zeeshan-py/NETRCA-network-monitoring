import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NetRCA | Network operations",
  description: "AI-assisted network root cause analysis for controlled simulations",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
