import { useEffect, useMemo, useRef, useState } from "react";
import type { StockNewsItem } from "@stock-analyst/api-types";
import { formatDate, type DailyChangeInfo } from "./utils";
import { rankDayNews } from "./newsRanking";

interface NewsSectionProps {
  news: StockNewsItem[];
  dailyChanges: DailyChangeInfo[];
  /** When set, the panel expands that date group (if collapsed) and scrolls to it. */
  scrollToDate?: string | null;
}

interface DateGroup {
  date: string;
  items: StockNewsItem[];
  info?: DailyChangeInfo;
  isAnomaly: boolean;
}

const PREVIEW_COUNT = 3;
const PANEL_HEIGHT = 480;

function formatTime(datetimeSeconds: number): string {
  const date = new Date(datetimeSeconds * 1000);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Three display states per group:
 * "collapsed"  → only the header row (default for normal days)
 * "preview"    → header + top PREVIEW_COUNT items + "Show N more" (default for anomaly days)
 * "full"       → header + all items
 */
type GroupState = "collapsed" | "preview" | "full";

export default function NewsSection({
  news,
  dailyChanges,
  scrollToDate,
}: NewsSectionProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<"all" | "movers">("all");
  // Explicit overrides; undefined means use the default for that group type.
  const [overrides, setOverrides] = useState<Record<string, GroupState>>({});

  const changeByDate = useMemo(() => {
    const map = new Map<string, DailyChangeInfo>();
    for (const info of dailyChanges) map.set(info.date, info);
    return map;
  }, [dailyChanges]);

  const coverage = useMemo(() => {
    if (news.length === 0) return null;
    let earliest = news[0].date;
    let latest = news[0].date;
    for (const item of news) {
      if (item.date < earliest) earliest = item.date;
      if (item.date > latest) latest = item.date;
    }
    return { earliest, latest };
  }, [news]);

  const allGroups: DateGroup[] = useMemo(() => {
    const byDate = new Map<string, StockNewsItem[]>();
    for (const item of news) {
      const list = byDate.get(item.date) ?? [];
      list.push(item);
      byDate.set(item.date, list);
    }

    return Array.from(byDate.entries())
      .map(([date, items]) => {
        const info = changeByDate.get(date);
        return {
          date,
          items: rankDayNews(items, items.length),
          info,
          isAnomaly: info?.isAnomaly ?? false,
        };
      })
      .sort((a, b) => (a.date < b.date ? 1 : -1));
  }, [news, changeByDate]);

  const groups = useMemo(
    () =>
      filter === "movers" ? allGroups.filter((g) => g.isAnomaly) : allGroups,
    [allGroups, filter],
  );

  const getGroupState = (group: DateGroup): GroupState => {
    if (overrides[group.date] !== undefined) return overrides[group.date];
    return group.isAnomaly ? "preview" : "collapsed";
  };

  const setGroupState = (date: string, state: GroupState) => {
    setOverrides((prev) => ({ ...prev, [date]: state }));
  };

  // Clicking the header of a collapsed normal day opens it to preview.
  // Clicking the header of a preview/full anomaly day collapses it.
  const handleHeaderClick = (group: DateGroup) => {
    const current = getGroupState(group);
    if (current === "collapsed") {
      setGroupState(group.date, "preview");
    } else {
      setGroupState(group.date, "collapsed");
    }
  };

  // Respond to chart marker clicks: ensure group is visible then scroll.
  useEffect(() => {
    if (!scrollToDate) return;
    const el = scrollRef.current;
    if (!el) return;

    // Make sure the target group is at least in preview state.
    setOverrides((prev) => {
      const current = prev[scrollToDate];
      if (current === "collapsed" || current === undefined) {
        const group = allGroups.find((g) => g.date === scrollToDate);
        if (group && !group.isAnomaly) {
          return { ...prev, [scrollToDate]: "preview" };
        }
      }
      return prev;
    });

    // Wait for the expand to render, then scroll within the panel.
    requestAnimationFrame(() => {
      const target = el.querySelector<HTMLElement>(
        `#${CSS.escape(`news-${scrollToDate}`)}`,
      );
      if (!target) return;
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [scrollToDate, allGroups]);

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 shadow-xl flex flex-col">
      {/* Panel header */}
      <div className="flex items-center justify-between px-6 pt-5 pb-3 flex-wrap gap-2 flex-shrink-0 border-b border-gray-700/60">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
          Recent News
        </h3>
        <div className="flex items-center gap-3">
          {coverage && (
            <span className="text-xs text-gray-500">
              Coverage: {formatDate(coverage.earliest)} –{" "}
              {formatDate(coverage.latest)}
            </span>
          )}
          {/* Filter chips */}
          <div className="flex rounded-lg border border-gray-700 overflow-hidden text-xs font-medium">
            <button
              onClick={() => setFilter("all")}
              className={`px-3 py-1 transition-colors ${
                filter === "all"
                  ? "bg-gray-700 text-white"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              All days
            </button>
            <button
              onClick={() => setFilter("movers")}
              className={`px-3 py-1 border-l border-gray-700 transition-colors ${
                filter === "movers"
                  ? "bg-purple-900/60 text-purple-200"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Big movers
            </button>
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <div
        ref={scrollRef}
        className="overflow-y-auto overscroll-contain"
        style={{ maxHeight: PANEL_HEIGHT }}
      >
        {groups.length === 0 ? (
          <div className="text-sm text-gray-500 py-8 text-center px-6">
            {filter === "movers"
              ? "No notable moves in the covered period."
              : "No recent news captured for this ticker yet."}
          </div>
        ) : (
          <div className="flex flex-col divide-y divide-gray-700/60">
            {groups.map((group) => {
              const state = getGroupState(group);
              const isOpen = state !== "collapsed";
              const showAll = state === "full";
              const visibleItems = showAll
                ? group.items
                : group.items.slice(0, PREVIEW_COUNT);
              const hiddenCount = group.items.length - visibleItems.length;
              const changePct = group.info?.changePct ?? null;

              return (
                <div
                  key={group.date}
                  id={`news-${group.date}`}
                  className="scroll-mt-2"
                >
                  {/* Sticky group header — acts as toggle */}
                  <button
                    onClick={() => handleHeaderClick(group)}
                    className="sticky top-0 z-10 w-full bg-gray-800 flex items-center gap-3 px-6 py-3 text-left hover:bg-gray-750 transition-colors"
                  >
                    <span className="text-sm font-bold text-white">
                      {formatDate(group.date)}
                    </span>
                    {changePct !== null && (
                      <span
                        className={`text-xs font-mono font-bold ${
                          changePct >= 0 ? "text-green-400" : "text-red-400"
                        }`}
                      >
                        {changePct >= 0 ? "+" : ""}
                        {changePct.toFixed(1)}%
                      </span>
                    )}
                    {group.isAnomaly && (
                      <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border border-purple-700 bg-purple-900/30 text-purple-300">
                        Notable Move
                      </span>
                    )}
                    <span className="text-xs text-gray-600 ml-auto">
                      {group.items.length}{" "}
                      {group.items.length === 1 ? "headline" : "headlines"}
                    </span>
                    <span className="text-gray-500 text-xs w-3 text-center flex-shrink-0">
                      {isOpen ? "▾" : "▸"}
                    </span>
                  </button>

                  {/* Expanded content */}
                  {isOpen && (
                    <div className="px-6 pb-4">
                      <ul className="space-y-2.5">
                        {visibleItems.map((item) => (
                          <li key={item.id} className="text-sm">
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-gray-200 hover:text-blue-400 transition-colors font-medium leading-snug"
                            >
                              {item.headline}
                            </a>
                            <div className="text-xs text-gray-500 mt-0.5">
                              {item.source || "Unknown source"} ·{" "}
                              {formatTime(item.datetime)}
                            </div>
                          </li>
                        ))}
                      </ul>
                      <div className="flex gap-3 mt-3">
                        {hiddenCount > 0 && (
                          <button
                            onClick={() => setGroupState(group.date, "full")}
                            className="text-xs text-blue-400 hover:text-blue-300 font-medium"
                          >
                            Show {hiddenCount} more
                          </button>
                        )}
                        {showAll && group.items.length > PREVIEW_COUNT && (
                          <button
                            onClick={() => setGroupState(group.date, "preview")}
                            className="text-xs text-gray-500 hover:text-gray-400 font-medium"
                          >
                            Show less
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
