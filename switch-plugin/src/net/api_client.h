#pragma once
#include "net/http_client.h"
#include "youyuzz_common.h"
#include <string>
#include <vector>
#include <functional>

namespace youyuzz {

struct ActivateResult {
    bool        success = false;
    std::string message;
    std::string license_key;
};

class ApiClient {
public:
    ApiClient();
    void set_pc_endpoint(const std::string& ip, int port);

    // PC Backend API
    std::vector<GameItem> search_games(const std::string& keyword, int limit = 10);
    GameDetail            get_game_detail(const std::string& url);
    std::string           start_install(const std::string& game_url);
    InstallProgress       get_install_progress(const std::string& task_id);
    bool                  listen_install_sse(const std::string& task_id,
                                             std::function<bool(const InstallProgress&)> cb);

    // Cloudflare Workers API
    ActivateResult activate_code(const std::string& code, const std::string& device_id);
    bool           verify_license(const std::string& license_key, const std::string& device_id);

    std::string last_error() const { return m_http.last_error(); }

private:
    HttpClient  m_http;
    std::string m_pc_base;
};

} // namespace youyuzz