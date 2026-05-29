#pragma once
#include "youyuzz_common.h"
#include <SDL2/SDL.h>
#include <string>

namespace youyuzz {

class Gui {
public:
    Gui();
    ~Gui();

    bool init();
    void exit();

    void begin_frame();
    void end_frame();

    void draw_rect(int x, int y, int w, int h, Color c);
    void draw_text(int x, int y, const std::string& text, Color c, int font_size = 20);
    void draw_text_centered(int y, const std::string& text, Color c, int font_size = 20);
    void draw_progress_bar(int x, int y, int w, int h, float progress, Color fg, Color bg);

    int  text_width(const std::string& text, int font_size = 20);
    bool show_keyboard(std::string& inout_text, const std::string& title = "Input");

    void draw_header(const std::string& title);
    void draw_footer(const std::string& hint);
    void draw_status_bar(const std::string& left, const std::string& right);

    SDL_Renderer* renderer() { return m_renderer; }

private:
    SDL_Window*   m_window   = nullptr;
    SDL_Renderer* m_renderer = nullptr;
    bool          m_initialized = false;
};

} // namespace youyuzz