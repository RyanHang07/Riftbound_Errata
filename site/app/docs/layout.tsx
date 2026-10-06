import { DocsSidebar } from "@/components/docs-sidebar";

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <main>
      <div className="docs">
        <DocsSidebar />
        {children}
      </div>
    </main>
  );
}
