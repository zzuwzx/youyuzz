#include "net/api_client.h"
#include <cstdio>
#include <cstring>

namespace youyuzz {

ApiClient::ApiClient() { set_pc_endpoint(DEFAULT_PC_IP, DEFAULT_PC_PORT); }

void ApiClient::set_pc_endpoint(const std::string& ip, int port) {
    char buf[128];
    snprintf(buf, sizeof(buf), "http://%s:%d", ip.c_str(), port);
    m_pc_base = buf;
}

// Minimal JSON extractors
static std::string jstr(const std::string& json, const std::string& key) {
    std::string needle = "\"" + key + "\"";
    size_t pos = json.find(needle);
    if (pos == std::string::npos) return "";
    pos = json.find(':', pos + needle.size());
    if (pos == std::string::npos) return "";
    pos++;
    while (pos < json.size() && (json[pos] == ' ' || json[pos] == '\t')) pos++;
    if (pos >= json.size() || json[pos] != '"') return "";
    pos++;
    size_t end = json.find('"', pos);
    if (end == std::string::npos) return "";
    return json.substr(pos, end - pos);
}

static int jint(const std::string& json, const std::string& key) {
    std::string needle = "\"" + key + "\"";
    size_t pos = json.find(needle);
    if (pos == std::string::npos) return 0;
    pos = json.find(':', pos + needle.size());
    if (pos == std::string::npos) return 0;
    return atoi(json.c_str() + pos + 1);
}

static float jfloat(const std::string& json, const std::string& key) {
    std::string needle = "\"" + key + "\"";
    size_t pos = json.find(needle);
    if (pos == std::string::npos) return 0.f;
    pos = json.find(':', pos + needle.size());
    if (pos == std::string::npos) return 0.f;
    return strtof(json.c_str() + pos + 1, nullptr);
}

static std::vector<GameItem> parse_search_results(const std::string& json) {
    std::vector<GameItem> results;
    size_t search_pos = 0;
    while (true) {
        size_t pos = json.find("\"title\"", search_pos);
        if (pos == std::string::npos) break;
        size_t obj_start = json.rfind('{', pos);
        size_t obj_end = json.find('}', pos);
        if (obj_start == std::string::npos || obj_end == std::string::npos) break;
        std::string obj = json.substr(obj_start, obj_end - obj_start + 1);
        GameItem item;
        item.title      = jstr(obj, "title");
        item.version    = jstr(obj, "version");
        item.size       = jstr(obj, "size");
        item.source_url = jstr(obj, "source_url");
        if (!item.title.empty()) results.push_back(item);
        search_pos = obj_end + 1;
    }
    return results;
}

std::vector<GameItem> ApiClient::search_games(const std::string& keyword, int limit) {
    char url[512];
    snprintf(url, sizeof(url), "%s/api/search?keyword=%s&limit=%d", m_pc_base.c_str(), keyword.c_str(), limit);
    std::string resp = m_http.get(url);
    if (resp.empty()) return {};
    return parse_search_results(resp);
}

GameDetail ApiClient::get_game_detail(const std::string& url) {
    char api_url[512];
    snprintf(api_url, sizeof(api_url), "%s/api/game/detail?url=%s", m_pc_base.c_str(), url.c_str());
    std::string resp = m_http.get(api_url);
    GameDetail d;
    if (resp.empty()) return d;
    d.title      = jstr(resp, "title");
    d.body_url   = jstr(resp, "body_url");
    d.update_url = jstr(resp, "update_url");
    d.dlc_url    = jstr(resp, "dlc_url");
    d.cheat_url  = jstr(resp, "cheat_url");
    d.image_url  = jstr(resp, "image_url");
    return d;
}

std::string ApiClient::start_install(const std::string& game_url) {
    char api_url[256];
    snprintf(api_url, sizeof(api_url), "%s/api/install", m_pc_base.c_str());
    char body[512];
    snprintf(body, sizeof(body), "{\"game_url\":\"%s\",\"install_order\":\"sequential\"}", game_url.c_str());
    std::string resp = m_http.post_json(api_url, body);
    return jstr(resp, "task_id");
}

InstallProgress ApiClient::get_install_progress(const std::string& task_id) {
    char url[256];
    snprintf(url, sizeof(url), "%s/api/install/%s/progress", m_pc_base.c_str(), task_id.c_str());
    std::string resp = m_http.get(url);
    InstallProgress p;
    if (resp.empty()) { p.error = "Network error"; p.done = true; return p; }
    p.stage           = jstr(resp, "stage");
    p.percent         = jfloat(resp, "percent");
    p.current_file    = jstr(resp, "current_file");
    p.speed           = jstr(resp, "speed");
    p.eta             = jstr(resp, "eta");
    p.total_files     = jint(resp, "total_files");
    p.completed_files = jint(resp, "completed_files");
    p.error           = jstr(resp, "error");
    p.done = (p.stage == "completed" || p.stage == "failed" || p.stage == "cancelled");
    return p;
}

bool ApiClient::listen_install_sse(const std::string& task_id, std::function<bool(const InstallProgress&)> cb) {
    char url[256];
    snprintf(url, sizeof(url), "%s/api/install/%s/stream", m_pc_base.c_str(), task_id.c_str());
    return m_http.sse_listen(url, [&](const std::string& line) -> bool {
        InstallProgress p;
        p.stage           = jstr(line, "stage");
        p.percent         = jfloat(line, "percent");
        p.current_file    = jstr(line, "current_file");
        p.speed           = jstr(line, "speed");
        p.eta             = jstr(line, "eta");
        p.total_files     = jint(line, "total_files");
        p.completed_files = jint(line, "completed_files");
        p.error           = jstr(line, "error");
        p.done = (p.stage == "completed" || p.stage == "failed" || p.stage == "cancelled");
        return cb(p);
    });
}

ActivateResult ApiClient::activate_code(const std::string& code, const std::string& device_id) {
    char url[256];
    snprintf(url, sizeof(url), "%s/api/auth/activate", CF_AUTH_BASE);
    char body[512];
    snprintf(body, sizeof(body), "{\"code\":\"%s\",\"device_id\":\"%s\",\"device_type\":\"switch\"}", code.c_str(), device_id.c_str());
    std::string resp = m_http.post_json(url, body);
    ActivateResult r;
    if (resp.empty()) { r.message = m_http.last_error(); return r; }
    r.success     = resp.find("\"success\":true") != std::string::npos;
    r.message     = jstr(resp, "message");
    r.license_key = jstr(resp, "license_key");
    return r;
}

bool ApiClient::verify_license(const std::string& license_key, const std::string& device_id) {
    char url[256];
    snprintf(url, sizeof(url), "%s/api/auth/verify?license_key=%s&device_id=%s", CF_AUTH_BASE, license_key.c_str(), device_id.c_str());
    std::string resp = m_http.get(url);
    return resp.find("\"active\":true") != std::string::npos ||
           resp.find("\"valid\":true") != std::string::npos;
}

} // namespace youyuzz