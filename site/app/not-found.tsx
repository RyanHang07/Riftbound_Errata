import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="results">
      <h1>No such page</h1>
      <p className="lede">That page isn&apos;t in this version of the site.</p>
      <div><Button href="/docs/" variant="gold">Go to the docs</Button></div>
    </main>
  );
}
