#pragma once
#include <string>
namespace youyuzz {
struct Config {
    std::string pc_ip           = "192.168.1.100";
    int         pc_port         = 18888;
    std::string license_key;
    bool        activated       = false;
    int         free_tries_used = 0;
    std::string pushdeer_key;
    bool load();
    bool save() const;
};
} // namespace youyuzz