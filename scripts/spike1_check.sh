#!/usr/bin/env bash
# Slice 1 spike: what can a normal home connection reach?
#
# Run on your own machine (the cloud session's network blocks every Riot and
# community host). Downloads nothing to keep: HEAD requests only, so no Riot
# text lands on disk or in the repository.
#
# Part 1 settles provenance. Riot's CDN names every file after the SHA-1 of its
# bytes, so if a URL built from a GitHub copy's SHA-1 answers 200, that copy is
# byte-for-byte Riot's file. Five of nine were already matched from search
# results; these are the four that were not.
#
# Part 2 records obtained / blocked for each official page, as the brief asks.
set -u

CDN="https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live"
check() {  # label url
  code=$(curl -sS -o /dev/null -I -L -m 20 -A "Mozilla/5.0 rb_errata-spike" -w "%{http_code}" "$2" 2>/dev/null)
  # Some APIs refuse HEAD with 405 (found on Riftcodex, first home run). That
  # is not a block, so retry once with a GET that discards the body.
  if [ "$code" = "405" ]; then
    code=$(curl -sS -o /dev/null -L -m 20 -A "Mozilla/5.0 rb_errata-spike" -w "%{http_code}" "$2" 2>/dev/null)
  fi
  case "$code" in
    200) state="obtained" ;;
    000) state="blocked (no connection)" ;;
    *)   state="blocked (HTTP $code)" ;;
  esac
  printf "  %-34s %-26s %s\n" "$1" "$state" "$2"
}

echo "Part 1: are the unmatched GitHub Core Rules copies Riot's own files?"
check "Core Rules v1.0 (2025-06-02)" "$CDN/c780858c1621672aea0dc6b454e9233f5a43d000.pdf"
check "Core Rules v1.1 (2025-10-01)" "$CDN/dbc96e31db9d0257b0791aafb6dbb0cd219d3efb.pdf"
check "Core Rules v1.3 (2026-03-30)" "$CDN/7affc578516386a973dffcc8132350856c5a104c.pdf"
check "Core Rules v1.4 (2026-07-16)" "$CDN/e9ac8e3d33e0f78cef296f5945aba7bc1313b086.pdf"
echo "  (200 = verified identical. 403/404 = not proof of anything; the file may"
echo "   simply live under a different path. Tell Claude either way.)"

echo
echo "Part 2: can the official pages be reached?"
N="https://playriftbound.com/en-us/news"
check "Rules Hub"                     "https://playriftbound.com/en-us/rules-hub/"
check "Patch notes: Origins"          "$N/rules-and-releases/riftbound-core-rules-patch-notes/"
check "Patch notes: Spiritforged"     "$N/rules-and-releases/riftbound-core-rules-spiritforged-patch-notes/"
check "Patch notes: Unleashed"        "$N/rules-and-releases/riftbound-core-rules-unleashed-patch-notes/"
check "Patch notes: Vendetta"         "$N/announcements/core-rules-vendetta-patch-notes/"
check "Errata: Origins"               "$N/rules-and-releases/riftbound-origins-card-errata/"
check "Errata: Spiritforged"          "$N/rules-and-releases/riftbound-spiritforged-errata/"
check "Errata: Unleashed"             "$N/rules-and-releases/unleashed-errata-updates/"
check "FAQ: Origins"                  "$N/rules-and-releases/riftbound-origins-faq/"
check "FAQ: Spiritforged"             "$N/rules-and-releases/riftbound-spiritforged-faq/"
check "FAQ: Unleashed"                "$N/rules-and-releases/unleashed-rules-faq-and-clarifications/"
check "FAQ: Vendetta"                 "$N/rules-and-releases/vendetta-rules-faq-and-clarifications/"
check "Ban list: July 2026"           "$N/announcements/july-ban-list-updates/"
check "Ban list: September 2026"      "$N/announcements/september-ban-list-updates-effective-september-18-2026/"
check "Card gallery (card data)"      "https://riftbound.leagueoflegends.com/en-us/card-gallery/"
check "Card errata PDF (2025-10-21)"  "$CDN/5bcbb23cb6131680ec8d469de6c87a3966a7622d.pdf"
check "Riot Developer Portal docs"    "https://developer.riotgames.com/docs/riftbound"
check "Riot Riftbound dev policy"     "https://developer.riotgames.com/policies/riftbound"
check "Riot Legal Jibber Jabber"      "https://www.riotgames.com/en/legal"
check "Riftcodex API (community)"     "https://api.riftcodex.com/"
