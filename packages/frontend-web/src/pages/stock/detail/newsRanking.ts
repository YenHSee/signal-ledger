import type { StockNewsItem } from "@signal-ledger/api-types";

/**
 * Lower number = more reputable / less likely to be filler wire content.
 * Sources not listed fall back to DEFAULT_TIER.
 */
const SOURCE_TIERS: Record<string, number> = {
  reuters: 1,
  bloomberg: 1,
  "wall street journal": 1,
  "the wall street journal": 1,
  "associated press": 1,
  cnbc: 2,
  marketwatch: 2,
  barrons: 2,
  "barron's": 2,
  "yahoo finance": 3,
  yahoo: 3,
  "seeking alpha": 3,
  seekingalpha: 3,
  "business wire": 3,
  businesswire: 3,
  "pr newswire": 3,
  prnewswire: 3,
  benzinga: 4,
  "motley fool": 4,
  "the motley fool": 4,
  zacks: 4,
};

const DEFAULT_TIER = 5;

function getSourceTier(source: string): number {
  return SOURCE_TIERS[source.trim().toLowerCase()] ?? DEFAULT_TIER;
}

/**
 * Collapses near-duplicate wire headlines (e.g. the same story syndicated by
 * multiple outlets) down to a normalized key for dedup purposes.
 */
function normalizeHeadline(headline: string): string {
  return headline
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Dedupes same-story headlines (keeping the most reputable source) and
 * ranks the remainder by source tier, then recency. Used to pick the
 * top headlines to surface in a chart marker tooltip for a given day.
 */
export function rankDayNews(
  items: StockNewsItem[],
  limit = 3,
): StockNewsItem[] {
  const bestByHeadline = new Map<string, StockNewsItem>();

  for (const item of items) {
    const key = normalizeHeadline(item.headline);
    if (!key) continue;

    const existing = bestByHeadline.get(key);
    if (!existing) {
      bestByHeadline.set(key, item);
      continue;
    }

    const existingTier = getSourceTier(existing.source);
    const candidateTier = getSourceTier(item.source);
    const isBetterTier = candidateTier < existingTier;
    const isEarlierAtSameTier =
      candidateTier === existingTier && item.datetime < existing.datetime;
    if (isBetterTier || isEarlierAtSameTier) {
      bestByHeadline.set(key, item);
    }
  }

  return Array.from(bestByHeadline.values())
    .sort((a, b) => {
      const tierDiff = getSourceTier(a.source) - getSourceTier(b.source);
      if (tierDiff !== 0) return tierDiff;
      return b.datetime - a.datetime;
    })
    .slice(0, limit);
}
