import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { EventCreate, EventUpdate } from "@/types";
import { useAuth } from "@/features/auth/AuthProvider";
import { useProductionMembers } from "@/features/members/hooks/useProductionMembers";
import CountdownBadge from "@/features/production/CountdownBadge";
import {
  addDays,
  monthGridRange,
  monthLabel,
  startOfDay,
} from "./calendarUtils";
import {
  useCreateEvent,
  useEvents,
  useUpdateEvent,
} from "./hooks/useEvents";
import MonthView from "./MonthView";
import WeekView from "./WeekView";
import EventDetailModal from "./EventDetailModal";
import EventFormModal from "./EventFormModal";

type ViewMode = "month" | "week";

export default function CalendarPage() {
  const { orgId, productionId } = useParams<{
    orgId: string;
    productionId: string;
  }>();
  const { user } = useAuth();

  const [viewMode, setViewMode] = useState<ViewMode>("month");
  const [cursor, setCursor] = useState<Date>(() => startOfDay(new Date()));
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [editingEventId, setEditingEventId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createInitialStart, setCreateInitialStart] = useState<Date | null>(
    null,
  );

  const { data: members = [] } = useProductionMembers(orgId!, productionId!);
  const currentMember = useMemo(
    () => members.find((m) => m.user_id === user?.id) ?? null,
    [members, user],
  );
  const canManage = currentMember?.production_role === "manager";

  // 表示範囲（UTC）
  const range = useMemo(() => {
    if (viewMode === "month") {
      return monthGridRange(cursor.getFullYear(), cursor.getMonth());
    }
    const weekStart = startOfDay(
      addDays(cursor, -cursor.getDay()), // 日曜始まり
    );
    const weekEnd = addDays(weekStart, 7);
    return {
      startFrom: weekStart.toISOString(),
      startTo: weekEnd.toISOString(),
    };
  }, [viewMode, cursor]);

  const { data: events = [], isLoading } = useEvents(orgId!, productionId!, range);

  const createEvent = useCreateEvent(orgId!, productionId!);
  const updateEvent = useUpdateEvent(orgId!, productionId!);

  const handlePrev = () => {
    if (viewMode === "month") {
      setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1));
    } else {
      setCursor(addDays(cursor, -7));
    }
  };

  const handleNext = () => {
    if (viewMode === "month") {
      setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1));
    } else {
      setCursor(addDays(cursor, 7));
    }
  };

  const handleToday = () => setCursor(startOfDay(new Date()));

  const handleDayClick = (dateISO: string) => {
    if (!canManage) return;
    // 月ビューでの日付クリック: 10:00開始でフォーム起動
    const [y, m, d] = dateISO.split("-").map((s) => parseInt(s, 10));
    const start = new Date(y, m - 1, d, 10, 0, 0, 0);
    setCreateInitialStart(start);
    setShowCreate(true);
  };

  const handleSlotClick = (dateISO: string, hour: number) => {
    if (!canManage) return;
    const [y, m, d] = dateISO.split("-").map((s) => parseInt(s, 10));
    const start = new Date(y, m - 1, d, hour, 0, 0, 0);
    setCreateInitialStart(start);
    setShowCreate(true);
  };

  const handleCreateSubmit = (data: EventCreate | EventUpdate) => {
    createEvent.mutate(data as EventCreate, {
      onSuccess: () => {
        setShowCreate(false);
        setCreateInitialStart(null);
      },
    });
  };

  const handleUpdateSubmit = (data: EventCreate | EventUpdate) => {
    if (!editingEventId) return;
    updateEvent.mutate(
      { eventId: editingEventId, body: data as EventUpdate },
      {
        onSuccess: () => {
          setEditingEventId(null);
        },
      },
    );
  };

  // 編集対象の既存イベント（詳細モーダルと共有）
  const editingEvent = useMemo(() => {
    if (!editingEventId) return null;
    // List の EventListItem から最小限のプロパティを詳細風に構築する必要があるが、
    // EventFormModal は EventDetail を期待するため、詳細取得のキャッシュから拾う運用。
    // シンプルにするため、編集時は詳細モーダルを閉じてフォームを開く直前に URL 不要で動作する。
    // 実際のフォーム初期値は `existing` 経由のため、リスト上の情報で埋める。
    return events.find((e) => e.id === editingEventId) ?? null;
  }, [events, editingEventId]);

  const headerLabel = useMemo(() => {
    if (viewMode === "month") {
      return monthLabel(cursor.getFullYear(), cursor.getMonth());
    }
    const weekStart = startOfDay(addDays(cursor, -cursor.getDay()));
    const weekEnd = addDays(weekStart, 6);
    return `${weekStart.getMonth() + 1}/${weekStart.getDate()} 〜 ${weekEnd.getMonth() + 1}/${weekEnd.getDate()}`;
  }, [viewMode, cursor]);

  const dashboardPath = `/organizations/${orgId}/productions/${productionId}/dashboard`;
  const boardPath = `/organizations/${orgId}/productions/${productionId}/board`;

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-gray-400 hover:text-gray-600 text-sm">
            &larr; ホーム
          </Link>
          <h1 className="text-lg font-bold text-gray-900">カレンダー</h1>
          <Link
            to={dashboardPath}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            ダッシュボード
          </Link>
          <Link
            to={boardPath}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            カンバンボード
          </Link>
          <CountdownBadge orgId={orgId!} productionId={productionId!} />
        </div>
        <div className="flex items-center gap-2">
          {canManage && (
            <button
              type="button"
              onClick={() => {
                setCreateInitialStart(null);
                setShowCreate(true);
              }}
              className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700"
            >
              + イベント作成
            </button>
          )}
        </div>
      </header>

      <div className="px-6 py-3 bg-white border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handlePrev}
            className="px-2 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            ‹
          </button>
          <button
            type="button"
            onClick={handleToday}
            className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            今日
          </button>
          <button
            type="button"
            onClick={handleNext}
            className="px-2 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            ›
          </button>
          <span className="ml-3 text-base font-semibold text-gray-900">
            {headerLabel}
          </span>
        </div>
        <div className="flex items-center gap-1 rounded border border-gray-300 overflow-hidden">
          <button
            type="button"
            onClick={() => setViewMode("month")}
            className={`px-3 py-1 text-sm ${
              viewMode === "month"
                ? "bg-indigo-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-50"
            }`}
          >
            月
          </button>
          <button
            type="button"
            onClick={() => setViewMode("week")}
            className={`px-3 py-1 text-sm ${
              viewMode === "week"
                ? "bg-indigo-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-50"
            }`}
          >
            週
          </button>
        </div>
      </div>

      <main className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <div className="text-center text-gray-500 py-10">読み込み中...</div>
        ) : viewMode === "month" ? (
          <MonthView
            year={cursor.getFullYear()}
            month={cursor.getMonth()}
            events={events}
            onEventClick={(id) => setSelectedEventId(id)}
            onDayClick={handleDayClick}
          />
        ) : (
          <WeekView
            weekStart={startOfDay(addDays(cursor, -cursor.getDay()))}
            events={events}
            onEventClick={(id) => setSelectedEventId(id)}
            onSlotClick={handleSlotClick}
          />
        )}
      </main>

      {/* 詳細モーダル */}
      {selectedEventId && (
        <EventDetailModal
          orgId={orgId!}
          productionId={productionId!}
          eventId={selectedEventId}
          currentUserId={user?.id ?? null}
          canManage={canManage}
          members={members}
          onClose={() => setSelectedEventId(null)}
          onEdit={() => {
            setEditingEventId(selectedEventId);
            setSelectedEventId(null);
          }}
        />
      )}

      {/* 作成モーダル */}
      {showCreate && (
        <EventFormModal
          initialStart={createInitialStart}
          onSubmit={handleCreateSubmit}
          onClose={() => {
            setShowCreate(false);
            setCreateInitialStart(null);
          }}
          isSubmitting={createEvent.isPending}
        />
      )}

      {/* 編集モーダル */}
      {editingEvent && (
        <EventFormModal
          existing={{
            ...editingEvent,
            attendees: [],
            scenes: [],
          }}
          onSubmit={handleUpdateSubmit}
          onClose={() => setEditingEventId(null)}
          isSubmitting={updateEvent.isPending}
        />
      )}
    </div>
  );
}
