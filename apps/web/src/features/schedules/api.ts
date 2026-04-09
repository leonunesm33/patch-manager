import { http } from "@/lib/http";
import type { ScheduleCreate, ScheduleItem } from "@/features/schedules/types";

export function fetchSchedules() {
  return http<ScheduleItem[]>("/schedules");
}

export function createSchedule(payload: ScheduleCreate) {
  return http<ScheduleItem>("/schedules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSchedule(scheduleId: string, payload: ScheduleCreate) {
  return http<ScheduleItem>(`/schedules/${scheduleId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteSchedule(scheduleId: string) {
  return http<void>(`/schedules/${scheduleId}`, {
    method: "DELETE",
  });
}
