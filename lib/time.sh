#!/usr/bin/env bash
# time.sh
# 通用時間工具（sleep / next boundary）
# 不在這裡 set -euo pipefail，交給呼叫端決定。

if [[ -n "${TIME_SH_LOADED:-}" ]]; then
  return 0 2>/dev/null || exit 0
fi
TIME_SH_LOADED=1

# 平台分支：macOS (BSD date) vs Linux (GNU date)
if date -d "@0" '+%s' >/dev/null 2>&1; then
  _date_from_epoch() { date -d "@$1" "$2"; }
  _date_from_str()   { date -d "$1" "$2"; }
else
  # macOS BSD date
  _date_from_epoch() { date -r "$1" "$2"; }
  _date_from_str()   {
    # Approximate: parse "today HH:00:00" / "tomorrow HH:00:00"
    local str="$1" fmt="$2"
    local hh="${str##* }"
    hh="${hh%%:*}"
    local today_epoch
    today_epoch="$(date -j -f '%Y-%m-%d %H:%M:%S' "$(date '+%Y-%m-%d') ${hh}:00:00" '+%s' 2>/dev/null || echo 0)"
    if echo "$str" | grep -q "tomorrow"; then
      today_epoch=$(( today_epoch + 86400 ))
    fi
    date -r "$today_epoch" "$fmt"
  }
fi

sleep_until_next_hour() {
  local now_ts next_ts sleep_sec
  now_ts="$(date +%s)"
  next_ts=$(( (now_ts/3600 + 1) * 3600 ))
  sleep_sec=$(( next_ts - now_ts ))
  echo "下一次醒來：$(_date_from_epoch "$next_ts" '+%Y-%m-%d %H:%M:%S')（${sleep_sec}s）"
  sleep "$sleep_sec"
}

# 需要外部先設定 START_HOUR / END_HOUR（或你也可以改成參數式）
sleep_until_next_start_hour() {
  local now_ts hour target_ts sleep_sec
  now_ts="$(date +%s)"
  hour="$(date +%H)"

  if (( 10#$hour < 10#${START_HOUR} )); then
    target_ts="$(_date_from_str "today ${START_HOUR}:00:00" '+%s')"
  else
    target_ts="$(_date_from_str "tomorrow ${START_HOUR}:00:00" '+%s')"
  fi

  sleep_sec=$(( target_ts - now_ts ))
  echo "本次任務：不在時段（${START_HOUR}–${END_HOUR}）"
  echo "睡到：$(_date_from_epoch "$target_ts" '+%Y-%m-%d %H:%M:%S')（${sleep_sec}s）"
  sleep "$sleep_sec"
}