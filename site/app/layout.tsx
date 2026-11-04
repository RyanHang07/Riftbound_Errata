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
            No Riot rule text appears on this site.
            <br />
            {/* Required verbatim by Riot's Legal Jibber Jabber (section 6) and the Riftbound Developer API Policy (Brand Integrity). */}
            rb_errata was created under Riot Games&apos; &ldquo;Legal Jibber Jabber&rdquo; policy using assets owned by Riot Games. Riot Games does not endorse or sponsor this project.
          </div>
        </footer>
        <CommandMenu />
      </body>
    </html>
  );
}
