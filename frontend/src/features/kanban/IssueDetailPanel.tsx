import type { IssueDetail, StatusDefinition } from "@/types";

const PRIORITY_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-blue-100 text-blue-700",
};

const TYPE_LABELS: Record<string, string> = {
  task: "タスク",
  bug: "バグ",
  request: "要望",
  notice: "連絡",
};

interface Props {
  issue: IssueDetail;
  statuses: StatusDefinition[];
  onClose: () => void;
  onStatusChange: (issueId: string, statusId: string | null) => void;
}

export default function IssueDetailPanel({
  issue,
  statuses,
  onClose,
  onStatusChange,
}: Props) {
  const priorityClass = PRIORITY_COLORS[issue.priority] ?? "bg-gray-100 text-gray-700";

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div
        className="absolute inset-0"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg bg-white shadow-xl overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 truncate pr-4">
            {issue.title}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl shrink-0"
          >
            &times;
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* メタ情報 */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">種類</span>
              <p className="font-medium">{TYPE_LABELS[issue.issue_type] ?? issue.issue_type}</p>
            </div>
            <div>
              <span className="text-gray-500">優先度</span>
              <p>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${priorityClass}`}>
                  {PRIORITY_LABELS[issue.priority] ?? issue.priority}
                </span>
              </p>
            </div>
            <div>
              <span className="text-gray-500">ステータス</span>
              <div className="mt-1">
                <select
                  value={issue.status_id ?? ""}
                  onChange={(e) =>
                    onStatusChange(issue.id, e.target.value || null)
                  }
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                >
                  <option value="">未分類</option>
                  {statuses.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <span className="text-gray-500">期限</span>
              <p className="font-medium">
                {issue.due_date
                  ? new Date(issue.due_date).toLocaleDateString("ja-JP")
                  : "未設定"}
              </p>
            </div>
          </div>

          {/* 説明 */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">説明</h3>
            {issue.description ? (
              <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                {issue.description}
              </p>
            ) : (
              <p className="text-sm text-gray-400 italic">説明なし</p>
            )}
          </div>

          {/* 担当者 */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">担当者</h3>
            {issue.assignees.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {issue.assignees.map((a) => (
                  <div
                    key={a.user_id}
                    className="flex items-center gap-1.5 bg-gray-100 rounded-full px-3 py-1"
                  >
                    <div className="w-5 h-5 rounded-full bg-indigo-500 text-white text-xs flex items-center justify-center">
                      {a.display_name.charAt(0)}
                    </div>
                    <span className="text-sm text-gray-700">{a.display_name}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic">未割当</p>
            )}
          </div>

          {/* ラベル */}
          {issue.labels.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">ラベル</h3>
              <div className="flex flex-wrap gap-1.5">
                {issue.labels.map((label) => (
                  <span
                    key={label.label_id}
                    className="text-xs px-2 py-1 rounded-full font-medium"
                    style={{
                      backgroundColor: label.color ? `${label.color}20` : "#e5e7eb",
                      color: label.color ?? "#6b7280",
                    }}
                  >
                    {label.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* タイムスタンプ */}
          <div className="text-xs text-gray-400 border-t pt-4 space-y-1">
            <p>
              作成日: {new Date(issue.created_at).toLocaleString("ja-JP")}
            </p>
            <p>
              更新日: {new Date(issue.updated_at).toLocaleString("ja-JP")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
