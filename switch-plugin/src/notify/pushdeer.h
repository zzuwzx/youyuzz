#pragma once
#include <string>

namespace youyuzz {

class PushDeer {
public:
    PushDeer();
    ~PushDeer();

    void set_key(const std::string& key);
    bool send(const std::string& title, const std::string& content);
    bool is_configured() const;

private:
    std::string m_key;
};

} // namespace youyuzz