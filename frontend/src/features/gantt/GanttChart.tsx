import { useRef } from "react";
import type { Issue, ProductionPhase, Milestone } from "@/types";
import type { DepartmentGroup } from "./hooks/useGanttData";
import GanttTimelineHeader from "./GanttTimelineHeader";
import GanttBar from "./GanttBar";

interface GanttChartProps {
  groups: DepartmentGroup[];
  phases: ProductionPhase[];
  milestones: Milestone[];
  timelineStart: Date;
  timelineEnd: Date;
  dayWidth: number;
  onIssueClick: (issue: Issue) => void;
}

function diffDays(a: Date, b: Date): number {
  return (b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24);
}

const ROW_HEIGHT = 36;
const DEPT_HEADER_HEIGHT = 28;
const LABEL_WIDTH = 200;

export default function GanttChart({
  groups,
  phases,
  milestones,
  timelineStart,
  timelineEnd,
  dayWidth,
  onIssueClick,
}: GanttChartProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const totalDays = Math.ceil(diffDays(timelineStart, timelineEnd));
  const timelineWidth = totalDays * dayWidth;

  // Today position
  const today = new Date();
  const todayOffset = diffDays(timelineStart, today) * dayWidth;
  const showToday = todayOffset >= 0 && todayOffset <= timelineWidth;

  // Calculate total rows for background elements
  let totalContentHeight = 0;
  for (const group of groups) {
    totalContentHeight += DEPT_HEADER_HEIGHT + group.issues.length * ROW_HEIGHT;
  }

  return (
    <div className="flex h-full border border-gray-300 rounded-lg overflow-hidden bg-white">
      {/* Left labels column */}
      <div
        className="shrink-0 border-r border-gray-300 bg-gray-50 overflow-y-auto"
        style={{ width: LABEL_WIDTH }}
      >
        {/* Header spacer */}
        <div className="h-12 border-b border-gray-300" />
        {groups.map((group) => (
          <div key={group.department?.id ?? "__none"}>
            {/* Department header */}
            <div
              className="flex items-center px-3 text-xs font-bold text-gray-700 border-b border-gray-200"
              style={{
                height: DEPT_HEADER_HEIGHT,
                backgroundColor: group.department?.color
                  ? group.department.color + "22"
                  : "#f9fafb",
              }}
            >
              <span
                className="w-2.5 h-2.5 rounded-full mr-2 shrink-0"
                style={{
                  backgroundColor: group.department?.color ?? "#9ca3af",
                }}
              />
              {group.department?.name ?? "未分類"}
            </div>
            {/* Issue rows */}
            {group.issues.map((issue) => (
              <div
                key={issue.id}
                className="flex items-center px-3 text-xs text-gray-600 border-b border-gray-100 truncate cursor-pointer hover:bg-gray-100"
                style={{ height: ROW_HEIGHT }}
                onClick={() => onIssueClick(issue)}
              >
                {issue.title}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Right timeline area */}
      <div className="flex-1 overflow-auto" ref={scrollRef}>
        <div style={{ width: timelineWidth, minHeight: "100%" }} className="relative">
          {/* Timeline header */}
          <GanttTimelineHeader
            timelineStart={timelineStart}
            totalDays={totalDays}
            dayWidth={dayWidth}
          />

          {/* Content area */}
          <div className="relative" style={{ height: totalContentHeight }}>
            {/* Weekend background stripes */}
            {Array.from({ length: totalDays }, (_, i) => {
              const d = new Date(timelineStart);
              d.setDate(d.getDate() + i);
              const dow = d.getDay();
              if (dow !== 0 && dow !== 6) return null;
              return (
                <div
                  key={`weekend-${i}`}
                  className="absolute top-0 bottom-0 bg-gray-50"
                  style={{ left: i * dayWidth, width: dayWidth }}
                />
              );
            })}

            {/* Phase background bands */}
            {phases.map((phase) => {
              if (!phase.start_date || !phase.end_date) return null;
              const phaseStart = diffDays(timelineStart, new Date(phase.start_date)) * dayWidth;
              const phaseWidth = Math.max(
                diffDays(new Date(phase.start_date), new Date(phase.end_date)),
                1,
              ) * dayWidth;
              return (
                <div
                  key={phase.id}
                  className="absolute top-0 bottom-0 border-l border-r border-dashed border-indigo-200"
                  style={{
                    left: phaseStart,
                    width: phaseWidth,
                    backgroundColor: "rgba(99, 102, 241, 0.05)",
                  }}
                >
                  <div className="sticky top-12 text-[10px] text-indigo-400 font-medium px-1 truncate">
                    {phase.name}
                  </div>
                </div>
              );
            })}

            {/* Milestone markers */}
            {milestones.map((ms) => {
              if (!ms.date) return null;
              const offset = diffDays(timelineStart, new Date(ms.date)) * dayWidth;
              const msColor = ms.color ?? "#f59e0b";
              return (
                <div
                  key={ms.id}
                  className="absolute top-0 bottom-0 pointer-events-none"
                  style={{ left: offset, width: 0 }}
                >
                  <div
                    className="absolute top-0 bottom-0 border-l-2 border-dashed"
                    style={{ borderColor: msColor }}
                  />
                  <div
                    className="absolute -top-0.5 -left-2.5 w-5 h-5 rotate-45 rounded-sm"
                    style={{ backgroundColor: msColor }}
                    title={ms.name}
                  />
                  <div
                    className="absolute top-5 -left-8 text-[10px] font-medium w-16 text-center truncate"
                    style={{ color: msColor }}
                  >
                    {ms.name}
                  </div>
                </div>
              );
            })}

            {/* Today line */}
            {showToday && (
              <div
                className="absolute top-0 bottom-0 border-l-2 border-dashed border-red-400 z-10 pointer-events-none"
                style={{ left: todayOffset }}
              >
                <div className="absolute -top-0.5 -left-3 bg-red-400 text-white text-[9px] px-1 rounded">
                  今日
                </div>
              </div>
            )}

            {/* Issue bars */}
            {(() => {
              let yOffset = 0;
              return groups.map((group) => {
                const groupY = yOffset;
                yOffset += DEPT_HEADER_HEIGHT;
                const issueElements = group.issues.map((issue, idx) => {
                  const rowY = groupY + DEPT_HEADER_HEIGHT + idx * ROW_HEIGHT;
                  return (
                    <div
                      key={issue.id}
                      className="absolute w-full"
                      style={{ top: rowY, height: ROW_HEIGHT }}
                    >
                      <GanttBar
                        issue={issue}
                        timelineStart={timelineStart}
                        dayWidth={dayWidth}
                        color={group.department?.color ?? null}
                        onClick={() => onIssueClick(issue)}
                      />
                    </div>
                  );
                });
                yOffset += group.issues.length * ROW_HEIGHT;
                return (
                  <div key={group.department?.id ?? "__none"}>
                    {/* Department header row - visual separator */}
                    <div
                      className="absolute w-full border-b border-gray-200"
                      style={{
                        top: groupY,
                        height: DEPT_HEADER_HEIGHT,
                        backgroundColor: group.department?.color
                          ? group.department.color + "11"
                          : "transparent",
                      }}
                    />
                    {issueElements}
                  </div>
                );
              });
            })()}
          </div>
        </div>
      </div>
    </div>
  );
}
