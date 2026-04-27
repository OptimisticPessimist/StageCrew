import { useEffect, useState } from "react";
import type { EventCreate, EventDetail, EventType, EventUpdate } from "@/types";
import { fromLocalInputValue, toLocalInputValue } from "./calendarUtils";

interface Props {
  existing?: EventDetail | null;
  initialStart?: Date | null;
  onSubmit: (data: EventCreate | EventUpdate) => void;
  onClose: () => void;
  isSubmitting?: boolean;
}

const EVENT_TYPES: { value: EventType; label: string }[] = [
  { value: "rehearsal", label: "稽古" },
  { value: "performance", label: "本番" },
  { value: "meeting", label: "打ち合わせ" },
  { value: "other", label: "その他" },
];

export default function EventFormModal({
  existing,
  initialStart,
  onSubmit,
  onClose,
  isSubmitting,
}: Props) {
  const [title, setTitle] = useState(existing?.title ?? "");
  const [eventType, setEventType] = useState<EventType>(
    (existing?.event_type as EventType) ?? "rehearsal",
  );
  const [description, setDescription] = useState(existing?.description ?? "");
  const [startLocal, setStartLocal] = useState(
    existing
      ? toLocalInputValue(existing.start_at)
      : initialStart
        ? toLocalInputValue(initialStart.toISOString())
        : "",
  );
  const [endLocal, setEndLocal] = useState(
    existing?.end_at ? toLocalInputValue(existing.end_at) : "",
  );
  const [isAllDay, setIsAllDay] = useState(existing?.is_all_day ?? false);
  const [locationName, setLocationName] = useState(
    existing?.location_name ?? "",
  );
  const [locationUrl, setLocationUrl] = useState(existing?.location_url ?? "");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!startLocal && initialStart) {
      setStartLocal(toLocalInputValue(initialStart.toISOString()));
    }
  }, [initialStart, startLocal]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("タイトルを入力してください");
      return;
    }
    if (!startLocal) {
      setError("開始日時を指定してください");
      return;
    }
    if (endLocal && endLocal < startLocal) {
      setError("終了日時は開始日時以降である必要があります");
      return;
    }

    const payload: EventCreate | EventUpdate = {
      title: title.trim(),
      event_type: eventType,
      description: description.trim() || null,
      start_at: fromLocalInputValue(startLocal),
      end_at: endLocal ? fromLocalInputValue(endLocal) : null,
      is_all_day: isAllDay,
      location_name: locationName.trim() || null,
      location_url: locationUrl.trim() || null,
    };
    onSubmit(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          <div className="px-6 pt-5 pb-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              {existing ? "イベントを編集" : "イベントを作成"}
            </h2>
            {error && (
              <div className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  タイトル <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                  autoFocus
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    種別
                  </label>
                  <select
                    value={eventType}
                    onChange={(e) =>
                      setEventType(e.target.value as EventType)
                    }
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  >
                    {EVENT_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={isAllDay}
                      onChange={(e) => setIsAllDay(e.target.checked)}
                    />
                    終日
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    開始 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={startLocal}
                    onChange={(e) => setStartLocal(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    終了
                  </label>
                  <input
                    type="datetime-local"
                    value={endLocal}
                    onChange={(e) => setEndLocal(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  場所
                </label>
                <input
                  type="text"
                  value={locationName}
                  onChange={(e) => setLocationName(e.target.value)}
                  placeholder="スタジオA など"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  場所URL
                </label>
                <input
                  type="url"
                  value={locationUrl}
                  onChange={(e) => setLocationUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  説明
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 px-6 py-4 border-t bg-gray-50 rounded-b-xl">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !title.trim() || !startLocal}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {existing ? "更新" : "作成"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
