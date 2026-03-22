import type { Issue } from "@/types";

const PRIORITY_BORDER: Record<string, string> = {
  high: "border-l-red-500",
  medium: "border-l-yellow-500",
  low: "border-l-blue-400",
};

interface GanttBarProps {
  issue: Issue;
  timelineStart: Date;
  dayWidth: number;
  color: string | null;
  isClosed?: boolean;
  onClick: () => void;
}

function diffDays(a: Date, b: Date): number {
  return (b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24);
}

export default function GanttBar({
  issue,
  timelineStart,
  dayWidth,
  color,
  isClosed = false,
  onClick,
}: GanttBarProps) {
  const start = new Date(issue.start_date!);
  const end = new Date(issue.due_date!);

  const leftPx = diffDays(timelineStart, start) * dayWidth;
  // +1 to treat due_date as inclusive (3/1〜3/2 = 2 days)
  const durationDays = Math.max(diffDays(start, end) + 1, 1);
  const widthPx = durationDays * dayWidth;

  const bgColor = color ?? "#6366f1";
  const priorityBorder = isClosed
    ? "border-l-gray-400"
    : (PRIORITY_BORDER[issue.priority] ?? "border-l-gray-400");

  return (
    <div
      className={`absolute top-1 h-7 rounded cursor-pointer border-l-4 ${priorityBorder} flex items-center overflow-hidden hover:opacity-80 transition-opacity group ${
        isClosed ? "opacity-40" : ""
      }`}
      style={{
        left: leftPx,
        width: Math.max(widthPx, dayWidth * 0.5),
        backgroundColor: isClosed ? "#9ca3af" : bgColor + "cc",
      }}
      onClick={onClick}
      title={`${isClosed ? "✓ " : ""}${issue.title}\n${start.toLocaleDateString("ja-JP")} 〜 ${end.toLocaleDateString("ja-JP")}`}
    >
      <span
        className={`text-[11px] font-medium px-1.5 truncate drop-shadow-sm ${
          isClosed ? "text-gray-200 line-through" : "text-white"
        }`}
      >
        {isClosed && "✓ "}
        {issue.title}
      </span>
    </div>
  );
}
