#include "ctrl_uart.h"
#include "dac_output.h"
#include <stdlib.h>

static String g_line;

static bool json_get_string(const String &s, const char *key, char *out, size_t outLen) {
  String pat = String("\"") + key + "\"";
  int k = s.indexOf(pat);
  if (k < 0) return false;
  int colon = s.indexOf(':', k + pat.length());
  if (colon < 0) return false;
  int q1 = s.indexOf('"', colon + 1);
  if (q1 < 0) return false;
  int q2 = s.indexOf('"', q1 + 1);
  if (q2 < 0) return false;
  String v = s.substring(q1 + 1, q2);
  strlcpy(out, v.c_str(), outLen);
  return true;
}

static bool json_get_u32(const String &s, const char *key, uint32_t &out) {
  String pat = String("\"") + key + "\"";
  int k = s.indexOf(pat);
  if (k < 0) return false;
  int colon = s.indexOf(':', k + pat.length());
  if (colon < 0) return false;
  // skip spaces
  int i = colon + 1;
  while (i < (int)s.length() && (s[i] == ' ' || s[i] == '\t')) i++;
  if (i >= (int)s.length()) return false;
  char *endp = nullptr;
  out = strtoul(s.c_str() + i, &endp, 10);
  return endp != s.c_str() + i;
}

static bool json_get_float(const String &s, const char *key, float &out) {
  String pat = String("\"") + key + "\"";
  int k = s.indexOf(pat);
  if (k < 0) return false;
  int colon = s.indexOf(':', k + pat.length());
  if (colon < 0) return false;
  int i = colon + 1;
  while (i < (int)s.length() && (s[i] == ' ' || s[i] == '\t')) i++;
  char *endp = nullptr;
  out = strtof(s.c_str() + i, &endp);
  return endp != s.c_str() + i;
}

static void emit_status(const QamConfig &cfg) {
  DacStatus st = dac_output_status();
  Serial.printf("{\"ok\":true,\"cmd\":\"status\",\"streaming\":%s,\"symbol_rate\":%u,\"sps\":%u,\"sample_rate\":%u,\"gain\":%.3f,\"modulation\":\"%s\",\"shape\":\"%s\",\"seed\":%u,\"frames\":%u,\"loaded\":%u,\"buf_bytes\":%u,\"uptime_s\":%.2f,\"last_error\":\"%s\"}\n",
                st.streaming ? "true" : "false", cfg.symbol_rate, cfg.sps, st.sample_rate, cfg.gain,
                cfg.modulation, cfg.shape, cfg.seed, st.frames_emitted, (unsigned)st.loaded_bytes,
                (unsigned)st.buf_bytes, millis() / 1000.0, dac_output_last_error());
}

static void emit_ok(const char *cmd, const char *msg = "ok") {
  Serial.printf("{\"ok\":true,\"cmd\":\"%s\",\"msg\":\"%s\"}\n", cmd, msg);
}
static void emit_err(const char *cmd, const char *msg) {
  Serial.printf("{\"ok\":false,\"cmd\":\"%s\",\"error\":\"%s\"}\n", cmd, msg);
}

void ctrl_uart_init(uint32_t baud) {
  Serial.begin(baud);
  g_line.reserve(256);
}

void ctrl_uart_poll(QamConfig &active, QamConfig &pending, bool &pendingValid) {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (g_line.length() == 0) continue;
      String s = g_line;
      g_line = "";
      char cmd[24] = {};
      if (!json_get_string(s, "cmd", cmd, sizeof(cmd))) { emit_err("unknown", "missing cmd"); continue; }

      if (strcmp(cmd, "configure") == 0) {
        QamConfig c = pendingValid ? pending : active;
        json_get_string(s, "modulation", c.modulation, sizeof(c.modulation));
        json_get_string(s, "shape", c.shape, sizeof(c.shape));
        json_get_u32(s, "symbol_rate", c.symbol_rate);
        json_get_u32(s, "sps", c.sps);
        json_get_u32(s, "seed", c.seed);
        json_get_float(s, "gain", c.gain);
        if (c.sps == 0) c.sps = 8;
        if (c.symbol_rate == 0) c.symbol_rate = 20000;
        if (c.gain <= 0 || c.gain > 1.0f) c.gain = 0.8f;
        pending = c;
        pendingValid = true;
        emit_ok("configure", "pending config stored; apply with start/restart");
      } else if (strcmp(cmd, "start") == 0) {
        if (pendingValid) { active = pending; pendingValid = false; }
        if (dac_output_start(active)) emit_status(active);
        else emit_err("start", dac_output_last_error());
      } else if (strcmp(cmd, "stop") == 0) {
        dac_output_stop();
        emit_ok("stop");
      } else if (strcmp(cmd, "restart") == 0) {
        if (pendingValid) { active = pending; pendingValid = false; }
        dac_output_stop();
        if (dac_output_start(active)) emit_status(active);
        else emit_err("restart", dac_output_last_error());
      } else if (strcmp(cmd, "status") == 0) {
        emit_status(active);
      } else {
        emit_err(cmd, "unknown cmd");
      }
    } else {
      if (g_line.length() < 512) g_line += ch;
    }
  }
}