#include "net/http_client.h"
#include <curl/curl.h>
#include <cstdio>
#include <cstring>

namespace youyuzz {

static size_t write_cb(char* ptr, size_t size, size_t nmemb, void* userdata) {
    auto* str = static_cast<std::string*>(userdata);
    str->append(ptr, size * nmemb);
    return size * nmemb;
}

struct FileCtx {
    FILE* fp;
    ProgressCb cb;
};

static size_t file_write_cb(char* ptr, size_t size, size_t nmemb, void* userdata) {
    auto* ctx = static_cast<FileCtx*>(userdata);
    return fwrite(ptr, size, nmemb, ctx->fp);
}

static int progress_cb_wrapper(void* clientp, curl_off_t dltotal, curl_off_t dlnow, curl_off_t, curl_off_t) {
    auto* ctx = static_cast<FileCtx*>(clientp);
    if (ctx->cb) {
        return ctx->cb(dlnow, dltotal) ? 0 : 1;
    }
    return 0;
}

struct SseCtx {
    std::function<bool(const std::string&)> callback;
    std::string buffer;
};

static size_t sse_write_cb(char* ptr, size_t size, size_t nmemb, void* userdata) {
    auto* ctx = static_cast<SseCtx*>(userdata);
    ctx->buffer.append(ptr, size * nmemb);
    size_t pos;
    while ((pos = ctx->buffer.find('\n')) != std::string::npos) {
        std::string line = ctx->buffer.substr(0, pos);
        ctx->buffer.erase(0, pos + 1);
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.rfind("data:", 0) == 0) {
            std::string payload = line.substr(5);
            if (!payload.empty() && payload[0] == ' ') payload.erase(0, 1);
            if (!ctx->callback(payload)) return 0;
        }
    }
    return size * nmemb;
}

HttpClient::HttpClient()  { curl_global_init(CURL_GLOBAL_ALL); }
HttpClient::~HttpClient() { curl_global_cleanup(); }

std::string HttpClient::get(const std::string& url, long timeout_sec) {
    m_last_error.clear();
    CURL* curl = curl_easy_init();
    if (!curl) { m_last_error = "curl_easy_init failed"; return ""; }
    std::string response;
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_sec);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 10L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "Youyuzz-Switch/1.0");
    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) { m_last_error = curl_easy_strerror(res); response.clear(); }
    curl_easy_cleanup(curl);
    return response;
}

std::string HttpClient::post_json(const std::string& url, const std::string& json_body, long timeout_sec) {
    m_last_error.clear();
    CURL* curl = curl_easy_init();
    if (!curl) { m_last_error = "curl_easy_init failed"; return ""; }
    std::string response;
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_body.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_sec);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 10L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "Youyuzz-Switch/1.0");
    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) { m_last_error = curl_easy_strerror(res); response.clear(); }
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    return response;
}

bool HttpClient::download(const std::string& url, const std::string& dest_path, ProgressCb progress_cb, long timeout_sec) {
    m_last_error.clear();
    FILE* fp = fopen(dest_path.c_str(), "wb");
    if (!fp) { m_last_error = "Cannot open: " + dest_path; return false; }
    CURL* curl = curl_easy_init();
    if (!curl) { fclose(fp); m_last_error = "curl_easy_init failed"; return false; }
    FileCtx ctx{fp, progress_cb};
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, file_write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &ctx);
    curl_easy_setopt(curl, CURLOPT_XFERINFOFUNCTION, progress_cb_wrapper);
    curl_easy_setopt(curl, CURLOPT_XFERINFODATA, &ctx);
    curl_easy_setopt(curl, CURLOPT_NOPROGRESS, 0L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_sec);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 15L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "Youyuzz-Switch/1.0");
    CURLcode res = curl_easy_perform(curl);
    fclose(fp);
    curl_easy_cleanup(curl);
    if (res != CURLE_OK) { m_last_error = curl_easy_strerror(res); return false; }
    return true;
}

bool HttpClient::sse_listen(const std::string& url, std::function<bool(const std::string&)> callback, long timeout_sec) {
    m_last_error.clear();
    CURL* curl = curl_easy_init();
    if (!curl) { m_last_error = "curl_easy_init failed"; return false; }
    SseCtx ctx{callback, ""};
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, sse_write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &ctx);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_sec);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 10L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "Youyuzz-Switch/1.0");
    CURLcode res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);
    if (res != CURLE_OK && res != CURLE_WRITE_ERROR) {
        m_last_error = curl_easy_strerror(res);
        return false;
    }
    return true;
}

} // namespace youyuzz