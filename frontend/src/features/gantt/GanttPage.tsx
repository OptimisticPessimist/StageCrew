import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useGanttData } from "./hooks/useGanttData";
import { useStatuses } from "@/features/kanban/hooks/useStatuses";
import { useIssueDetail, useUpdateIssueStatus } from "@/features/kanban/hooks/useIssues";
import GanttChart from "./GanttChart";
import IssueDetailPanel from "@/features/kanban/IssueDetailPanel";
import type { Issue } from "@/types";

type ViewMode = "week" | "month";

const DAY_WIDTH: Record<ViewMode, number> = {
  week: 40,
  month: 12,
};

export default function GanttPage() {
  const { orgId, productionId } = useParams<{
    orgId: string;
    productionId: string;
  }>();

  const [viewMode, setViewMode] = useState<ViewMode>("week");
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [showUnscheduled, setShowUnscheduled] = useState(false);

  const {
    scheduledGroups,
    unscheduledIssues,
    phases,
    milestones,
    timelineStart,
    timelineEnd,
    isLoading,
  } = useGanttData(orgId!, productionId!);

  const { data: statuses = [] } = useStatuses(orgId!, productionId!);
  const { data: selectedIssue } = useIssueDetail(
    orgId!,
    productionId!,
    selectedIssueId,
  );
  const updateStatus = useUpdateIssueStatus(orgId!, productionId!);

  const handleIssueClick = (issue: Issue) => {
    setSelectedIssueId(issue.id);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* ヘッダー */}
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-gray-400 hover:text-gray-600 text-sm">
            &larr; ホーム
          </Link>
          <h1 className="text-lg font-bold text-gray-900">ガントチャート</h1>
          <Link
            to={`/organizations/${orgId}/productions/${productionId}/board`}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            カンバンボード
          </Link>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-gray-300 overflow-hidden">
            <button
              onClick={() => setViewMode("week")}
              className={`px-3 py-1.5 text-sm font-medium ${
                viewMode === "week"
                  ? "bg-indigo-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              週表示
            </button>
            <button
              onClick={() => setViewMode("month")}
              className={`px-3 py-1.5 text-sm font-medium ${
                viewMode === "month"
                  ? "bg-indigo-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              月表示
            </button>
          </div>
        </div>
      </header>

      {/* ガントチャート */}
      <main className="flex-1 overflow-hidden p-6">
        {scheduledGroups.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <p className="text-gray-500 text-lg mb-2">
              スケジュールされた課題がありません
            </p>
            <p className="text-gray-400 text-sm mb-4">
              課題に開始日と期限を設定すると、ガントチャートに表示されます
            </p>
            <Link
              to={`/organizations/${orgId}/productions/${productionId}/board`}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
            >
              カンバンボードで課題を管理
            </Link>
          </div>
        ) : (
          <GanttChart
            groups={scheduledGroups}
            phases={phases}
            milestones={milestones}
            timelineStart={timelineStart}
            timelineEnd={timelineEnd}
            dayWidth={DAY_WIDTH[viewMode]}
            onIssueClick={handleIssueClick}
          />
        )}
      </main>

      {/* 未スケジュール課題 */}
      {unscheduledIssues.length > 0 && (
        <div className="border-t bg-white px-6 py-3">
          <button
            onClick={() => setShowUnscheduled(!showUnscheduled)}
            className="text-sm font-medium text-gray-600 hover:text-gray-800 flex items-center gap-1"
          >
            <span className={`transition-transform ${showUnscheduled ? "rotate-90" : ""}`}>
              ▶
            </span>
            未スケジュール課題 ({unscheduledIssues.length})
          </button>
          {showUnscheduled && (
            <div className="mt-2 max-h-48 overflow-y-auto">
              {unscheduledIssues.map((issue) => (
                <div
                  key={issue.id}
                  className="flex items-center gap-3 py-1.5 px-2 text-sm text-gray-600 hover:bg-gray-50 cursor-pointer rounded"
                  onClick={() => handleIssueClick(issue)}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      issue.priority === "high"
                        ? "bg-red-500"
                        : issue.priority === "medium"
                          ? "bg-yellow-500"
                          : "bg-blue-400"
                    }`}
                  />
                  <span className="truncate">{issue.title}</span>
                  <span className="text-xs text-gray-400 shrink-0">
                    {issue.start_date ? "" : "開始日なし"}
                    {!issue.start_date && !issue.due_date ? " / " : ""}
                    {issue.due_date ? "" : "期限なし"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 詳細パネル */}
      {selectedIssue && (
        <IssueDetailPanel
          issue={selectedIssue}
          statuses={statuses}
          onClose={() => setSelectedIssueId(null)}
          onStatusChange={(issueId, statusId) =>
            updateStatus.mutate({ issueId, statusId })
          }
        />
      )}
    </div>
  );
}
