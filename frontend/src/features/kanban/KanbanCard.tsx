import { Draggable } from "@hello-pangea/dnd";
import type { Issue } from "@/types";

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-blue-100 text-blue-700",
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const TYPE_LABELS: Record<string, string> = {
  task: "タスク",
  bug: "バグ",
  request: "要望",
  notice: "連絡",
};

interface Props {
  issue: Issue;
  index: number;
  isClosed: boolean;
  onClick: (issue: Issue) => void;
}

export default function KanbanCard({ issue, index, isClosed, onClick }: Props) {
  const priorityClass = PRIORITY_COLORS[issue.priority] ?? "bg-gray-100 text-gray-700";
  const isOverdue =
    !isClosed && issue.due_date && new Date(issue.due_date) < new Date();

  return (
    <Draggable draggableId={issue.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={() => onClick(issue)}
          className={`rounded-lg border p-3 mb-2 cursor-pointer transition-shadow ${
            snapshot.isDragging ? "shadow-lg ring-2 ring-indigo-300" : "shadow-sm hover:shadow-md"
          } ${isClosed ? "bg-gray-50 opacity-70" : "bg-white"}`}
        >
          <div className="flex items-start gap-2 mb-1">
            <span className="text-xs text-gray-400">
              {TYPE_LABELS[issue.issue_type] ?? issue.issue_type}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${priorityClass}`}>
              {PRIORITY_LABELS[issue.priority] ?? issue.priority}
            </span>
          </div>

          <h4
            className={`text-sm font-medium leading-snug mb-2 ${
              isClosed
                ? "text-gray-400 line-through"
                : "text-gray-900"
            }`}
          >
            {isClosed && <span className="mr-1">✓</span>}
            {issue.title}
          </h4>

          {issue.labels.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {issue.labels.map((label) => (
                <span
                  key={label.label_id}
                  className="text-xs px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: label.color ? `${label.color}20` : "#e5e7eb",
                    color: label.color ?? "#6b7280",
                  }}
                >
                  {label.name}
                </span>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between">
            {issue.due_date ? (
              <span
                className={`text-xs ${isOverdue ? "text-red-600 font-medium" : "text-gray-400"}`}
              >
                {new Date(issue.due_date).toLocaleDateString("ja-JP", {
                  month: "short",
                  day: "numeric",
                })}
              </span>
            ) : (
              <span />
            )}

            {issue.assignees.length > 0 && (
              <div className="flex -space-x-1">
                {issue.assignees.slice(0, 3).map((a) => (
                  <div
                    key={a.user_id}
                    className="w-6 h-6 rounded-full bg-indigo-500 text-white text-xs flex items-center justify-center ring-2 ring-white"
                    title={a.display_name}
                  >
                    {a.display_name.charAt(0)}
                  </div>
                ))}
                {issue.assignees.length > 3 && (
                  <div className="w-6 h-6 rounded-full bg-gray-300 text-gray-600 text-xs flex items-center justify-center ring-2 ring-white">
                    +{issue.assignees.length - 3}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </Draggable>
  );
}
