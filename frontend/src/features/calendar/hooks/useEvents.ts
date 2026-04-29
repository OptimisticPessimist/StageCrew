import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  AttendeeAdd,
  AttendeeUpdate,
  EventAttendee,
  EventCreate,
  EventDetail,
  EventListItem,
  EventUpdate,
} from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/events`;
}

function listKey(orgId: string, productionId: string, range?: DateRange) {
  return [
    "events",
    orgId,
    productionId,
    range?.startFrom ?? null,
    range?.startTo ?? null,
  ] as const;
}

function detailKey(
  orgId: string,
  productionId: string,
  eventId: string,
) {
  return ["event", orgId, productionId, eventId] as const;
}

export interface DateRange {
  startFrom?: string;
  startTo?: string;
}

export function useEvents(
  orgId: string,
  productionId: string,
  range?: DateRange,
) {
  return useQuery({
    queryKey: listKey(orgId, productionId, range),
    queryFn: () => {
      const params = new URLSearchParams();
      if (range?.startFrom) params.set("start_from", range.startFrom);
      if (range?.startTo) params.set("start_to", range.startTo);
      const qs = params.toString();
      return api.get<EventListItem[]>(
        `${basePath(orgId, productionId)}/${qs ? `?${qs}` : ""}`,
      );
    },
  });
}

export function useEvent(
  orgId: string,
  productionId: string,
  eventId: string | null,
) {
  return useQuery({
    queryKey: detailKey(orgId, productionId, eventId ?? ""),
    queryFn: () =>
      api.get<EventDetail>(`${basePath(orgId, productionId)}/${eventId}`),
    enabled: !!eventId,
  });
}

function invalidateAllEvents(
  qc: ReturnType<typeof useQueryClient>,
  orgId: string,
  productionId: string,
) {
  qc.invalidateQueries({ queryKey: ["events", orgId, productionId] });
}

export function useCreateEvent(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EventCreate) =>
      api.post<EventDetail>(`${basePath(orgId, productionId)}/`, body),
    onSuccess: () => invalidateAllEvents(qc, orgId, productionId),
  });
}

export function useUpdateEvent(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      eventId,
      body,
    }: {
      eventId: string;
      body: EventUpdate;
    }) =>
      api.patch<EventDetail>(
        `${basePath(orgId, productionId)}/${eventId}`,
        body,
      ),
    onSuccess: (_data, vars) => {
      invalidateAllEvents(qc, orgId, productionId);
      qc.invalidateQueries({
        queryKey: detailKey(orgId, productionId, vars.eventId),
      });
    },
  });
}

export function useDeleteEvent(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) =>
      api.delete(`${basePath(orgId, productionId)}/${eventId}`),
    onSuccess: () => invalidateAllEvents(qc, orgId, productionId),
  });
}

export function useAddAttendees(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      eventId,
      body,
    }: {
      eventId: string;
      body: AttendeeAdd;
    }) =>
      api.post<EventAttendee[]>(
        `${basePath(orgId, productionId)}/${eventId}/attendees`,
        body,
      ),
    onSuccess: (_data, vars) =>
      qc.invalidateQueries({
        queryKey: detailKey(orgId, productionId, vars.eventId),
      }),
  });
}

export function useUpdateAttendee(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      eventId,
      userId,
      body,
    }: {
      eventId: string;
      userId: string;
      body: AttendeeUpdate;
    }) =>
      api.patch<EventAttendee>(
        `${basePath(orgId, productionId)}/${eventId}/attendees/${userId}`,
        body,
      ),
    onSuccess: (_data, vars) =>
      qc.invalidateQueries({
        queryKey: detailKey(orgId, productionId, vars.eventId),
      }),
  });
}

export function useRemoveAttendee(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      eventId,
      userId,
    }: {
      eventId: string;
      userId: string;
    }) =>
      api.delete(
        `${basePath(orgId, productionId)}/${eventId}/attendees/${userId}`,
      ),
    onSuccess: (_data, vars) =>
      qc.invalidateQueries({
        queryKey: detailKey(orgId, productionId, vars.eventId),
      }),
  });
}
