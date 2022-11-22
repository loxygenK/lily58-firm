#!/bin/env python
import os


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

    matrix = []
    for row in range(0, image.height, 8):
        for col in range(0, image.width, 6):
            for x in range(6):
                pixels_row = []
                for y in range(8):
                    pixels_row.append(image.pixels[row + y][col + x])
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


# Export normal font
image = MonotoneBitmapImage.load_from("./font.bmp")
pixs = pixels_to_qmk_matrix(image)
write_to_file("font.c", f'''
#include "progmem.h"

{export_qmk_matrix_to_c("const unsigned char font[] PROGMEM", pixs)}
'''.strip())

