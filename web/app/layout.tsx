import "./globals.css";
import type { Metadata } from "next";
import * as React from "react";

export const metadata: Metadata = {
  title: "Cryptography Lab — Shri Labs",
  description: "Shridhar Infosec Solutions — CEH v13 hands-on cryptography labs",
  icons: { icon: "/assets/favicon.png" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
