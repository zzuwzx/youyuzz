#pragma once
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <functional>

constexpr int SCREEN_W = 1280;
constexpr int SCREEN_H = 720;

constexpr int    MAX_FREE_TRIES       = 5;
constexpr const char* APP_NAME        = "Youyuzz";
constexpr const char* CONFIG_DIR      = "sdmc:/youyuzz/";
constexpr const char* CONFIG_FILE     = "sdmc:/youyuzz/config.json";
constexpr const char* CACHE_DIR       = "sdmc:/youyuzz/cache/";
constexpr const char* DOWNLOAD_DIR    = "sdmc:/youyuzz/downloads/";

constexpr const char* CF_AUTH_BASE    = "https://youyuzz-auth.zxxxwang-82a.workers.dev";
constexpr const char* DEFAULT_PC_IP   = "192.168.1.100";
constexpr int         DEFAULT_PC_PORT = 18888;

struct Color { uint8_t r, g, b, a; };
constexpr Color COLOR_BG       = { 20,  20,  30,  255 };
constexpr Color COLOR_TITLE    = { 100, 200, 255, 255 };
constexpr Color COLOR_TEXT     = { 220, 220, 230, 255 };
constexpr Color COLOR_TEXT_DIM = { 140, 140, 150, 255 };
constexpr Color COLOR_ACCENT   = { 80,  180, 255, 255 };
constexpr Color COLOR_SUCCESS  = { 80,  220, 120, 255 };
constexpr Color COLOR_ERROR    = { 240, 80,  80,  255 };
constexpr Color COLOR_PROGRESS = { 60,  160, 255, 255 };
constexpr Color COLOR_BAR_BG   = { 50,  50,  60,  255 };

struct GameItem {
    std::string title;
    std::string version;
    std::string size;
    std::string source_url;
};

struct GameDetail {
    std::string title;
    std::string body_url;
    std::string update_url;
    std::string dlc_url;
    std::string cheat_url;
    std::string image_url;
};

struct InstallProgress {
    std::string stage;
    float       percent  = 0.f;
    std::string current_file;
    std::string speed;
    std::string eta;
    int         total_files     = 0;
    int         completed_files = 0;
    std::string error;
    bool        done = false;
};