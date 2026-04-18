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

  const { data: scripts = [], isLoading } = useScripts(orgId!, productionId!);
  const deleteScript = useDeleteScript(orgId!, productionId!);
  const uploadScript = useUploadScript(orgId!, productionId!);
  const [uploadOpen, setUploadOpen] = useState(false);

  const dashboardPath = `/organizations/${orgId}/productions/${productionId}/dashboard`;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  const handleDelete = (script: ScriptListItem) => {
    if (!window.confirm(`「${script.title}」を削除しますか？`)) return;
    deleteScript.mutate(script.id);
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
        {scripts.length === 0 ? (
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
          scripts.map((script) => (
            <ScriptCard
              key={script.id}
              script={script}
              orgId={orgId!}
              productionId={productionId!}
              onDelete={() => handleDelete(script)}
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
}: {
  script: ScriptListItem;
  orgId: string;
  productionId: string;
  onDelete: () => void;
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
        className="text-sm text-red-400 hover:text-red-600 shrink-0"
      >
        削除
      </button>
    </div>
  );
}
