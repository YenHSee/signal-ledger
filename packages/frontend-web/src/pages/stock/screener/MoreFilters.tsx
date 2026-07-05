import type {
  ScreenerConclusionFilter,
  ScreenerHasReportFilter,
  ScreenerMaFilter,
  ScreenerNearExtremeFilter,
} from "@stock-analyst/api-types";
import { ChevronDown } from "lucide-react";
import type { ScreenerUiState } from "./utils";

interface MoreFiltersProps {
  state: ScreenerUiState;
  onChange: (patch: Partial<ScreenerUiState>) => void;
  onClear: () => void;
  activeCount: number;
}

const inputClass =
  "w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-gray-500";
const labelClass = "text-xs text-gray-500 mb-1 block";
const selectClass =
  "w-full appearance-none bg-gray-900 border border-gray-700 rounded-lg pl-3 pr-8 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-gray-500 cursor-pointer";

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={selectClass}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown
          size={14}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
        />
      </div>
    </div>
  );
}

function NumberInput({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  value?: number;
  placeholder?: string;
  onChange: (value: number | undefined) => void;
}) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      <input
        type="number"
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(e) =>
          onChange(e.target.value === "" ? undefined : Number(e.target.value))
        }
        className={inputClass}
      />
    </div>
  );
}

const MA_OPTIONS = [
  { value: "all", label: "Any" },
  { value: "above", label: "Above" },
  { value: "below", label: "Below" },
];

const NEAR_OPTIONS = [
  { value: "all", label: "Any" },
  { value: "high", label: "Near 52W High" },
  { value: "low", label: "Near 52W Low" },
];

const REPORT_OPTIONS = [
  { value: "all", label: "All" },
  { value: "yes", label: "Has Report" },
  { value: "no", label: "No Report" },
];

export default function MoreFilters({
  state,
  onChange,
  onClear,
  activeCount,
}: MoreFiltersProps) {
  const toggleConclusion = (conclusion: ScreenerConclusionFilter) => {
    const current = state.conclusions ?? [];
    const next = current.includes(conclusion)
      ? current.filter((item) => item !== conclusion)
      : [...current, conclusion];
    onChange({ conclusions: next.length > 0 ? next : undefined, page: 1 });
  };

  return (
    <div className="mb-4">
      <div className="flex items-center gap-3 mb-3">
        <button
          type="button"
          onClick={() =>
            onChange({ showMoreFilters: !state.showMoreFilters })
          }
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
        >
          {state.showMoreFilters ? "−" : "+"} More Filters
          {activeCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-blue-600 rounded-full">
              {activeCount}
            </span>
          )}
        </button>
        {activeCount > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-xs text-gray-400 hover:text-white underline"
          >
            Clear all filters
          </button>
        )}
      </div>

      {state.showMoreFilters && (
        <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4 space-y-5">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
              Valuation
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <NumberInput
                label="MCap Min ($)"
                value={state.marketCapMin}
                placeholder="10000000000"
                onChange={(v) => onChange({ marketCapMin: v, page: 1 })}
              />
              <NumberInput
                label="MCap Max ($)"
                value={state.marketCapMax}
                placeholder="1000000000000"
                onChange={(v) => onChange({ marketCapMax: v, page: 1 })}
              />
              <NumberInput
                label="Fwd P/E Min"
                value={state.forwardPeMin}
                onChange={(v) => onChange({ forwardPeMin: v, page: 1 })}
              />
              <NumberInput
                label="Fwd P/E Max"
                value={state.forwardPeMax}
                onChange={(v) => onChange({ forwardPeMax: v, page: 1 })}
              />
              <NumberInput
                label="vs SPX Min"
                value={state.vsSpxMin}
                onChange={(v) => onChange({ vsSpxMin: v, page: 1 })}
              />
              <NumberInput
                label="vs SPX Max"
                value={state.vsSpxMax}
                onChange={(v) => onChange({ vsSpxMax: v, page: 1 })}
              />
              <NumberInput
                label="PEG Max"
                value={state.pegMax}
                onChange={(v) => onChange({ pegMax: v, page: 1 })}
              />
            </div>
          </div>

          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
              Growth & Quality
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <NumberInput
                label="Rev Growth Min (%)"
                value={state.revenueGrowthMin}
                onChange={(v) => onChange({ revenueGrowthMin: v, page: 1 })}
              />
              <NumberInput
                label="EPS Growth Min (%)"
                value={state.earningsGrowthMin}
                onChange={(v) => onChange({ earningsGrowthMin: v, page: 1 })}
              />
              <NumberInput
                label="ROE Min (%)"
                value={state.roeMin}
                onChange={(v) => onChange({ roeMin: v, page: 1 })}
              />
              <NumberInput
                label="Profit Margin Min (%)"
                value={state.profitMarginMin}
                onChange={(v) => onChange({ profitMarginMin: v, page: 1 })}
              />
              <NumberInput
                label="Div Yield Min (%)"
                value={state.dividendYieldMin}
                onChange={(v) => onChange({ dividendYieldMin: v, page: 1 })}
              />
            </div>
          </div>

          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
              Technical
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <FilterSelect
                label="Price vs MA50"
                value={state.ma50 ?? "all"}
                options={MA_OPTIONS}
                onChange={(v) =>
                  onChange({ ma50: v as ScreenerMaFilter, page: 1 })
                }
              />
              <FilterSelect
                label="Price vs MA200"
                value={state.ma200 ?? "all"}
                options={MA_OPTIONS}
                onChange={(v) =>
                  onChange({ ma200: v as ScreenerMaFilter, page: 1 })
                }
              />
              <FilterSelect
                label="52-Week Position"
                value={state.nearExtreme ?? "all"}
                options={NEAR_OPTIONS}
                onChange={(v) =>
                  onChange({
                    nearExtreme: v as ScreenerNearExtremeFilter,
                    page: 1,
                  })
                }
              />
            </div>
          </div>

          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
              AI Intel
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <FilterSelect
                label="Report Status"
                value={state.hasReport ?? "all"}
                options={REPORT_OPTIONS}
                onChange={(v) =>
                  onChange({
                    hasReport: v as ScreenerHasReportFilter,
                    page: 1,
                  })
                }
              />
              <div>
                <label className={labelClass}>Conclusion</label>
                <div className="flex gap-2">
                  {(["BUY", "HOLD", "SELL"] as ScreenerConclusionFilter[]).map(
                    (conclusion) => {
                      const active = state.conclusions?.includes(conclusion);
                      return (
                        <button
                          key={conclusion}
                          type="button"
                          onClick={() => toggleConclusion(conclusion)}
                          className={`px-2.5 py-1 text-xs font-bold rounded border transition-colors ${
                            active
                              ? "bg-blue-600 border-blue-500 text-white"
                              : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-500"
                          }`}
                        >
                          {conclusion}
                        </button>
                      );
                    },
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
