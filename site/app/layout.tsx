import type { Metadata } from "next";
import "./globals.css";
import { CommandMenu } from "@/components/command-menu";
import { Nav } from "@/components/nav";
import { stars } from "@/lib/github";

export const metadata: Metadata = {
  title: "rb_errata",
  description: "Riftbound rules answered as of a date, with versioned citations. Runs locally.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const count = await stars();
  return (
    <html lang="en">
      <head>
        {/* Linked, not next/font: next/font downloads at build time, and a
            build must not fail because a font host is unreachable. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" />
      </head>
      <body>
        <Nav stars={count} />
        {children}
        <footer>
          <div>
            Built by RyanHang07. Rulings in the question set are adapted from Riftbound FAQ by Christian &ldquo;Near&rdquo; Ivicevic, CC BY-SA 4.0.
            Riftbound is a trademark of Riot Games; this is an unofficial fan project, and no Riot rule text appears on this site.
          </div>
        </footer>
        <CommandMenu />
      </body>
    </html>
  );
}
