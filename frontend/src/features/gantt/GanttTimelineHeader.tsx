interface GanttTimelineHeaderProps {
  timelineStart: Date;
  totalDays: number;
  dayWidth: number;
}

export default function GanttTimelineHeader({
  timelineStart,
  totalDays,
  dayWidth,
}: GanttTimelineHeaderProps) {
  const days: Date[] = [];
  for (let i = 0; i < totalDays; i++) {
    const d = new Date(timelineStart);
    d.setDate(d.getDate() + i);
    days.push(d);
  }

  // Group days by month
  const months: { label: string; days: number; startIndex: number }[] = [];
  let currentMonth = "";
  for (let i = 0; i < days.length; i++) {
    const d = days[i];
    const label = `${d.getFullYear()}年${d.getMonth() + 1}月`;
    if (label !== currentMonth) {
      months.push({ label, days: 1, startIndex: i });
      currentMonth = label;
    } else {
      months[months.length - 1].days++;
    }
  }

  return (
    <div className="sticky top-0 z-20 bg-white border-b border-gray-300">
      {/* Month row */}
      <div className="flex border-b border-gray-200" style={{ height: 24 }}>
        {months.map((m) => (
          <div
            key={`${m.label}-${m.startIndex}`}
            className="text-xs font-semibold text-gray-700 border-r border-gray-200 flex items-center px-1 overflow-hidden"
            style={{ width: m.days * dayWidth, minWidth: 0 }}
          >
            {m.label}
          </div>
        ))}
      </div>
      {/* Day row */}
      <div className="flex" style={{ height: 24 }}>
        {days.map((d, i) => {
          const dow = d.getDay();
          const isWeekend = dow === 0 || dow === 6;
          return (
            <div
              key={i}
              className={`text-[10px] text-center border-r border-gray-200 flex items-center justify-center ${
                isWeekend ? "bg-gray-100 text-gray-400" : "text-gray-600"
              }`}
              style={{ width: dayWidth, minWidth: 0 }}
            >
              {dayWidth >= 20 ? d.getDate() : i % 2 === 0 ? d.getDate() : ""}
            </div>
          );
        })}
      </div>
    </div>
  );
}
