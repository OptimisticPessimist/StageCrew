-- ============================================================
-- 締切リマインダー: pg_cron + pg_net
-- Supabase ダッシュボード > SQL Editor で実行するか、
-- supabase db push で適用する。
-- ============================================================

-- 拡張を有効化
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- 締切リマインダー関数
CREATE OR REPLACE FUNCTION public.notify_deadline_reminders()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  prod RECORD;
  issue RECORD;
  payload TEXT;
  fields TEXT;
  field_entry TEXT;
  max_days INT := 3;
  reminder_days INT[] := ARRAY[3, 1];
  has_fields BOOLEAN;
BEGIN
  -- webhook URL を持つ各 production を処理
  FOR prod IN
    SELECT id, name, discord_webhook_url
    FROM public.productions
    WHERE discord_webhook_url IS NOT NULL
      AND discord_webhook_url != ''
  LOOP
    fields := '';
    has_fields := false;

    FOR issue IN
      SELECT
        i.title,
        i.due_date,
        (i.due_date::date - CURRENT_DATE) AS days_remaining
      FROM public.issues i
      LEFT JOIN public.status_definitions sd ON i.status_id = sd.id
      WHERE i.production_id = prod.id
        AND i.due_date IS NOT NULL
        AND i.due_date::date <= CURRENT_DATE + make_interval(days => max_days + 1)
        AND (i.status_id IS NULL OR sd.is_closed = false)
      ORDER BY (i.due_date::date - CURRENT_DATE)
    LOOP
      -- reminder_days に一致するか、期限超過の場合のみ通知
      IF issue.days_remaining < 0 OR issue.days_remaining = ANY(reminder_days) THEN
        field_entry := format(
          '{"name": %s, "value": "%s日%s", "inline": false}',
          to_json(issue.title),
          ABS(issue.days_remaining),
          CASE WHEN issue.days_remaining < 0 THEN '超過' ELSE '前' END
        );

        IF has_fields THEN
          fields := fields || ', ';
        END IF;
        fields := fields || field_entry;
        has_fields := true;
      END IF;
    END LOOP;

    IF has_fields THEN
      payload := format(
        '{"embeds": [{"title": %s, "color": 15105570, "fields": [%s]}]}',
        to_json('📅 締切リマインダー - ' || prod.name),
        fields
      );

      PERFORM net.http_post(
        url := prod.discord_webhook_url,
        headers := '{"Content-Type": "application/json"}'::jsonb,
        body := payload::jsonb
      );
    END IF;
  END LOOP;
END;
$$;

-- 毎日 00:00 UTC (JST 09:00) に実行
SELECT cron.schedule(
  'deadline-reminders',
  '0 0 * * *',
  'SELECT public.notify_deadline_reminders()'
);
