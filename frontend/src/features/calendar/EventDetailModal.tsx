import { useMemo, useState } from "react";
import type { EventAttendee, ProductionMember, RsvpStatus } from "@/types";
import {
  EVENT_TYPE_COLORS,
  EVENT_TYPE_LABELS,
  RSVP_LABELS,
  formatDateTime,
  isSafeHttpUrl,
} from "./calendarUtils";
import {
  useAddAttendees,
  useDeleteEvent,
  useEvent,
  useRemoveAttendee,
  useUpdateAttendee,
} from "./hooks/useEvents";

interface Props {
  orgId: string;
  productionId: string;
  eventId: string;
  currentUserId: string | null;
  canManage: boolean;
  members: ProductionMember[];
  onClose: () => void;
  onEdit: () => void;
}

const RSVP_OPTIONS: { value: RsvpStatus; label: string }[] = [
  { value: "accepted", label: "参加" },
  { value: "tentative", label: "未定" },
  { value: "declined", label: "不参加" },
];

export default function EventDetailModal({
  orgId,
  productionId,
  eventId,
  currentUserId,
  canManage,
  members,
  onClose,
  onEdit,
}: Props) {
  const { data: event, isLoading } = useEvent(orgId, productionId, eventId);
  const addAttendees = useAddAttendees(orgId, productionId);
  const updateAttendee = useUpdateAttendee(orgId, productionId);
  const removeAttendee = useRemoveAttendee(orgId, productionId);
  const deleteEvent = useDeleteEvent(orgId, productionId);
  const [pickerOpen, setPickerOpen] = useState(false);

  const myAttendee = useMemo(
    () =>
      event?.attendees.find((a) => a.user_id === currentUserId) ?? null,
    [event, currentUserId],
  );

  const missingMembers = useMemo(() => {
    if (!event) return [];
    const existingIds = new Set(event.attendees.map((a) => a.user_id));
    return members.filter((m) => !existingIds.has(m.user_id));
  }, [event, members]);

  const handleDelete = () => {
    if (!window.confirm("このイベントを削除します。よろしいですか？")) return;
    deleteEvent.mutate(eventId, { onSuccess: () => onClose() });
  };

  const handleRsvp = (status: RsvpStatus) => {
    if (!myAttendee) return;
    updateAttendee.mutate({
      eventId,
      userId: myAttendee.user_id,
      body: { rsvp_status: status },
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        {isLoading || !event ? (
          <div className="p-10 text-center text-gray-500">読み込み中...</div>
        ) : (
          <>
            <div className="px-6 pt-5 pb-4 border-b">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <span
                    className={`inline-block text-xs px-2 py-0.5 rounded border ${
                      EVENT_TYPE_COLORS[event.event_type] ??
                      EVENT_TYPE_COLORS.other
                    }`}
                  >
                    {EVENT_TYPE_LABELS[event.event_type] ?? event.event_type}
                  </span>
                  <h2 className="text-xl font-bold text-gray-900 mt-2 break-words">
                    {event.title}
                  </h2>
                  <div className="text-sm text-gray-600 mt-1">
                    {event.is_all_day ? (
                      <span>終日</span>
                    ) : (
                      <>
                        <span>{formatDateTime(event.start_at)}</span>
                        {event.end_at && (
                          <span> 〜 {formatDateTime(event.end_at)}</span>
                        )}
                      </>
                    )}
                  </div>
                </div>
                {canManage && (
                  <div className="flex gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={onEdit}
                      className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      編集
                    </button>
                    <button
                      type="button"
                      onClick={handleDelete}
                      className="px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
                    >
                      削除
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="px-6 py-4 space-y-4">
              {(event.location_name || event.location_url) && (
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-1">
                    場所
                  </h3>
                  <div className="text-sm text-gray-900">
                    {event.location_name}
                    {event.location_url && isSafeHttpUrl(event.location_url) && (
                      <>
                        {" "}
                        <a
                          href={event.location_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 hover:underline"
                        >
                          リンク
                        </a>
                      </>
                    )}
                  </div>
                </section>
              )}

              {event.description && (
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-1">
                    説明
                  </h3>
                  <p className="text-sm text-gray-900 whitespace-pre-wrap">
                    {event.description}
                  </p>
                </section>
              )}

              {event.scenes.length > 0 && (
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-1">
                    対象シーン
                  </h3>
                  <ul className="text-sm text-gray-900 space-y-0.5">
                    {event.scenes.map((s) => (
                      <li key={s.scene_id}>
                        第{s.act_number}幕 第{s.scene_number}場: {s.heading}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* 自分のRSVP */}
              {myAttendee && (
                <section className="border-t pt-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">
                    自分の出欠
                  </h3>
                  <div className="flex gap-2">
                    {RSVP_OPTIONS.map((opt) => {
                      const active = myAttendee.rsvp_status === opt.value;
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => handleRsvp(opt.value)}
                          disabled={updateAttendee.isPending}
                          className={`px-3 py-1.5 text-sm rounded-lg border ${
                            active
                              ? "bg-indigo-600 text-white border-indigo-600"
                              : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                          }`}
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* 参加者一覧 */}
              <section className="border-t pt-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-700">
                    招集メンバー ({event.attendees.length})
                  </h3>
                  {canManage && missingMembers.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setPickerOpen((v) => !v)}
                      className="text-sm text-indigo-600 hover:underline"
                    >
                      {pickerOpen ? "閉じる" : "+ メンバー追加"}
                    </button>
                  )}
                </div>

                {pickerOpen && canManage && (
                  <MemberPicker
                    members={missingMembers}
                    isPending={addAttendees.isPending}
                    onAdd={(userIds) =>
                      addAttendees.mutate(
                        { eventId, body: { user_ids: userIds } },
                        { onSuccess: () => setPickerOpen(false) },
                      )
                    }
                  />
                )}

                {event.attendees.length === 0 ? (
                  <div className="text-sm text-gray-500">
                    まだ招集されたメンバーはいません
                  </div>
                ) : (
                  <ul className="divide-y">
                    {event.attendees.map((a) => (
                      <AttendeeRow
                        key={a.id}
                        attendee={a}
                        canManage={canManage}
                        onRemove={() =>
                          removeAttendee.mutate({
                            eventId,
                            userId: a.user_id,
                          })
                        }
                      />
                    ))}
                  </ul>
                )}
              </section>
            </div>

            <div className="flex justify-end px-6 py-4 border-t bg-gray-50 rounded-b-xl">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                閉じる
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function AttendeeRow({
  attendee,
  canManage,
  onRemove,
}: {
  attendee: EventAttendee;
  canManage: boolean;
  onRemove: () => void;
}) {
  const rsvpColor: Record<string, string> = {
    accepted: "text-emerald-700 bg-emerald-50",
    declined: "text-red-700 bg-red-50",
    tentative: "text-yellow-700 bg-yellow-50",
    pending: "text-gray-600 bg-gray-100",
  };
  return (
    <li className="py-2 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm text-gray-900 truncate">
          {attendee.display_name}
        </span>
        <span
          className={`text-[11px] px-1.5 py-0.5 rounded ${
            rsvpColor[attendee.rsvp_status] ?? rsvpColor.pending
          }`}
        >
          {RSVP_LABELS[attendee.rsvp_status] ?? attendee.rsvp_status}
        </span>
        {attendee.attendance_type === "optional" && (
          <span className="text-[10px] text-gray-500">（任意）</span>
        )}
      </div>
      {canManage && (
        <button
          type="button"
          onClick={onRemove}
          className="text-xs text-red-600 hover:underline"
        >
          外す
        </button>
      )}
    </li>
  );
}

function MemberPicker({
  members,
  isPending,
  onAdd,
}: {
  members: ProductionMember[];
  isPending: boolean;
  onAdd: (userIds: string[]) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const toggle = (id: string) =>
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  return (
    <div className="mb-3 p-3 bg-gray-50 rounded border">
      <div className="grid grid-cols-2 gap-1 mb-2 max-h-48 overflow-y-auto">
        {members.map((m) => (
          <label
            key={m.user_id}
            className="flex items-center gap-2 text-sm py-1 px-2 rounded hover:bg-white"
          >
            <input
              type="checkbox"
              checked={selected.includes(m.user_id)}
              onChange={() => toggle(m.user_id)}
            />
            <span>{m.display_name}</span>
          </label>
        ))}
      </div>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          disabled={selected.length === 0 || isPending}
          onClick={() => onAdd(selected)}
          className="px-3 py-1.5 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-40"
        >
          {selected.length}人を追加
        </button>
      </div>
    </div>
  );
}
