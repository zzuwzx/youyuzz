#include "config/config.h"
#include "youyuzz_common.h"
#include <cstdio>
#include <cstring>
#include <sys/stat.h>

namespace youyuzz {

static std::string extract_string(const char* json, const char* key) {
    char search[128];
    snprintf(search, sizeof(search), "\"%s\"", key);
    const char* p = strstr(json, search);
    if (!p) return "";
    p = strchr(p + strlen(search), ':');
    if (!p) return "";
    p++;
    while (*p == ' ' || *p == '\t') p++;
    if (*p == '"') {
        p++;
        const char* end = strchr(p, '"');
        if (!end) return "";
        return std::string(p, end - p);
    }
    return "";
}

static int extract_int(const char* json, const char* key) {
    char search[128];
    snprintf(search, sizeof(search), "\"%s\"", key);
    const char* p = strstr(json, search);
    if (!p) return 0;
    p = strchr(p + strlen(search), ':');
    if (!p) return 0;
    return atoi(p + 1);
}

static bool extract_bool(const char* json, const char* key) {
    char search[128];
    snprintf(search, sizeof(search), "\"%s\"", key);
    const char* p = strstr(json, search);
    if (!p) return false;
    return strstr(p, "true") != nullptr;
}

bool Config::load() {
    FILE* f = fopen(CONFIG_FILE, "r");
    if (!f) return false;
    char buf[1024] = {0};
    fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);

    pc_ip = extract_string(buf, "pc_ip");
    if (pc_ip.empty()) pc_ip = DEFAULT_PC_IP;
    pc_port = extract_int(buf, "pc_port");
    if (pc_port <= 0) pc_port = DEFAULT_PC_PORT;
    license_key = extract_string(buf, "license_key");
    activated = extract_bool(buf, "activated");
    free_tries_used = extract_int(buf, "free_tries_used");
    pushdeer_key = extract_string(buf, "pushdeer_key");
    return true;
}

bool Config::save() const {
    mkdir(CONFIG_DIR, 0777);
    FILE* f = fopen(CONFIG_FILE, "w");
    if (!f) return false;
    fprintf(f, "{\n");
    fprintf(f, "  \"pc_ip\": \"%s\",\n", pc_ip.c_str());
    fprintf(f, "  \"pc_port\": %d,\n", pc_port);
    fprintf(f, "  \"license_key\": \"%s\",\n", license_key.c_str());
    fprintf(f, "  \"activated\": %s,\n", activated ? "true" : "false");
    fprintf(f, "  \"free_tries_used\": %d,\n", free_tries_used);
    fprintf(f, "  \"pushdeer_key\": \"%s\"\n", pushdeer_key.c_str());
    fprintf(f, "}\n");
    fclose(f);
    return true;
}

} // namespace youyuzz