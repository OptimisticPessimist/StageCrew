import type { EventListItem } from "@/types";
import {
  EVENT_TYPE_COLORS,
  addDays,
  formatTime,
  isSameDay,
  localDateISO,
  startOfDay,
} from "./calendarUtils";

interface Props {
  weekStart: Date; // 日曜
  events: EventListItem[];
  onEventClick: (eventId: string) => void;
  onSlotClick: (dateISO: string, hour: number) => void;
}

const WEEK_LABELS = ["日", "月", "火", "水", "木", "金", "土"];
const HOUR_RANGE = Array.from({ length: 15 }, (_, i) => 8 + i); // 8:00-22:00
const SLOT_HEIGHT = 36; // px per hour

export default function WeekView({
  weekStart,
  events,
  onEventClick,
  onSlotClick,
}: Props) {
  const start = startOfDay(weekStart);
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i));
  const today = new Date();

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      {/* 曜日ヘッダー */}
      <div className="grid grid-cols-[64px_repeat(7,1fr)] border-b bg-gray-50 text-xs font-medium text-gray-600">
        <div />
        {days.map((d, i) => {
          const isToday = isSameDay(d, today);
          return (
            <div
              key={d.toISOString()}
              className={`px-2 py-2 text-center border-l ${
                isToday ? "bg-indigo-50" : ""
              } ${i === 0 ? "text-red-600" : i === 6 ? "text-blue-600" : ""}`}
            >
              <div>{WEEK_LABELS[i]}</div>
              <div
                className={`font-bold text-sm ${
                  isToday ? "text-indigo-600" : "text-gray-900"
                }`}
              >
                {d.getMonth() + 1}/{d.getDate()}
              </div>
            </div>
          );
        })}
      </div>

      {/* 時間グリッド */}
      <div className="grid grid-cols-[64px_repeat(7,1fr)] relative">
        <div className="flex flex-col">
          {HOUR_RANGE.map((h) => (
            <div
              key={h}
              style={{ height: SLOT_HEIGHT }}
              className="text-[10px] text-gray-500 text-right pr-1 border-t"
            >
              {String(h).padStart(2, "0")}:00
            </div>
          ))}
        </div>
        {days.map((d) => (
          <DayColumn
            key={d.toISOString()}
            day={d}
            events={events}
            onEventClick={onEventClick}
            onSlotClick={onSlotClick}
          />
        ))}
      </div>
    </div>
  );
}

function DayColumn({
  day,
  events,
  onEventClick,
  onSlotClick,
}: {
  day: Date;
  events: EventListItem[];
  onEventClick: (id: string) => void;
  onSlotClick: (iso: string, hour: number) => void;
}) {
  const dayISO = localDateISO(day);
  const dayEvents = events.filter((ev) => {
    const start = new Date(ev.start_at);
    return isSameDay(start, day);
  });

  return (
    <div className="relative border-l">
      {HOUR_RANGE.map((h) => (
        <div
          key={h}
          onClick={() => onSlotClick(dayISO, h)}
          style={{ height: SLOT_HEIGHT }}
          className="border-t hover:bg-indigo-50/40 cursor-pointer"
        />
      ))}
      {dayEvents.map((ev) => {
        const start = new Date(ev.start_at);
        const end = ev.end_at
          ? new Date(ev.end_at)
          : new Date(start.getTime() + 60 * 60 * 1000);
        const startHour = start.getHours() + start.getMinutes() / 60;
        const endHour = end.getHours() + end.getMinutes() / 60;
        const top = Math.max(0, (startHour - HOUR_RANGE[0]) * SLOT_HEIGHT);
        const height = Math.max(
          18,
          (endHour - startHour) * SLOT_HEIGHT - 2,
        );
        return (
          <button
            key={ev.id}
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onEventClick(ev.id);
            }}
            style={{ top, height }}
            className={`absolute left-1 right-1 text-left text-[11px] px-1.5 py-0.5 rounded border overflow-hidden ${
              EVENT_TYPE_COLORS[ev.event_type] ?? EVENT_TYPE_COLORS.other
            }`}
            title={ev.title}
          >
            <div className="font-medium truncate">{ev.title}</div>
            {!ev.is_all_day && (
              <div className="text-[10px] opacity-80">
                {formatTime(ev.start_at)}
                {ev.end_at ? ` - ${formatTime(ev.end_at)}` : ""}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
