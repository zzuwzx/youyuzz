#pragma once
#include "config/config.h"
#include "net/api_client.h"
#include <string>

namespace youyuzz {

class Auth {
public:
    Auth(Config& config, ApiClient& api);

    bool        can_use() const;
    bool        use_free_try();
    std::string activate(const std::string& code);
    bool        verify_online();
    bool        is_activated() const { return m_config.activated; }
    int         free_tries_remaining() const;
    std::string get_device_id() const;

private:
    Config&    m_config;
    ApiClient& m_api;
};

} // namespace youyuzz