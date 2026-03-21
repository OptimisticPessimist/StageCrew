import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import type { Issue, IssueCreate } from "@/types";
import { useStatuses, useCreateStatus } from "./hooks/useStatuses";
import {
  useIssues,
  useIssueDetail,
  useCreateIssue,
  useUpdateIssueStatus,
} from "./hooks/useIssues";
import KanbanBoard from "./KanbanBoard";
import IssueCreateModal from "./IssueCreateModal";
import IssueDetailPanel from "./IssueDetailPanel";

export default function KanbanPage() {
  const { orgId, productionId } = useParams<{
    orgId: string;
    productionId: string;
  }>();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createDefaultStatusId, setCreateDefaultStatusId] = useState<
    string | null
  >(null);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [showStatusForm, setShowStatusForm] = useState(false);
  const [newStatusName, setNewStatusName] = useState("");
  const [newStatusColor, setNewStatusColor] = useState("#6366f1");

  const {
    data: statuses = [],
    isLoading: loadingStatuses,
  } = useStatuses(orgId!, productionId!);

  const {
    data: issues = [],
    isLoading: loadingIssues,
  } = useIssues(orgId!, productionId!);

  const { data: selectedIssue } = useIssueDetail(
    orgId!,
    productionId!,
    selectedIssueId,
  );

  const createIssue = useCreateIssue(orgId!, productionId!);
  const updateStatus = useUpdateIssueStatus(orgId!, productionId!);
  const createStatus = useCreateStatus(orgId!, productionId!);

  const handleMoveIssue = (issueId: string, newStatusId: string | null) => {
    updateStatus.mutate({ issueId, statusId: newStatusId });
  };

  const handleCardClick = (issue: Issue) => {
    setSelectedIssueId(issue.id);
  };

  const handleAddClick = (statusId: string | null) => {
    setCreateDefaultStatusId(statusId);
    setShowCreateModal(true);
  };

  const handleCreateIssue = (data: IssueCreate) => {
    createIssue.mutate(data, {
      onSuccess: () => setShowCreateModal(false),
    });
  };

  const handleCreateStatus = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStatusName.trim()) return;
    createStatus.mutate(
      {
        name: newStatusName.trim(),
        color: newStatusColor,
        sort_order: statuses.length,
      },
      {
        onSuccess: () => {
          setNewStatusName("");
          setShowStatusForm(false);
        },
      },
    );
  };

  if (loadingStatuses || loadingIssues) {
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
          <h1 className="text-lg font-bold text-gray-900">カンバンボード</h1>
        </div>
        <div className="flex items-center gap-2">
          {showStatusForm ? (
            <form onSubmit={handleCreateStatus} className="flex items-center gap-2">
              <input
                type="color"
                value={newStatusColor}
                onChange={(e) => setNewStatusColor(e.target.value)}
                className="w-8 h-8 rounded cursor-pointer"
              />
              <input
                type="text"
                value={newStatusName}
                onChange={(e) => setNewStatusName(e.target.value)}
                placeholder="ステータス名"
                className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                autoFocus
              />
              <button
                type="submit"
                disabled={!newStatusName.trim()}
                className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-40"
              >
                追加
              </button>
              <button
                type="button"
                onClick={() => setShowStatusForm(false)}
                className="px-2 py-1.5 text-sm text-gray-500 hover:text-gray-700"
              >
                &times;
              </button>
            </form>
          ) : (
            <button
              onClick={() => setShowStatusForm(true)}
              className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
            >
              + ステータス追加
            </button>
          )}
          <button
            onClick={() => handleAddClick(null)}
            className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700"
          >
            + 課題を作成
          </button>
        </div>
      </header>

      {/* ボード */}
      <main className="flex-1 overflow-hidden p-6">
        {statuses.length === 0 && issues.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <p className="text-gray-500 text-lg mb-2">
              まだステータスがありません
            </p>
            <p className="text-gray-400 text-sm mb-4">
              「ステータス追加」ボタンからカンバンのカラムを作成してください
            </p>
            <button
              onClick={() => setShowStatusForm(true)}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
            >
              最初のステータスを作成
            </button>
          </div>
        ) : (
          <KanbanBoard
            statuses={statuses}
            issues={issues}
            onMoveIssue={handleMoveIssue}
            onCardClick={handleCardClick}
            onAddClick={handleAddClick}
          />
        )}
      </main>

      {/* モーダル */}
      {showCreateModal && (
        <IssueCreateModal
          statuses={statuses}
          defaultStatusId={createDefaultStatusId}
          onSubmit={handleCreateIssue}
          onClose={() => setShowCreateModal(false)}
        />
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
