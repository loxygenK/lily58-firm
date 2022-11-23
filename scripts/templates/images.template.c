#include QMK_KEYBOARD_H
#include "progmem.h"
#include "./images.h"

void render_pixels(int ox, int oy, int width, int height, const char mat[], size_t len) {
    int x = 0, y = 0;
    for(int i = 0; i < len; i++) {
        for(int b = 0; b < 8; b++) {
            oled_write_pixel(ox + x, oy + y, mat[i] & (1 << b));
            ++x;

            if(x >= width) {
                x = 0; ++y;
            }
        }
    }
}

{-image-data-}
