export interface MonthCell {
  date: Date;
  isCurrentMonth: boolean;
  iso: string; // YYYY-MM-DD (local)
}

export function startOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

export function addDays(d: Date, days: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + days);
  return x;
}

export function localDateISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

/** 日曜始まり・6週間 42セルの月間グリッドを生成。 */
export function buildMonthGrid(year: number, month: number): MonthCell[] {
  const first = new Date(year, month, 1);
  const startOffset = first.getDay(); // 0=Sun
  const gridStart = addDays(first, -startOffset);
  const cells: MonthCell[] = [];
  for (let i = 0; i < 42; i++) {
    const d = addDays(gridStart, i);
    cells.push({
      date: d,
      isCurrentMonth: d.getMonth() === month,
      iso: localDateISO(d),
    });
  }
  return cells;
}

export function monthLabel(year: number, month: number): string {
  return `${year}年${month + 1}月`;
}

export function formatTime(utcIso: string): string {
  const d = new Date(utcIso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function formatDateTime(utcIso: string): string {
  const d = new Date(utcIso);
  const md = `${d.getMonth() + 1}/${d.getDate()}`;
  const hm = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  return `${md} ${hm}`;
}

/** `<input type="datetime-local">` 用のローカル日時文字列に変換。 */
export function toLocalInputValue(utcIso: string | null | undefined): string {
  if (!utcIso) return "";
  const d = new Date(utcIso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${day}T${hh}:${mm}`;
}

/** datetime-local の文字列をサーバー送信用 UTC ISO 文字列に変換。 */
export function fromLocalInputValue(localValue: string): string {
  const d = new Date(localValue);
  return d.toISOString();
}

/** 月グリッド全体をカバーする UTC 範囲 [start, end)。 */
export function monthGridRange(year: number, month: number): {
  startFrom: string;
  startTo: string;
} {
  const cells = buildMonthGrid(year, month);
  const start = startOfDay(cells[0].date);
  const end = startOfDay(addDays(cells[cells.length - 1].date, 1));
  return { startFrom: start.toISOString(), startTo: end.toISOString() };
}

export const EVENT_TYPE_LABELS: Record<string, string> = {
  rehearsal: "稽古",
  performance: "本番",
  meeting: "打ち合わせ",
  other: "その他",
};

export const EVENT_TYPE_COLORS: Record<string, string> = {
  rehearsal: "bg-indigo-100 text-indigo-800 border-indigo-300",
  performance: "bg-rose-100 text-rose-800 border-rose-300",
  meeting: "bg-emerald-100 text-emerald-800 border-emerald-300",
  other: "bg-gray-100 text-gray-800 border-gray-300",
};

export const RSVP_LABELS: Record<string, string> = {
  pending: "未回答",
  accepted: "参加",
  declined: "不参加",
  tentative: "未定",
};

/**
 * URL を厳密に検証し、http/https スキームかつ有効な hostname を持つ場合のみ true を返す。
 * `new URL()` でパースすることで、制御文字・不正形式・`javascript:` などの危険スキームを排除する。
 */
export function isSafeHttpUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  try {
    const parsed = new URL(url.trim());
    return (parsed.protocol === "http:" || parsed.protocol === "https:") && parsed.hostname.length > 0;
  } catch {
    return false;
  }
}
