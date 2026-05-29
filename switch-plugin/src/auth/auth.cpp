#include "auth/auth.h"
#include "youyuzz_common.h"
#include <cstdio>
#include <switch.h>

namespace youyuzz {

Auth::Auth(Config& config, ApiClient& api) : m_config(config), m_api(api) {}

bool Auth::can_use() const {
    return m_config.activated || m_config.free_tries_used < MAX_FREE_TRIES;
}

bool Auth::use_free_try() {
    if (m_config.activated) return true;
    if (m_config.free_tries_used >= MAX_FREE_TRIES) return false;
    m_config.free_tries_used++;
    m_config.save();
    return true;
}

int Auth::free_tries_remaining() const {
    if (m_config.activated) return -1;
    return MAX_FREE_TRIES - m_config.free_tries_used;
}

std::string Auth::get_device_id() const {
    AccountUid uid = {0};
    accountGetLastOpenedUser(&uid);
    char id_str[64];
    snprintf(id_str, sizeof(id_str), "%016lx%016lx", uid.uid[1], uid.uid[0]);
    return std::string(id_str);
}

std::string Auth::activate(const std::string& code) {
    std::string device_id = get_device_id();
    auto result = m_api.activate_code(code, device_id);
    if (result.success) {
        m_config.activated = true;
        m_config.license_key = result.license_key;
        m_config.save();
    }
    return result.message;
}

bool Auth::verify_online() {
    if (m_config.license_key.empty()) return false;
    std::string device_id = get_device_id();
    bool valid = m_api.verify_license(m_config.license_key, device_id);
    if (!valid) {
        m_config.activated = false;
        m_config.save();
    }
    return valid;
}

} // namespace youyuzz