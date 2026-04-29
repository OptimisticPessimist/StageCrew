import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  useScripts,
  useDeleteScript,
  useUploadScript,
} from "./hooks/useScripts";
import ScriptUploadModal from "./ScriptUploadModal";
import type { ScriptListItem } from "@/types";

export default function ScriptListPage() {
  const { orgId, productionId } = useParams<{
    orgId: string;
    productionId: string;
  }>();

  const {
    data: scripts,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useScripts(orgId!, productionId!);
  const deleteScript = useDeleteScript(orgId!, productionId!);
  const uploadScript = useUploadScript(orgId!, productionId!);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const dashboardPath = `/organizations/${orgId}/productions/${productionId}/dashboard`;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-3 p-6">
        <div className="text-sm font-medium text-red-700">
          脚本一覧を取得できませんでした
        </div>
        <div className="text-xs text-gray-500">
          {error instanceof Error ? error.message : "不明なエラー"}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            {isFetching ? "再試行中..." : "再試行"}
          </button>
          <Link
            to={dashboardPath}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ダッシュボードに戻る
          </Link>
        </div>
      </div>
    );
  }

  const scriptList = scripts ?? [];

  const handleDelete = async (script: ScriptListItem) => {
    if (deletingId) return;
    if (!window.confirm(`「${script.title}」を削除しますか？`)) return;
    setDeleteError(null);
    setDeletingId(script.id);
    try {
      await deleteScript.mutateAsync(script.id);
    } catch (err) {
      setDeleteError(
        `「${script.title}」の削除に失敗しました: ${
          err instanceof Error ? err.message : "不明なエラー"
        }`,
      );
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to={dashboardPath}
            className="text-gray-400 hover:text-gray-600 text-sm"
          >
            &larr; ダッシュボード
          </Link>
          <h1 className="text-lg font-bold text-gray-900">脚本</h1>
        </div>
        <button
          onClick={() => setUploadOpen(true)}
          className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700"
        >
          + アップロード
        </button>
      </header>

      <main className="max-w-4xl mx-auto p-6 space-y-3">
        {deleteError && (
          <div
            role="alert"
            className="bg-red-50 border border-red-200 text-red-700 text-sm rounded px-3 py-2 flex items-start justify-between gap-3"
          >
            <span>{deleteError}</span>
            <button
              type="button"
              onClick={() => setDeleteError(null)}
              className="text-red-500 hover:text-red-700 shrink-0"
              aria-label="エラーメッセージを閉じる"
            >
              ×
            </button>
          </div>
        )}
        {scriptList.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <p className="mb-2">まだ脚本がありません</p>
            <button
              onClick={() => setUploadOpen(true)}
              className="text-indigo-600 hover:text-indigo-700 text-sm font-medium"
            >
              最初の脚本をアップロード
            </button>
          </div>
        ) : (
          scriptList.map((script) => (
            <ScriptCard
              key={script.id}
              script={script}
              orgId={orgId!}
              productionId={productionId!}
              onDelete={() => handleDelete(script)}
              isDeleting={deletingId === script.id}
              deleteDisabled={deletingId !== null && deletingId !== script.id}
            />
          ))
        )}
      </main>

      {uploadOpen && (
        <ScriptUploadModal
          title="脚本をアップロード"
          submitLabel="アップロード"
          onClose={() => setUploadOpen(false)}
          onSubmit={({ file }) => uploadScript.mutateAsync(file)}
        />
      )}
    </div>
  );
}

function ScriptCard({
  script,
  orgId,
  productionId,
  onDelete,
  isDeleting,
  deleteDisabled,
}: {
  script: ScriptListItem;
  orgId: string;
  productionId: string;
  onDelete: () => void;
  isDeleting: boolean;
  deleteDisabled: boolean;
}) {
  const detailPath = `/organizations/${orgId}/productions/${productionId}/scripts/${script.id}`;
  const uploadedAt = new Date(script.uploaded_at).toLocaleString();

  return (
    <div className="bg-white rounded-lg border p-4 flex items-start gap-4">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Link
            to={detailPath}
            className="font-medium text-gray-900 hover:text-indigo-700"
          >
            {script.title}
          </Link>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
            Rev {script.revision}
          </span>
          {script.is_public && (
            <span className="text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
              公開
            </span>
          )}
        </div>
        {script.author && (
          <div className="mt-1 text-sm text-gray-600">作: {script.author}</div>
        )}
        {script.synopsis && (
          <p className="mt-1 text-sm text-gray-500 line-clamp-2">
            {script.synopsis}
          </p>
        )}
        <div className="mt-2 text-xs text-gray-400">
          最終アップロード: {uploadedAt}
        </div>
      </div>
      <button
        onClick={onDelete}
        disabled={isDeleting || deleteDisabled}
        aria-busy={isDeleting}
        className="text-sm text-red-400 hover:text-red-600 shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isDeleting ? "削除中..." : "削除"}
      </button>
    </div>
  );
}
