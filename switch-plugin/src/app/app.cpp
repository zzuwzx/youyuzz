#include "app/app.h"
#include <cstdio>
#include <cstring>
#include <switch.h>

namespace youyuzz {

App::App() : m_auth(m_config, m_api) {}
App::~App() {}

bool App::init() {
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    m_config.load();
    m_api.set_pc_endpoint(m_config.pc_ip, m_config.pc_port);
    m_pushdeer.set_key(m_config.pushdeer_key);
    mkdir(CONFIG_DIR, 0777);
    mkdir(CACHE_DIR, 0777);
    mkdir(DOWNLOAD_DIR, 0777);
    if (!m_gui.init()) return false;
    m_running = true;
    return true;
}

void App::notify(const std::string& title, const std::string& content) {
    if (m_pushdeer.is_configured()) {
        std::thread([this, title, content]() {
            m_pushdeer.send(title, content);
        }).detach();
    }
}

void App::run() {
    while (m_running) {
        poll_input();
        switch (m_state) {
            case AppState::MAIN_MENU:      handle_main_menu(); break;
            case AppState::SEARCH:         handle_search(); break;
            case AppState::SEARCH_RESULTS: handle_search_results(); break;
            case AppState::GAME_DETAIL:    handle_game_detail(); break;
            case AppState::INSTALLING:     handle_installing(); break;
            case AppState::ACTIVATE:       handle_activate(); break;
            case AppState::SETTINGS:       handle_settings(); break;
            case AppState::EXIT:           m_running = false; break;
        }
        m_gui.begin_frame();
        switch (m_state) {
            case AppState::MAIN_MENU:      render_main_menu(); break;
            case AppState::SEARCH:         render_search(); break;
            case AppState::SEARCH_RESULTS: render_search_results(); break;
            case AppState::GAME_DETAIL:    render_game_detail(); break;
            case AppState::INSTALLING:     render_installing(); break;
            case AppState::ACTIVATE:       render_activate(); break;
            case AppState::SETTINGS:       render_settings(); break;
            default: break;
        }
        if (m_message_timer > 0) {
            m_message_timer--;
            int mw = m_gui.text_width(m_message) + 40;
            int mx = (SCREEN_W - mw) / 2;
            m_gui.draw_rect(mx, SCREEN_H - 120, mw, 36, {40, 40, 60, 220});
            m_gui.draw_text(mx + 20, SCREEN_H - 112, m_message, COLOR_TEXT, 14);
        }
        m_gui.end_frame();
    }
}

void App::poll_input() {
    hidScanInput();
    m_held = hidKeysHeld(CONTROLLER_P1_AUTO);
    m_pressed = hidKeysDown(CONTROLLER_P1_AUTO);
}

bool App::just_pressed(uint64_t key) {
    return (m_pressed & key) != 0;
}

void App::show_message(const std::string& msg, uint32_t duration) {
    m_message = msg;
    m_message_timer = duration;
}

void App::check_activation_status() {
    if (!m_auth.can_use()) {
        m_state = AppState::ACTIVATE;
        show_message("Free tries exhausted. Please activate.", 300);
    }
}

// ============================================================
// Main Menu
// ============================================================
void App::handle_main_menu() {
    if (just_pressed(HidNpadButton_Up) && m_menu_index > 0) m_menu_index--;
    if (just_pressed(HidNpadButton_Down) && m_menu_index < 3) m_menu_index++;
    if (just_pressed(HidNpadButton_A)) {
        switch (m_menu_index) {
            case 0:
                check_activation_status();
                if (m_state == AppState::MAIN_MENU) {
                    m_state = AppState::SEARCH;
                    m_search_keyword.clear();
                }
                break;
            case 1: m_state = AppState::ACTIVATE; break;
            case 2: m_state = AppState::SETTINGS; break;
            case 3: m_state = AppState::EXIT; break;
        }
    }
}

void App::render_main_menu() {
    m_gui.draw_header("Main Menu");
    const char* items[] = { "Search Games", "Activate", "Settings", "Exit" };
    for (int i = 0; i < 4; i++) {
        int y = 120 + i * 60;
        Color bg = (i == m_menu_index) ? COLOR_ACCENT : Color{40, 40, 55, 255};
        Color tc = (i == m_menu_index) ? COLOR_BG : COLOR_TEXT;
        m_gui.draw_rect(100, y, SCREEN_W - 200, 48, bg);
        m_gui.draw_text(130, y + 14, items[i], tc, 18);
    }
    char status[128];
    if (m_config.activated) {
        snprintf(status, sizeof(status), "Status: ACTIVATED");
    } else {
        snprintf(status, sizeof(status), "Free tries: %d/%d", m_auth.free_tries_remaining(), MAX_FREE_TRIES);
    }
    m_gui.draw_status_bar(status, "");
    m_gui.draw_footer("A: Select  |  +: Exit");
}

// ============================================================
// Search
// ============================================================
void App::handle_search() {
    if (just_pressed(HidNpadButton_A)) {
        m_gui.show_keyboard(m_search_keyword, "Enter game name");
        if (!m_search_keyword.empty()) {
            show_message("Searching...");
            m_search_results = m_api.search_games(m_search_keyword);
            if (m_search_results.empty()) {
                show_message("No results found.", 180);
            } else {
                m_result_index = 0;
                m_state = AppState::SEARCH_RESULTS;
            }
        }
    }
    if (just_pressed(HidNpadButton_B)) m_state = AppState::MAIN_MENU;
}

void App::render_search() {
    m_gui.draw_header("Search Games");
    m_gui.draw_rect(80, 100, SCREEN_W - 160, 50, {40, 40, 55, 255});
    m_gui.draw_rect(80, 100, SCREEN_W - 160, 2, COLOR_ACCENT);
    if (m_search_keyword.empty()) {
        m_gui.draw_text(100, 118, "Press A to open keyboard...", COLOR_TEXT_DIM, 16);
    } else {
        m_gui.draw_text(100, 118, m_search_keyword, COLOR_TEXT, 18);
    }
    m_gui.draw_footer("A: Input  |  B: Back");
}

// ============================================================
// Search Results
// ============================================================
void App::handle_search_results() {
    int count = static_cast<int>(m_search_results.size());
    if (just_pressed(HidNpadButton_Up) && m_result_index > 0) m_result_index--;
    if (just_pressed(HidNpadButton_Down) && m_result_index < count - 1) m_result_index++;
    if (just_pressed(HidNpadButton_A)) {
        m_current_source_url = m_search_results[m_result_index].source_url;
        show_message("Loading details...");
        m_current_detail = m_api.get_game_detail(m_current_source_url);
        m_state = AppState::GAME_DETAIL;
    }
    if (just_pressed(HidNpadButton_B)) m_state = AppState::SEARCH;
}

void App::render_search_results() {
    m_gui.draw_header("Results: " + m_search_keyword);
    int start = 0;
    if (m_result_index > 8) start = m_result_index - 8;
    for (int i = start; i < static_cast<int>(m_search_results.size()) && i < start + 9; i++) {
        int y = 80 + (i - start) * 56;
        Color bg = (i == m_result_index) ? Color{50, 80, 120, 255} : Color{35, 35, 48, 255};
        m_gui.draw_rect(60, y, SCREEN_W - 120, 48, bg);
        m_gui.draw_text(80, y + 6, m_search_results[i].title, COLOR_TEXT, 16);
        if (!m_search_results[i].version.empty())
            m_gui.draw_text(80, y + 26, "v" + m_search_results[i].version, COLOR_TEXT_DIM, 12);
    }
    char hint[64];
    snprintf(hint, sizeof(hint), "%d/%d", m_result_index + 1, static_cast<int>(m_search_results.size()));
    m_gui.draw_footer("A: Select  |  B: Back");
    m_gui.draw_status_bar(m_search_results[m_result_index].title, hint);
}

// ============================================================
// Game Detail
// ============================================================
void App::handle_game_detail() {
    if (just_pressed(HidNpadButton_A)) {
        if (!m_auth.can_use()) { m_state = AppState::ACTIVATE; show_message("Please activate."); return; }
        if (!m_auth.use_free_try() && !m_auth.is_activated()) { m_state = AppState::ACTIVATE; show_message("Free tries exhausted."); return; }
        m_task_id = m_api.start_install(m_current_source_url);
        if (m_task_id.empty()) { show_message("Failed to start install.", 240); }
        else {
            m_install_progress = {};
            m_installing = true;
            m_state = AppState::INSTALLING;
            std::thread([this]() {
                m_api.listen_install_sse(m_task_id, [this](const InstallProgress& p) -> bool {
                    std::lock_guard<std::mutex> lock(m_progress_mutex);
                    m_install_progress = p;
                    if (p.done) { m_installing = false; return false; }
                    return true;
                });
            }).detach();
        }
    }
    if (just_pressed(HidNpadButton_B)) m_state = AppState::SEARCH_RESULTS;
}

void App::render_game_detail() {
    m_gui.draw_header("Game Detail");
    m_gui.draw_rect(60, 80, SCREEN_W - 120, 300, {30, 30, 45, 255});
    int y = 100;
    auto& d = m_current_detail;
    m_gui.draw_text(80, y, d.title.empty() ? "Unknown Title" : d.title, COLOR_TITLE, 20);
    y += 40;
    auto draw_link = [&](const char* label, const std::string& url) {
        if (!url.empty()) m_gui.draw_text(80, y, std::string(label) + ": Available", COLOR_SUCCESS, 14);
        else m_gui.draw_text(80, y, std::string(label) + ": N/A", COLOR_TEXT_DIM, 14);
        y += 28;
    };
    draw_link("Main", d.body_url);
    draw_link("Update", d.update_url);
    draw_link("DLC", d.dlc_url);
    draw_link("Cheat", d.cheat_url);
    m_gui.draw_footer("A: Install  |  B: Back");
}

// ============================================================
// Installing
// ============================================================
void App::handle_installing() {
    if (just_pressed(HidNpadButton_B) && m_install_progress.done) m_state = AppState::MAIN_MENU;
    if (!m_installing && m_install_progress.done) {
        if (m_install_progress.stage == "completed") {
            show_message("Install completed!", 300);
            notify("Youyuzz Install", "Game install completed successfully!");
        } else if (m_install_progress.stage == "failed") {
            show_message("Failed: " + m_install_progress.error, 300);
            notify("Youyuzz Install Failed", "Error: " + m_install_progress.error);
        }
    }
}

void App::render_installing() {
    m_gui.draw_header("Installing...");
    InstallProgress p;
    { std::lock_guard<std::mutex> lock(m_progress_mutex); p = m_install_progress; }
    int y = 120;
    char buf[128];
    snprintf(buf, sizeof(buf), "Stage: %s", p.stage.c_str());
    m_gui.draw_text(100, y, buf, COLOR_TEXT, 16);
    y += 40;
    m_gui.draw_progress_bar(100, y, SCREEN_W - 200, 30, p.percent / 100.f, COLOR_PROGRESS, COLOR_BAR_BG);
    y += 40;
    snprintf(buf, sizeof(buf), "%.1f%%", p.percent);
    m_gui.draw_text(100, y, buf, COLOR_ACCENT, 20);
    y += 35;
    if (!p.current_file.empty()) { m_gui.draw_text(100, y, "File: " + p.current_file, COLOR_TEXT_DIM, 14); y += 25; }
    if (!p.speed.empty()) { snprintf(buf, sizeof(buf), "Speed: %s", p.speed.c_str()); m_gui.draw_text(100, y, buf, COLOR_TEXT_DIM, 14); }
    if (!p.eta.empty())   { snprintf(buf, sizeof(buf), "ETA: %s", p.eta.c_str()); m_gui.draw_text(400, y, buf, COLOR_TEXT_DIM, 14); }
    y += 25;
    if (p.total_files > 0) { snprintf(buf, sizeof(buf), "Files: %d/%d", p.completed_files, p.total_files); m_gui.draw_text(100, y, buf, COLOR_TEXT, 14); }
    if (!p.error.empty()) m_gui.draw_text(100, y + 30, "Error: " + p.error, COLOR_ERROR, 14);
    m_gui.draw_footer(p.done ? "B: Back" : "Please wait...");
}

// ============================================================
// Activate
// ============================================================
void App::handle_activate() {
    if (just_pressed(HidNpadButton_A)) {
        std::string code;
        if (m_gui.show_keyboard(code, "Enter activation code (XXXX-XXXX-XXXX)")) {
            show_message("Verifying...");
            std::string result = m_auth.activate(code);
            if (m_auth.is_activated()) { show_message("Activation successful!", 300); m_state = AppState::MAIN_MENU; }
            else show_message("Failed: " + result, 300);
        }
    }
    if (just_pressed(HidNpadButton_B)) m_state = AppState::MAIN_MENU;
}

void App::render_activate() {
    m_gui.draw_header("Activation");
    int y = 120;
    if (m_config.activated) {
        m_gui.draw_text_centered(y, "ACTIVATED", COLOR_SUCCESS, 28);
        y += 50;
        m_gui.draw_text_centered(y, "All features unlocked", COLOR_TEXT, 16);
    } else {
        char buf[64];
        snprintf(buf, sizeof(buf), "Free tries: %d/%d", m_auth.free_tries_remaining(), MAX_FREE_TRIES);
        m_gui.draw_text_centered(y, buf, COLOR_TEXT, 18);
        y += 50;
        m_gui.draw_text_centered(y, "Press A to enter code", COLOR_ACCENT, 16);
        y += 30;
        m_gui.draw_text_centered(y, "Format: XXXX-XXXX-XXXX", COLOR_TEXT_DIM, 14);
    }
    m_gui.draw_footer("A: Enter code  |  B: Back");
}

// ============================================================
// Settings
// ============================================================
void App::handle_settings() {
    static int settings_idx = 0;
    if (just_pressed(HidNpadButton_Up) && settings_idx > 0) settings_idx--;
    if (just_pressed(HidNpadButton_Down) && settings_idx < 2) settings_idx++;
    if (just_pressed(HidNpadButton_A)) {
        switch (settings_idx) {
            case 0: {
                std::string ip = m_config.pc_ip;
                if (m_gui.show_keyboard(ip, "Enter PC IP")) {
                    m_config.pc_ip = ip;
                    m_config.save();
                    m_api.set_pc_endpoint(m_config.pc_ip, m_config.pc_port);
                    show_message("PC IP: " + ip);
                }
                break;
            }
            case 1: {
                std::string key = m_config.pushdeer_key;
                if (m_gui.show_keyboard(key, "Enter PushDeer Key")) {
                    m_config.pushdeer_key = key;
                    m_config.save();
                    m_pushdeer.set_key(key);
                    show_message("PushDeer Key updated.");
                }
                break;
            }
            case 2: m_state = AppState::MAIN_MENU; break;
        }
    }
    if (just_pressed(HidNpadButton_B)) m_state = AppState::MAIN_MENU;
}

void App::render_settings() {
    m_gui.draw_header("Settings");
    int y = 100;
    m_gui.draw_rect(80, y, SCREEN_W - 160, 48, {40, 40, 55, 255});
    m_gui.draw_text(100, y + 6, "PC Server IP", COLOR_TEXT, 16);
    m_gui.draw_text(100, y + 26, m_config.pc_ip + ":" + std::to_string(m_config.pc_port), COLOR_ACCENT, 14);
    y += 60;
    m_gui.draw_rect(80, y, SCREEN_W - 160, 48, {40, 40, 55, 255});
    m_gui.draw_text(100, y + 6, "PushDeer Key", COLOR_TEXT, 16);
    m_gui.draw_text(100, y + 26, m_config.pushdeer_key.empty() ? "(not set)" : "Configured", COLOR_ACCENT, 14);
    y += 60;
    m_gui.draw_rect(80, y, SCREEN_W - 160, 48, {40, 40, 55, 255});
    m_gui.draw_text(100, y + 14, "Back", COLOR_TEXT, 16);
    m_gui.draw_footer("A: Edit  |  B: Back");
}

} // namespace youyuzz