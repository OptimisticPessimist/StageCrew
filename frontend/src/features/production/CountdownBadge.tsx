import { useProduction } from "./hooks/useProduction";

interface CountdownBadgeProps {
  orgId: string;
  productionId: string;
}

/** ISO datetime文字列から日付部分だけ取り出してローカルDate（午前0時）を返す */
export function parseLocalDate(isoString: string): Date {
  const [datePart] = isoString.split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function calendarDays(from: Date, to: Date): number {
  return Math.round((to.getTime() - from.getTime()) / 86_400_000);
}

export default function CountdownBadge({ orgId, productionId }: CountdownBadgeProps) {
  const { data: production } = useProduction(orgId, productionId);

  if (!production?.opening_date) return null;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const opening = parseLocalDate(production.opening_date);
  const closing = production.closing_date ? parseLocalDate(production.closing_date) : null;

  const daysToOpening = calendarDays(today, opening);
  const daysToClosing = closing ? calendarDays(today, closing) : null;

  // 初日より前
  if (daysToOpening > 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
        本番まであと {daysToOpening} 日
      </span>
    );
  }

  // 初日当日
  if (daysToOpening === 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
        本番当日！
      </span>
    );
  }

  // 公演期間中（初日〜千秋楽）
  if (daysToClosing !== null && daysToClosing > 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
        本番期間中（千秋楽まであと {daysToClosing} 日）
      </span>
    );
  }

  // 千秋楽当日
  if (daysToClosing === 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
        千秋楽当日！
      </span>
    );
  }

  // 千秋楽後 → 非表示
  return null;
}
