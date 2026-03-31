import { useRef, useState, type ChangeEvent } from "react";
import { useParams, Link } from "react-router-dom";
import { useScripts, useUploadScript, useDeleteScript } from "./hooks/useScripts";
import CountdownBadge from "@/features/production/CountdownBadge";
import type { ScriptListItem } from "@/types";

export default function ScriptsPage() {
  const { orgId, productionId } = useParams<{
    orgId: string;
    productionId: string;
  }>();

  const { data: scripts = [], isLoading } = useScripts(orgId!, productionId!);
  const uploadScript = useUploadScript(orgId!, productionId!);
  const deleteScript = useDeleteScript(orgId!, productionId!);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const dashboardPath = `/organizations/${orgId}/productions/${productionId}/dashboard`;

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    uploadScript.mutate(file, {
      onError: (err) => {
        setUploadError(err instanceof Error ? err.message : "アップロードに失敗しました");
      },
      onSettled: () => {
        if (fileInputRef.current) fileInputRef.current.value = "";
      },
    });
  };

  const handleDelete = async (script: ScriptListItem) => {
    if (!confirm(`「${script.title}」を削除しますか？`)) return;
    setDeletingId(script.id);
    deleteScript.mutate(script.id, {
      onSettled: () => setDeletingId(null),
    });
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to={dashboardPath} className="text-gray-400 hover:text-gray-600 text-sm">
            &larr; ダッシュボード
          </Link>
          <h1 className="text-lg font-bold text-gray-900">脚本管理</h1>
          <CountdownBadge orgId={orgId!} productionId={productionId!} />
        </div>
        <div className="flex items-center gap-2">
          {uploadScript.isPending && (
            <span className="text-sm text-gray-500">アップロード中...</span>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.fountain"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadScript.isPending}
            className="bg-indigo-600 text-white px-4 py-2 rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            脚本をアップロード
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        {uploadError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {uploadError}
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-12 text-gray-500">
            読み込み中...
          </div>
        ) : scripts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <p className="text-lg mb-2">脚本がありません</p>
            <p className="text-sm">
              .fountain または .txt ファイルをアップロードしてください
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {scripts.map((script) => (
              <ScriptCard
                key={script.id}
                script={script}
                orgId={orgId!}
                productionId={productionId!}
                onDelete={() => handleDelete(script)}
                isDeleting={deletingId === script.id}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function ScriptCard({
  script,
  orgId,
  productionId,
  onDelete,
  isDeleting,
}: {
  script: ScriptListItem;
  orgId: string;
  productionId: string;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const detailPath = `/organizations/${orgId}/productions/${productionId}/scripts/${script.id}`;
  const pdfUrl = `/api/organizations/${orgId}/productions/${productionId}/scripts/${script.id}/pdf`;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <Link
            to={detailPath}
            className="font-semibold text-gray-900 hover:text-indigo-600 block truncate"
          >
            {script.title}
          </Link>
          {script.author && (
            <p className="text-sm text-gray-500 mt-0.5">作: {script.author}</p>
          )}
        </div>
        <span className="shrink-0 text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
          第{script.revision}稿
        </span>
      </div>

      {script.synopsis && (
        <p className="text-sm text-gray-600 line-clamp-2">{script.synopsis}</p>
      )}

      <div className="flex items-center justify-between pt-1 border-t border-gray-100">
        <div className="flex items-center gap-2">
          <Link
            to={detailPath}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            詳細
          </Link>
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-gray-600 hover:text-gray-800"
          >
            PDF
          </a>
        </div>
        <button
          onClick={onDelete}
          disabled={isDeleting}
          className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
        >
          削除
        </button>
      </div>
    </div>
  );
}
