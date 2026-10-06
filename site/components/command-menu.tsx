"use client";
// ⌘K search over the docs, shadcn's pattern (cmdk). Opened by ⌘K / Ctrl+K
// or the nav's search button.
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { NAV } from "@/lib/docs";

export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); }
    };
    const show = () => setOpen(true);
    addEventListener("keydown", key);
    addEventListener("open-command-menu", show);
    return () => { removeEventListener("keydown", key); removeEventListener("open-command-menu", show); };
  }, []);
  const go = (href: string) => { setOpen(false); router.push(href); };
  return (
    <Command.Dialog open={open} onOpenChange={setOpen} label="Search documentation">
      <Command.Input placeholder="Search documentation..." />
      <Command.List>
        <Command.Empty>No pages match.</Command.Empty>
        {NAV.map((g) => (
          <Command.Group key={g.group} heading={g.group}>
            {g.pages.map((p) => (
              <Command.Item key={p.slug} value={`${p.title} ${g.group} ${p.lede}`} onSelect={() => go(`/docs/${p.slug}/`)}>
                {p.title}
              </Command.Item>
            ))}
          </Command.Group>
        ))}
        <Command.Group heading="Pages">
          <Command.Item value="Results ablation table predictions" onSelect={() => go("/results/")}>Results</Command.Item>
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}
