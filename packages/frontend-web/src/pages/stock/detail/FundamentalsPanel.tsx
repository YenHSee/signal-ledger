import type { ReactNode } from "react";
import type { FundamentalsProfile } from "@signal-ledger/api-types";
import {
  formatCurrency,
  formatDate,
  formatPercent,
  formatRatio,
  getMaStatus,
  getRangePosition,
} from "./utils";

interface FundamentalsPanelProps {
  fundamentalsProfile: FundamentalsProfile | null;
  riskLevel: string | null;
}

function Row({
  label,
  value,
  valueClassName = "text-white",
}: {
  label: string;
  value: ReactNode;
  valueClassName?: string;
}) {
  return (
    <li className="flex justify-between items-center text-sm">
      <span className="text-gray-400">{label}</span>
      <span className={`font-mono font-bold ${valueClassName}`}>{value}</span>
    </li>
  );
}

function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mt-5 mb-2 first:mt-0">
      {children}
    </h4>
  );
}

function AnalystRatingBar({
  fundamentalsProfile,
}: {
  fundamentalsProfile: FundamentalsProfile;
}) {
  const { strongBuy, buy, hold, sell, strongSell } =
    fundamentalsProfile.analystRatings;
  const total = strongBuy + buy + hold + sell + strongSell;

  if (total === 0) {
    return <div className="text-sm text-gray-500">No analyst coverage</div>;
  }

  const segments = [
    { label: "Strong Buy", count: strongBuy, color: "bg-green-500" },
    { label: "Buy", count: buy, color: "bg-green-700" },
    { label: "Hold", count: hold, color: "bg-yellow-600" },
    { label: "Sell", count: sell, color: "bg-red-700" },
    { label: "Strong Sell", count: strongSell, color: "bg-red-500" },
  ];

  return (
    <div>
      <div className="flex h-2.5 w-full rounded-full overflow-hidden bg-gray-900">
        {segments.map((segment) =>
          segment.count > 0 ? (
            <div
              key={segment.label}
              className={segment.color}
              style={{ width: `${(segment.count / total) * 100}%` }}
              title={`${segment.label}: ${segment.count}`}
            />
          ) : null,
        )}
      </div>
      <div className="flex justify-between text-[10px] text-gray-500 mt-1.5">
        <span>{total} analysts</span>
        <span>
          {strongBuy + buy} Buy · {hold} Hold · {sell + strongSell} Sell
        </span>
      </div>
    </div>
  );
}

function RangeBar({
  fundamentalsProfile,
}: {
  fundamentalsProfile: FundamentalsProfile;
}) {
  const { week52High, week52Low } = fundamentalsProfile.technical;
  const position = getRangePosition(
    fundamentalsProfile.price,
    week52Low,
    week52High,
  );

  return (
    <div>
      <div className="relative h-2 w-full rounded-full bg-gray-900">
        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-red-700/40 via-gray-700 to-green-700/40" />
        {position !== null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-blue-400 border-2 border-gray-900"
            style={{ left: `${position}%` }}
          />
        )}
      </div>
      <div className="flex justify-between text-[10px] text-gray-500 mt-1.5">
        <span>{formatCurrency(week52Low)}</span>
        <span>52-Week Range</span>
        <span>{formatCurrency(week52High)}</span>
      </div>
    </div>
  );
}

export default function FundamentalsPanel({
  fundamentalsProfile,
  riskLevel,
}: FundamentalsPanelProps) {
  if (!fundamentalsProfile) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b border-gray-700 pb-2">
          Fundamentals
        </h3>
        <div className="text-sm text-gray-500">
          Fundamentals data unavailable.
        </div>
      </div>
    );
  }

  const ma50Status = getMaStatus(
    fundamentalsProfile.price,
    fundamentalsProfile.technical.ma50,
  );
  const ma200Status = getMaStatus(
    fundamentalsProfile.price,
    fundamentalsProfile.technical.ma200,
  );

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
      <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2 border-b border-gray-700 pb-2">
        Fundamentals
      </h3>

      <SectionHeading>Valuation</SectionHeading>
      <ul className="space-y-2.5">
        <Row
          label="Trailing P/E"
          value={formatRatio(fundamentalsProfile.valuation.trailingPe)}
        />
        <Row
          label="Forward P/E"
          value={formatRatio(fundamentalsProfile.valuation.forwardPe)}
        />
        <Row
          label="PEG Ratio"
          value={formatRatio(fundamentalsProfile.valuation.pegRatio, "")}
          valueClassName={
            fundamentalsProfile.valuation.pegRatio !== null &&
            fundamentalsProfile.valuation.pegRatio > 2
              ? "px-2 py-0.5 rounded text-xs bg-red-900/50 text-red-400 border border-red-800"
              : "text-white"
          }
        />
        <Row
          label="P/B Ratio"
          value={formatRatio(fundamentalsProfile.valuation.priceToBook, "")}
        />
        <Row
          label="P/S Ratio"
          value={formatRatio(fundamentalsProfile.valuation.priceToSales, "")}
        />
        <Row
          label="EV/EBITDA"
          value={formatRatio(fundamentalsProfile.valuation.evToEbitda, "")}
        />
      </ul>

      <SectionHeading>Profitability & Growth</SectionHeading>
      <ul className="space-y-2.5">
        <Row
          label="Profit Margin"
          value={formatPercent(fundamentalsProfile.profitability.profitMargin)}
        />
        <Row
          label="ROE"
          value={formatPercent(
            fundamentalsProfile.profitability.returnOnEquity,
          )}
        />
        <Row
          label="Revenue Growth YoY"
          value={formatPercent(
            fundamentalsProfile.profitability.revenueGrowthYoy,
          )}
          valueClassName={
            (fundamentalsProfile.profitability.revenueGrowthYoy ?? 0) >= 0
              ? "text-green-400"
              : "text-red-400"
          }
        />
      </ul>

      <SectionHeading>Income</SectionHeading>
      <ul className="space-y-2.5">
        <Row
          label="Dividend Yield"
          value={formatPercent(fundamentalsProfile.income.dividendYield)}
        />
        <Row
          label="Dividend / Share"
          value={formatCurrency(fundamentalsProfile.income.dividendPerShare)}
        />
        <Row
          label="Ex-Dividend Date"
          value={formatDate(fundamentalsProfile.income.exDividendDate)}
        />
      </ul>

      <SectionHeading>Ownership & Sentiment</SectionHeading>
      <ul className="space-y-2.5 mb-3">
        <Row
          label="Institutional %"
          value={formatPercent(
            fundamentalsProfile.ownership.percentInstitutions,
          )}
        />
        <Row
          label="Insider %"
          value={formatPercent(fundamentalsProfile.ownership.percentInsiders)}
        />
      </ul>
      <AnalystRatingBar fundamentalsProfile={fundamentalsProfile} />

      <SectionHeading>Technical</SectionHeading>
      <div className="mb-3">
        <RangeBar fundamentalsProfile={fundamentalsProfile} />
      </div>
      <ul className="space-y-2.5">
        <Row
          label="vs MA50"
          value={ma50Status.label}
          valueClassName={ma50Status.color}
        />
        <Row
          label="vs MA200"
          value={ma200Status.label}
          valueClassName={ma200Status.color}
        />
        <Row
          label="Beta"
          value={formatRatio(fundamentalsProfile.technical.beta, "")}
        />
        <Row
          label="Risk Profile"
          value={riskLevel || "Unknown"}
          valueClassName="text-yellow-400 uppercase"
        />
      </ul>
    </div>
  );
}
