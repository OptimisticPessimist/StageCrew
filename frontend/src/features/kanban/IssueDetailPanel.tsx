import { useState } from "react";
import type { IssueDetail, IssueUpdate, StatusDefinition } from "@/types";

const TYPE_LABELS: Record<string, string> = {
  task: "タスク",
  bug: "バグ",
  request: "要望",
  notice: "連絡",
};

export interface MemberOption {
  user_id: string;
  display_name: string;
}

interface Props {
  issue: IssueDetail;
  statuses: StatusDefinition[];
  members: MemberOption[];
  onClose: () => void;
  onStatusChange: (issueId: string, statusId: string | null) => void;
  onUpdate: (issueId: string, body: IssueUpdate) => void;
}

// ---- helpers ----
function toDateInputValue(utcStr: string | null): string {
  if (!utcStr) return "";
  return utcStr.slice(0, 10);
}

function toUtcDatetime(dateStr: string): string | null {
  if (!dateStr) return null;
  return `${dateStr}T00:00:00`;
}

// ---- Assignee Picker ----
function AssigneePicker({
  members,
  selectedIds,
  onChange,
}: {
  members: MemberOption[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}) {
  const [open, setOpen] = useState(false);

  const toggle = (userId: string) => {
    if (selectedIds.includes(userId)) {
      onChange(selectedIds.filter((id) => id !== userId));
    } else {
      onChange([...selectedIds, userId]);
    }
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm text-left focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none bg-white hover:bg-gray-50"
      >
        {selectedIds.length > 0 ? (
          <span className="text-gray-900">
            {selectedIds
              .map(
                (id) => members.find((m) => m.user_id === id)?.display_name,
              )
              .filter(Boolean)
              .join("、")}
          </span>
        ) : (
          <span className="text-gray-400">担当者を選択</span>
        )}
      </button>
      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
          />
          <div className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
            {members.length === 0 ? (
              <p className="px-3 py-2 text-sm text-gray-400">
                メンバーがいません
              </p>
            ) : (
              members.map((m) => (
                <label
                  key={m.user_id}
                  className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(m.user_id)}
                    onChange={() => toggle(m.user_id)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div className="w-5 h-5 rounded-full bg-indigo-500 text-white text-xs flex items-center justify-center shrink-0">
                    {m.display_name.charAt(0)}
                  </div>
                  <span className="text-sm text-gray-700">
                    {m.display_name}
                  </span>
                </label>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function IssueDetailPanel({
  issue,
  statuses,
  members,
  onClose,
  onStatusChange,
  onUpdate,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div className="absolute inset-0" onClick={onClose} />
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
              <div className="mt-1">
                <select
                  value={issue.issue_type}
                  onChange={(e) =>
                    onUpdate(issue.id, { issue_type: e.target.value })
                  }
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                >
                  {Object.entries(TYPE_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <span className="text-gray-500">優先度</span>
              <div className="mt-1">
                <select
                  value={issue.priority}
                  onChange={(e) =>
                    onUpdate(issue.id, { priority: e.target.value })
                  }
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                >
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
                </select>
              </div>
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
              <span className="text-gray-500">開始日</span>
              <div className="mt-1">
                <input
                  type="date"
                  value={toDateInputValue(issue.start_date)}
                  onChange={(e) =>
                    onUpdate(issue.id, {
                      start_date: toUtcDatetime(e.target.value),
                    })
                  }
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                />
              </div>
            </div>
            <div className="col-span-2">
              <span className="text-gray-500">期限</span>
              <div className="mt-1">
                <input
                  type="date"
                  value={toDateInputValue(issue.due_date)}
                  onChange={(e) =>
                    onUpdate(issue.id, {
                      due_date: toUtcDatetime(e.target.value),
                    })
                  }
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                />
              </div>
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
            <AssigneePicker
              members={members}
              selectedIds={issue.assignees.map((a) => a.user_id)}
              onChange={(ids) => onUpdate(issue.id, { assignee_ids: ids })}
            />
          </div>

          {/* ラベル */}
          {issue.labels.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                ラベル
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {issue.labels.map((label) => (
                  <span
                    key={label.label_id}
                    className="text-xs px-2 py-1 rounded-full font-medium"
                    style={{
                      backgroundColor: label.color
                        ? `${label.color}20`
                        : "#e5e7eb",
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
            <p>作成日: {new Date(issue.created_at).toLocaleString("ja-JP")}</p>
            <p>更新日: {new Date(issue.updated_at).toLocaleString("ja-JP")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
