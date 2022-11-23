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


def bytes_to_c_array(qmk_mat, wrap):
    c_sources = "{\n    "
    for i, mat in enumerate(qmk_mat):
        c_sources += f"{hex(mat)}, "
        if i % wrap == (wrap - 1):
            c_sources += "\n    "
    c_sources += "\n};"

    return c_sources


def hydrate_template(template, argument):
    basename, ext = template.rsplit(".", 2)
    with open(os.path.join(SCRIPT_DIR, "templates", f"{basename}.template.{ext}"), mode="r") as f:
        template_body = "".join(f.readlines()).strip()

    for k, v in argument.items():
        blacket = f"{{-{k}-}}"
        template_body = template_body.replace(blacket, str(v))

    return template_body


def write_to_file(filename, string):
    with open(filename, mode="w") as f:
        f.write(string)


print("--> Generating fonts")

image = MonotoneBitmapImage.load_from(os.path.join(ASSETS_DIR, "font.bmp"))
fonts = pixels_to_qmk_matrix(image)

header = ""
image_data_sources = ""
for file in os.listdir(os.path.join(ASSETS_DIR, "images")):
    image_id = os.path.splitext(file)[0]
    image = MonotoneBitmapImage.load_from(
        os.path.join(ASSETS_DIR, f"images/{file}")
    )

    print(f"--> Generating images ({file} {image.width}x{image.height})")

    mat = pixels_to_bytes(image)
    matdef = bytes_to_c_array(mat, 6).splitlines(True)

    fnsig = hydrate_template("images-fn-sig.c", {"name": image_id})
    header += hydrate_template("images-fn.h", {"signature": fnsig})
    image_data_sources += hydrate_template(
        "images-fn.c", {
            "signature": fnsig,
            "matrix-definition": (
                matdef[0] + textwrap.indent("".join(matdef[1:]), " " * 4)
            ),
            "width": image.width,
            "height": image.height,
            "len": len(mat)
        }
    ) + "\n\n"

write_to_file(
    os.path.join(ASSETS_DIR, "font.c"),
    hydrate_template("font.c", {
        "font-matrix": bytes_to_c_array(fonts, 6)
    })
)
write_to_file(
    os.path.join(ASSETS_DIR, "images.h"),
    hydrate_template("images.h", {
        "header": header
    })
)
write_to_file(
    os.path.join(ASSETS_DIR, "images.c"),
    hydrate_template("images.c", {
        "image-data": image_data_sources
    })
)
