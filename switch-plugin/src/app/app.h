#pragma once
#include "app/app_state.h"
#include "config/config.h"
#include "gui/gui.h"
#include "net/api_client.h"
#include "auth/auth.h"
#include "notify/pushdeer.h"
#include "youyuzz_common.h"
#include <string>
#include <vector>
#include <thread>
#include <atomic>
#include <mutex>

namespace youyuzz {

class App {
public:
    App();
    ~App();
    bool init();
    void run();

private:
    AppState    m_state = AppState::MAIN_MENU;
    bool        m_running = false;
    int         m_menu_index = 0;

    Config      m_config;
    Gui         m_gui;
    ApiClient   m_api;
    Auth        m_auth;
    PushDeer    m_pushdeer;

    std::string m_search_keyword;
    std::vector<GameItem> m_search_results;
    int         m_result_index = 0;

    GameDetail  m_current_detail;
    std::string m_current_source_url;

    std::string m_task_id;
    InstallProgress m_install_progress;
    std::atomic<bool> m_installing{false};
    std::mutex  m_progress_mutex;

    std::string m_message;
    uint32_t    m_message_timer = 0;

    uint64_t    m_held = 0;
    uint64_t    m_pressed = 0;

    void handle_main_menu();
    void handle_search();
    void handle_search_results();
    void handle_game_detail();
    void handle_installing();
    void handle_activate();
    void handle_settings();

    void render_main_menu();
    void render_search();
    void render_search_results();
    void render_game_detail();
    void render_installing();
    void render_activate();
    void render_settings();

    void poll_input();
    bool just_pressed(uint64_t key);
    void show_message(const std::string& msg, uint32_t duration_frames = 180);
    void check_activation_status();
    void notify(const std::string& title, const std::string& content);
};

} // namespace youyuzz