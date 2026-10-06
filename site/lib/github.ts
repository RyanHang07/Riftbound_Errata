// GitHub stars, fetched once at build time and baked into the page (A34):
// GitHub allows 60 unauthenticated requests an hour per visitor IP, so a
// browser-side fetch would fail for some visitors. Any failure, including a
// private repository, returns null and the button shows no count rather than
// a wrong one.
export const REPO = "RyanHang07/Riftbound_Errata";

export async function stars(): Promise<number | null> {
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}`, {
      headers: { Accept: "application/vnd.github+json" },
      signal: AbortSignal.timeout(5000),
    });
    if (!r.ok) return null;
    const j = (await r.json()) as { stargazers_count?: number };
    return typeof j.stargazers_count === "number" ? j.stargazers_count : null;
  } catch {
    return null;
  }
}
