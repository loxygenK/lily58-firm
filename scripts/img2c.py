#!/bin/env python
import os
import textwrap


SCRIPT_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, "../", "assets"))


class MonotoneBitmapImage:
    def __init__(self, width, height, pixels):
        self.width = width
        self.height = height
        self.pixels = pixels

    @staticmethod
    def load_from(filename):
        def load_bytes(stream, *lens):
            for len in lens:
                yield int.from_bytes(stream.read(len), "little")

        with open(filename, mode="br") as f:
            magic, filesize, _, offset = list(load_bytes(f, 2, 4, 4, 4))

            head, width, height, _, bits, compression, \
                image_size_b, xppm, yppm, \
                _, _ = list(load_bytes(f, 4, 4, 4, 2, 2, 4, 4, 4, 4, 4, 4))
            # skip to the Image
            _ = f.seek(offset)

            row = [False] * width
            pixels = [[]] * height
            x = 0
            y = 0
            while f.tell() < filesize:
                pixel = f.read(bits // 8)

                r = pixel[0]
                g = pixel[1]
                b = pixel[2]

                row[x] = (r != 0 and g != 0 and b != 0)

                x += 1
                if x == width:
                    pixels[height - y - 1] = row
                    row = [False] * width
                    x = 0
                    y += 1

        return MonotoneBitmapImage(width, height, pixels)


def pixels_to_qmk_matrix(image):
    def bools_to_binary(bools):
        binary = 0
        for b in range(len(bools) - 1, -1, -1):
            binary += (1 if bools[b] else 0) << (b)

        return binary

    if image.width % 6 != 0:
        raise Exception(
            "Image width must be dividable by 6 " +
            f"(width = {image.width}, maybe round it to {(image.width // 6 + 1) * 6}?)"
        )

    if image.height % 8 != 0:
        raise Exception(
            "Image height must be dividable by 8 " +
            f"(height = {image.height}, maybe round it to {(image.height // 8 + 8) * 6}?)"
        )

    matrix = []
    for row in range(0, image.height, 8):
        for col in range(0, image.width, 6):
            for x in range(6):
                pixels_row = []
                for y in range(8):
                    pixels_row.append(image.pixels[row + y][col + x])
                matrix.append(bools_to_binary(pixels_row))

    return matrix


def pixels_to_bytes(image):
    def bools_to_binary(bools):
        binary = 0
        for i, b in enumerate(bools):
            binary += (1 if b else 0) << i

        return binary

    if image.width % 8 != 0:
        raise Exception(
            "Image width must be dividable by 8 " +
            f"(width = {image.width}, maybe round it to {(image.width // 8 + 1) * 8}?)"
        )

    matrix = []
    for row in range(image.height):
        for col in range(0, image.width, 8):
            pixels_row = []
            for x in range(8):
                pixels_row.append(image.pixels[row][col + x])
            matrix.append(bools_to_binary(pixels_row))

    return matrix


def export_qmk_matrix_to_c(var_meta, qmk_mat):
    c_sources = var_meta + " = {\n    "
    for i, mat in enumerate(qmk_mat):
        c_sources += f"{hex(mat)}, "
        if i % 6 == 5:
            c_sources += "\n    "
    c_sources += "\n};"

    return c_sources


def write_to_file(filename, string):
    with open(filename, mode="w") as f:
        f.write(string)


print("--> Generating fonts")

image = MonotoneBitmapImage.load_from(os.path.join(ASSETS_DIR, "font.bmp"))
fonts = pixels_to_qmk_matrix(image)
write_to_file(os.path.join(ASSETS_DIR, "font.c"), f'''
#include "progmem.h"

{export_qmk_matrix_to_c("const unsigned char font[] PROGMEM", fonts)}
'''.strip())

header = ""
image_data_sources = ""
for file in os.listdir(os.path.join(ASSETS_DIR, "images")):
    image_id = os.path.splitext(file)[0]
    image = MonotoneBitmapImage.load_from(os.path.join(ASSETS_DIR, f"images/{file}"))

    print(f"--> Generating images ({file} {image.width}x{image.height})")

    mat = pixels_to_bytes(image)
    header += f"void render_{image_id.lower()}(int ox, int oy);\n"
    image_data_sources += f'''
void render_{image_id.lower()}(int ox, int oy) {{
{textwrap.indent(export_qmk_matrix_to_c(f"static const char matrix[]", mat), " " * 4)}

    render_pixels(ox, oy, {image.width}, {image.height}, matrix, {len(mat)});
}}'''

write_to_file(os.path.join(ASSETS_DIR, "images.h"), f'''
#ifndef F4N_IMAGE_H

{header}
#endif // F4N_IMAGE_H
'''.strip())
write_to_file(os.path.join(ASSETS_DIR, "images.c"), f'''
#include QMK_KEYBOARD_H
#include "progmem.h"
#include "./images.h"

void render_pixels(int ox, int oy, int width, int height, const char mat[], size_t len) {{
    int x = 0, y = 0;
    for(int i = 0; i < len; i++) {{
        for(int b = 0; b < 8; b++) {{
            oled_write_pixel(ox + x, oy + y, mat[i] & (1 << b));
            ++x;

            if(x >= width) {{
                x = 0; ++y;
            }}
        }}
    }}
}}

{image_data_sources}
'''.strip())


# Export normal font
