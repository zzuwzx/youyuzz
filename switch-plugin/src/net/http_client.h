#pragma once
#include <string>
#include <functional>

namespace youyuzz {

using ProgressCb = std::function<bool(int64_t current, int64_t total)>;

class HttpClient {
public:
    HttpClient();
    ~HttpClient();

    std::string get(const std::string& url, long timeout_sec = 15);
    std::string post_json(const std::string& url, const std::string& json_body, long timeout_sec = 15);
    bool download(const std::string& url, const std::string& dest_path,
                  ProgressCb progress_cb = nullptr, long timeout_sec = 300);
    bool sse_listen(const std::string& url,
                    std::function<bool(const std::string& line)> callback,
                    long timeout_sec = 60);

    std::string last_error() const { return m_last_error; }

private:
    std::string m_last_error;
};

} // namespace youyuzz