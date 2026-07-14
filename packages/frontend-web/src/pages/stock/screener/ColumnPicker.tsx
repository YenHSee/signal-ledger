import { ALL_SCREENER_COLUMNS, type ScreenerColumnKey } from "@signal-ledger/api-types";
import { Columns3 } from "lucide-react";
import { COLUMN_LABELS, sortColumnsByCanonicalOrder } from "./utils";

interface ColumnPickerProps {
  visibleColumns: ScreenerColumnKey[];
  onChange: (columns: ScreenerColumnKey[]) => void;
}

export default function ColumnPicker({
  visibleColumns,
  onChange,
}: ColumnPickerProps) {
  const toggleColumn = (column: ScreenerColumnKey) => {
    if (visibleColumns.includes(column)) {
      if (visibleColumns.length <= 3) return;
      onChange(visibleColumns.filter((item) => item !== column));
      return;
    }
    // Re-inserted columns always land back in their fixed, canonical
    // left-to-right position instead of being appended at the end.
    onChange(sortColumnsByCanonicalOrder([...visibleColumns, column]));
  };

  return (
    <div className="relative group">
      <button
        type="button"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
      >
        <Columns3 size={14} />
        Columns
      </button>
      <div className="absolute right-0 top-full mt-1 z-20 hidden group-hover:block group-focus-within:block">
        <div className="bg-gray-800 border border-gray-700 rounded-lg shadow-xl p-3 min-w-[180px]">
          {ALL_SCREENER_COLUMNS.map((column) => (
            <label
              key={column}
              className="flex items-center gap-2 py-1.5 text-sm text-gray-300 cursor-pointer hover:text-white"
            >
              <input
                type="checkbox"
                checked={visibleColumns.includes(column)}
                onChange={() => toggleColumn(column)}
                className="rounded border-gray-600"
              />
              {COLUMN_LABELS[column]}
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
