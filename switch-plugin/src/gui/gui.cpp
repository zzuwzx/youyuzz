#include "gui/gui.h"
#include <cstdio>
#include <cstring>
#include <switch.h>

namespace youyuzz {

Gui::Gui() {}
Gui::~Gui() { exit(); }

bool Gui::init() {
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK) < 0) {
        printf("SDL_Init failed: %s\n", SDL_GetError());
        return false;
    }
    m_window = SDL_CreateWindow("Youyuzz", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                                 SCREEN_W, SCREEN_H, SDL_WINDOW_SHOWN);
    if (!m_window) {
        printf("SDL_CreateWindow failed: %s\n", SDL_GetError());
        return false;
    }
    m_renderer = SDL_CreateRenderer(m_window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!m_renderer) {
        printf("SDL_CreateRenderer failed: %s\n", SDL_GetError());
        return false;
    }
    m_initialized = true;
    return true;
}

void Gui::exit() {
    if (m_renderer) { SDL_DestroyRenderer(m_renderer); m_renderer = nullptr; }
    if (m_window)   { SDL_DestroyWindow(m_window); m_window = nullptr; }
    if (m_initialized) { SDL_Quit(); m_initialized = false; }
}

void Gui::begin_frame() {
    SDL_SetRenderDrawColor(m_renderer, COLOR_BG.r, COLOR_BG.g, COLOR_BG.b, COLOR_BG.a);
    SDL_RenderClear(m_renderer);
}

void Gui::end_frame() {
    SDL_RenderPresent(m_renderer);
}

void Gui::draw_rect(int x, int y, int w, int h, Color c) {
    SDL_SetRenderDrawColor(m_renderer, c.r, c.g, c.b, c.a);
    SDL_Rect rect = {x, y, w, h};
    SDL_RenderFillRect(m_renderer, &rect);
}

void Gui::draw_text(int x, int y, const std::string& text, Color c, int font_size) {
    (void)font_size;
    SDL_SetRenderDrawColor(m_renderer, c.r, c.g, c.b, c.a);
    int cx = x;
    for (size_t i = 0; i < text.size(); i++) {
        uint8_t ch = static_cast<uint8_t>(text[i]);
        if (ch < 0x20) continue;
        for (int row = 0; row < 8; row++) {
            uint8_t bits = ((ch * 7 + row * 13) & 0xFF);
            for (int col = 0; col < 8; col++) {
                if (bits & (0x80 >> col)) {
                    SDL_RenderDrawPoint(m_renderer, cx + col, y + row);
                }
            }
        }
        cx += 10;
    }
}

void Gui::draw_text_centered(int y, const std::string& text, Color c, int font_size) {
    int w = static_cast<int>(text.size()) * 10;
    draw_text((SCREEN_W - w) / 2, y, text, c, font_size);
}

void Gui::draw_progress_bar(int x, int y, int w, int h, float progress, Color fg, Color bg) {
    draw_rect(x, y, w, h, bg);
    int fill_w = static_cast<int>(w * progress);
    if (fill_w > 0) draw_rect(x, y, fill_w, h, fg);
}

int Gui::text_width(const std::string& text, int font_size) {
    (void)font_size;
    return static_cast<int>(text.size()) * 10;
}

bool Gui::show_keyboard(std::string& inout_text, const std::string& title) {
    SwkbdConfig kbd;
    if (R_FAILED(swkbdCreate(&kbd, 0))) return false;
    swkbdConfigMakePresetDefault(&kbd);
    if (!title.empty()) {
        char t[64];
        snprintf(t, sizeof(t), "%s", title.c_str());
        swkbdConfigSetGuideText(&kbd, t);
    }
    if (!inout_text.empty()) {
        swkbdConfigSetInitialText(&kbd, inout_text.c_str());
    }
    char out[256] = {0};
    swkbdShow(&kbd, out, sizeof(out));
    swkbdClose(&kbd);
    if (strlen(out) > 0) {
        inout_text = out;
        return true;
    }
    return false;
}

void Gui::draw_header(const std::string& title) {
    draw_rect(0, 0, SCREEN_W, 60, {30, 30, 50, 255});
    draw_rect(0, 58, SCREEN_W, 2, COLOR_ACCENT);
    draw_text(30, 18, title, COLOR_TITLE, 24);
    draw_text(SCREEN_W - 150, 22, "Youyuzz", COLOR_TEXT_DIM, 16);
}

void Gui::draw_footer(const std::string& hint) {
    draw_rect(0, SCREEN_H - 44, SCREEN_W, 44, {25, 25, 40, 255});
    draw_rect(0, SCREEN_H - 44, SCREEN_W, 2, COLOR_ACCENT);
    draw_text(30, SCREEN_H - 32, hint, COLOR_TEXT_DIM, 14);
}

void Gui::draw_status_bar(const std::string& left, const std::string& right) {
    draw_text(30, SCREEN_H - 75, left, COLOR_TEXT, 14);
    int rw = text_width(right, 14);
    draw_text(SCREEN_W - rw - 30, SCREEN_H - 75, right, COLOR_TEXT_DIM, 14);
}

} // namespace youyuzz