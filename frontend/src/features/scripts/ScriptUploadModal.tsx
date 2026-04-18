import { useState } from "react";

const ACCEPT = ".txt,.fountain,text/plain";
const MAX_BYTES = 10 * 1024 * 1024;

interface Props {
  title: string;
  submitLabel: string;
  requireFile?: boolean;
  showRevisionText?: boolean;
  onClose: () => void;
  onSubmit: (input: {
    file: File;
    revisionText?: string;
  }) => Promise<unknown>;
}

export default function ScriptUploadModal({
  title,
  submitLabel,
  showRevisionText = false,
  onClose,
  onSubmit,
}: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [revisionText, setRevisionText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    if (selected && selected.size > MAX_BYTES) {
      setError("ファイルサイズが10MBを超えています");
      setFile(null);
      return;
    }
    setError(null);
    setFile(selected);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("ファイルを選択してください");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        file,
        revisionText: revisionText.trim() || undefined,
      });
      onClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "アップロードに失敗しました",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-lg shadow-xl w-full max-w-md p-5 space-y-4"
      >
        <h2 className="text-base font-bold text-gray-900">{title}</h2>

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">
            ファイル（.txt / .fountain）
          </label>
          <input
            type="file"
            accept={ACCEPT}
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:border-0 file:rounded file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
          />
          {file && (
            <p className="text-xs text-gray-500">
              {file.name}（{Math.round(file.size / 1024)} KB）
            </p>
          )}
        </div>

        {showRevisionText && (
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">
              改訂メモ（任意）
            </label>
            <textarea
              value={revisionText}
              onChange={(e) => setRevisionText(e.target.value)}
              rows={3}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              placeholder="このリビジョンの変更点など"
            />
          </div>
        )}

        {error && (
          <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50"
          >
            キャンセル
          </button>
          <button
            type="submit"
            disabled={!file || submitting}
            className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-40"
          >
            {submitting ? "送信中..." : submitLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
