import { useMemo } from "react";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { getPageRange } from "./utils";

const PAGE_SIZE_OPTIONS = [10, 50, 100];

interface PaginationProps {
  page: number;
  totalPages: number;
  limit: number;
  total: number;
  loading: boolean;
  onPageChange: (page: number) => void;
  onLimitChange: (limit: number) => void;
}

const navButtonClass =
  "inline-flex items-center justify-center w-8 h-8 rounded-lg border border-gray-700 bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white disabled:opacity-40 disabled:hover:bg-gray-800 disabled:hover:text-gray-300 transition-colors";

export default function Pagination({
  page,
  totalPages,
  limit,
  total,
  loading,
  onPageChange,
  onLimitChange,
}: PaginationProps) {
  const pageRange = useMemo(
    () => getPageRange(page, totalPages),
    [page, totalPages],
  );

  const startItem = total === 0 ? 0 : (page - 1) * limit + 1;
  const endItem = Math.min(page * limit, total);

  return (
    <div className="mt-6 flex flex-wrap items-center justify-between gap-4 text-sm">
      <div className="flex items-center gap-3 text-gray-400">
        <div className="flex items-center gap-2">
          <span>Rows per page</span>
          <div className="relative">
            <select
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              className="appearance-none bg-gray-800 border border-gray-700 rounded-lg pl-3 pr-7 py-1.5 text-gray-200 focus:outline-none focus:border-gray-500 cursor-pointer"
            >
              {PAGE_SIZE_OPTIONS.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
            <ChevronDown
              size={12}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none"
            />
          </div>
        </div>

        <span className="text-gray-500">
          {total === 0
            ? "No results"
            : `${startItem.toLocaleString()}–${endItem.toLocaleString()} of ${total.toLocaleString()}`}
        </span>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onPageChange(1)}
            disabled={page === 1 || loading}
            className={navButtonClass}
            aria-label="First page"
          >
            <ChevronsLeft size={16} />
          </button>
          <button
            type="button"
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page === 1 || loading}
            className={navButtonClass}
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>

          {pageRange.map((item, idx) =>
            item === "ellipsis" ? (
              <span
                key={`ellipsis-${idx}`}
                className="w-8 h-8 inline-flex items-center justify-center text-gray-500"
              >
                …
              </span>
            ) : (
              <button
                key={item}
                type="button"
                onClick={() => onPageChange(item)}
                disabled={loading}
                className={`inline-flex items-center justify-center w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                  item === page
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 border border-gray-700 text-gray-300 hover:bg-gray-700 hover:text-white"
                } disabled:opacity-40`}
              >
                {item}
              </button>
            ),
          )}

          <button
            type="button"
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            disabled={page === totalPages || loading}
            className={navButtonClass}
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
          <button
            type="button"
            onClick={() => onPageChange(totalPages)}
            disabled={page === totalPages || loading}
            className={navButtonClass}
            aria-label="Last page"
          >
            <ChevronsRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
