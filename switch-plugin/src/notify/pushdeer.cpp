#include "notify/pushdeer.h"
#include <curl/curl.h>
#include <cstdio>

namespace youyuzz {

static const char* PUSHDEER_API = "https://api2.pushdeer.com/message/push";

static size_t discard_cb(char* ptr, size_t size, size_t nmemb, void* userdata) {
    return size * nmemb;
}

PushDeer::PushDeer() {}
PushDeer::~PushDeer() {}

void PushDeer::set_key(const std::string& key) {
    m_key = key;
}

bool PushDeer::is_configured() const {
    return !m_key.empty();
}

bool PushDeer::send(const std::string& title, const std::string& content) {
    if (m_key.empty()) return false;

    CURL* curl = curl_easy_init();
    if (!curl) return false;

    // Build POST body: pushkey=xxx&text=title\ndesp=content&type=markdown
    char post_body[2048];
    snprintf(post_body, sizeof(post_body),
             "pushkey=%s&text=%s&desp=%s&type=markdown",
             m_key.c_str(), title.c_str(), content.c_str());

    curl_easy_setopt(curl, CURLOPT_URL, PUSHDEER_API);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, post_body);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, discard_cb);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 5L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "Youyuzz-Switch/1.0");

    CURLcode res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        printf("PushDeer send failed: %s\n", curl_easy_strerror(res));
        return false;
    }
    return true;
}

} // namespace youyuzz