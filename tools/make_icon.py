"""生成项目图标 assets/app.ico（纯标准库实现，无第三方依赖）。

图形：圆角紫色渐变方块 + 白色柱状图与基线，呼应“业绩统计”主题。
运行： .venv\\Scripts\\python.exe tools\\make_icon.py
"""
import os
import struct

SIZE = 64
MARGIN = 1
RADIUS = 13
TOP_COLOR = (124, 92, 255)      # #7C5CFF
BOTTOM_COLOR = (74, 47, 208)    # #4A2FD0

BARS = (
    (13, 19, 36),
    (26, 32, 29),
    (39, 45, 22),
)
BASELINE = (11, 53, 48)          # x1, x2, y（含）
BASELINE_HEIGHT = 3


def in_round_rect(x, y):
    left, top = MARGIN, MARGIN
    right, bottom = SIZE - MARGIN, SIZE - MARGIN
    if x < left or x >= right or y < top or y >= bottom:
        return False
    cx = min(max(x + 0.5, left + RADIUS), right - RADIUS)
    cy = min(max(y + 0.5, top + RADIUS), bottom - RADIUS)
    dx = x + 0.5 - cx
    dy = y + 0.5 - cy
    return dx * dx + dy * dy <= RADIUS * RADIUS


def background(y):
    span = SIZE - 2 * MARGIN - 1
    ratio = (y - MARGIN) / float(span)
    return tuple(
        int(round(TOP_COLOR[i] + (BOTTOM_COLOR[i] - TOP_COLOR[i]) * ratio))
        for i in range(3)
    )


def is_foreground(x, y):
    x1, x2, y_base = BASELINE
    if x1 <= x <= x2 and y_base <= y < y_base + BASELINE_HEIGHT:
        return True
    for bx1, bx2, by in BARS:
        if bx1 <= x <= bx2 and by <= y < BASELINE[2]:
            return True
    return False


def build_icon():
    xor = bytearray()
    for y in range(SIZE - 1, -1, -1):
        for x in range(SIZE):
            if not in_round_rect(x, y):
                xor += b'\x00\x00\x00\x00'
                continue
            if is_foreground(x, y):
                red = green = blue = 255
            else:
                red, green, blue = background(y)
            xor += bytes((blue, green, red, 255))

    mask_row = ((SIZE + 31) // 32) * 4
    and_mask = b'\x00' * (mask_row * SIZE)

    header = struct.pack(
        '<IiiHHIIiiII',
        40, SIZE, SIZE * 2, 1, 32, 0, len(xor), 0, 0, 0, 0,
    )
    image = header + bytes(xor) + and_mask

    icon_header = struct.pack('<HHH', 0, 1, 1)
    entry = struct.pack('<BBBBHHII', SIZE, SIZE, 0, 0, 1, 32, len(image), 22)
    return icon_header + entry + image


def main():
    target_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, 'app.ico')
    with open(target, 'wb') as handle:
        handle.write(build_icon())
    print('ICON_OK %s %d bytes' % (target, os.path.getsize(target)))


if __name__ == '__main__':
    main()