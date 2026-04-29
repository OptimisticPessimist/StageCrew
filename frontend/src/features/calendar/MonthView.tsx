import type { EventListItem } from "@/types";
import {
  EVENT_TYPE_COLORS,
  buildMonthGrid,
  formatTime,
  isSameDay,
  localDateISO,
} from "./calendarUtils";

interface Props {
  year: number;
  month: number; // 0-11
  events: EventListItem[];
  onEventClick: (eventId: string) => void;
  onDayClick: (dateISO: string) => void;
}

const WEEK_LABELS = ["日", "月", "火", "水", "木", "金", "土"];

export default function MonthView({
  year,
  month,
  events,
  onEventClick,
  onDayClick,
}: Props) {
  const cells = buildMonthGrid(year, month);
  const today = new Date();

  // 日付(YYYY-MM-DD)ごとにイベントをまとめる
  const eventsByDay = new Map<string, EventListItem[]>();
  for (const ev of events) {
    const iso = localDateISO(new Date(ev.start_at));
    const arr = eventsByDay.get(iso) ?? [];
    arr.push(ev);
    eventsByDay.set(iso, arr);
  }
  for (const arr of eventsByDay.values()) {
    arr.sort((a, b) => a.start_at.localeCompare(b.start_at));
  }

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="grid grid-cols-7 border-b bg-gray-50 text-xs font-medium text-gray-600">
        {WEEK_LABELS.map((label, i) => (
          <div
            key={label}
            className={`px-2 py-2 text-center ${i === 0 ? "text-red-600" : i === 6 ? "text-blue-600" : ""}`}
          >
            {label}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 auto-rows-fr">
        {cells.map((cell) => {
          const dayEvents = eventsByDay.get(cell.iso) ?? [];
          const isToday = isSameDay(cell.date, today);
          const dow = cell.date.getDay();
          return (
            <div
              key={cell.iso}
              onClick={() => onDayClick(cell.iso)}
              className={`min-h-[96px] border-t border-l p-1 cursor-pointer hover:bg-indigo-50/40 ${
                cell.isCurrentMonth ? "bg-white" : "bg-gray-50 text-gray-400"
              }`}
            >
              <div
                className={`text-xs font-medium mb-1 flex items-center justify-between ${
                  isToday ? "text-indigo-600 font-bold" : ""
                } ${dow === 0 && cell.isCurrentMonth ? "text-red-600" : ""} ${
                  dow === 6 && cell.isCurrentMonth ? "text-blue-600" : ""
                }`}
              >
                <span
                  className={
                    isToday
                      ? "inline-flex items-center justify-center w-5 h-5 rounded-full bg-indigo-600 text-white text-[11px]"
                      : ""
                  }
                >
                  {cell.date.getDate()}
                </span>
              </div>
              <div className="space-y-0.5">
                {dayEvents.slice(0, 3).map((ev) => (
                  <button
                    key={ev.id}
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onEventClick(ev.id);
                    }}
                    className={`block w-full text-left text-[11px] leading-tight px-1.5 py-0.5 rounded border truncate ${
                      EVENT_TYPE_COLORS[ev.event_type] ??
                      EVENT_TYPE_COLORS.other
                    }`}
                    title={ev.title}
                  >
                    {!ev.is_all_day && (
                      <span className="font-medium">
                        {formatTime(ev.start_at)}{" "}
                      </span>
                    )}
                    {ev.title}
                  </button>
                ))}
                {dayEvents.length > 3 && (
                  <div className="text-[11px] text-gray-500 px-1">
                    +{dayEvents.length - 3} 件
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
