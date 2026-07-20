from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ICON_DIR = Path(__file__).parent / "static" / "icons"
ICON_DIR.mkdir(parents=True, exist_ok=True)

SIZE = 64
BG = (246, 244, 255, 255)
PURPLE = (86, 59, 207, 255)
PURPLE_2 = (126, 104, 232, 255)
INK = (58, 54, 92, 255)
WHITE = (255, 255, 255, 255)


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((2, 2, SIZE - 2, SIZE - 2), fill=BG)
    return image, draw


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def centered_text(draw: ImageDraw.ImageDraw, text: str, size: int, y_offset: int = 0) -> None:
    text_font = font(size)
    box = draw.textbbox((0, 0), text, font=text_font)
    x = (SIZE - (box[2] - box[0])) / 2
    y = (SIZE - (box[3] - box[1])) / 2 - box[1] + y_offset
    draw.text((x, y), text, font=text_font, fill=PURPLE)


def save_icon(image: Image.Image, filename: str) -> None:
    image.save(
        ICON_DIR / filename,
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)],
    )


def air() -> Image.Image:
    image, draw = canvas()
    for y in (20, 31, 42):
        draw.arc((12, y - 10, 46, y + 10), start=190, end=355, fill=PURPLE, width=4)
        draw.line((12, y, 42, y), fill=PURPLE, width=4)
    return image


def internet() -> Image.Image:
    image, draw = canvas()
    for box in ((12, 17, 52, 57), (20, 29, 44, 57), (28, 41, 36, 57)):
        draw.arc(box, start=205, end=335, fill=PURPLE, width=5)
    draw.ellipse((28, 47, 36, 55), fill=PURPLE)
    return image


def gym() -> Image.Image:
    image, draw = canvas()
    draw.rounded_rectangle((8, 25, 16, 39), radius=3, fill=PURPLE)
    draw.rounded_rectangle((48, 25, 56, 39), radius=3, fill=PURPLE)
    draw.rounded_rectangle((18, 21, 24, 43), radius=3, fill=PURPLE_2)
    draw.rounded_rectangle((40, 21, 46, 43), radius=3, fill=PURPLE_2)
    draw.rounded_rectangle((24, 29, 40, 35), radius=3, fill=INK)
    return image


def pool() -> Image.Image:
    image, draw = canvas()
    for y in (24, 34, 44):
        points = []
        for x in range(10, 55, 4):
            points.append((x, y + (3 if (x // 4) % 2 else -3)))
        draw.line(points, fill=PURPLE, width=4, joint="curve")
    return image


def parking() -> Image.Image:
    image, draw = canvas()
    centered_text(draw, "P", 36, -1)
    return image


def pet() -> Image.Image:
    image, draw = canvas()
    for box in ((13, 17, 23, 27), (27, 11, 37, 21), (41, 17, 51, 27), (44, 31, 54, 41)):
        draw.ellipse(box, fill=PURPLE)
    draw.ellipse((20, 31, 44, 54), fill=PURPLE)
    return image


def laundry() -> Image.Image:
    image, draw = canvas()
    draw.rounded_rectangle((17, 10, 47, 54), radius=5, outline=PURPLE, width=4)
    draw.line((17, 21, 47, 21), fill=PURPLE, width=4)
    draw.ellipse((23, 28, 41, 46), outline=PURPLE, width=4)
    draw.ellipse((38, 14, 43, 19), fill=PURPLE)
    return image


def dishwasher() -> Image.Image:
    image, draw = canvas()
    draw.rounded_rectangle((16, 12, 48, 52), radius=4, outline=PURPLE, width=4)
    draw.line((16, 24, 48, 24), fill=PURPLE, width=4)
    draw.rounded_rectangle((24, 33, 40, 43), radius=2, outline=PURPLE, width=3)
    draw.ellipse((38, 17, 42, 21), fill=PURPLE)
    return image


def storage() -> Image.Image:
    image, draw = canvas()
    draw.rounded_rectangle((15, 20, 49, 48), radius=4, fill=PURPLE)
    draw.polygon([(15, 20), (24, 11), (58, 11), (49, 20)], fill=PURPLE_2)
    draw.polygon([(49, 20), (58, 11), (58, 39), (49, 48)], fill=INK)
    draw.line((22, 30, 42, 30), fill=WHITE, width=3)
    draw.line((22, 39, 42, 39), fill=WHITE, width=3)
    return image


def clubhouse() -> Image.Image:
    image, draw = canvas()
    draw.polygon([(10, 28), (32, 12), (54, 28)], fill=PURPLE)
    draw.rounded_rectangle((15, 28, 49, 52), radius=3, fill=PURPLE_2)
    draw.rectangle((27, 37, 37, 52), fill=WHITE)
    draw.ellipse((22, 32, 28, 38), fill=WHITE)
    draw.ellipse((36, 32, 42, 38), fill=WHITE)
    return image


def patio() -> Image.Image:
    image, draw = canvas()
    draw.arc((13, 10, 51, 48), start=200, end=340, fill=PURPLE, width=5)
    draw.line((32, 28, 32, 54), fill=PURPLE, width=4)
    draw.line((20, 54, 44, 54), fill=PURPLE, width=4)
    for x in (22, 32, 42):
        draw.line((32, 28, x, 18), fill=PURPLE_2, width=3)
    return image


ICONS = {
    "air.ico": air,
    "internet.ico": internet,
    "gym.ico": gym,
    "pool.ico": pool,
    "parking.ico": parking,
    "pet.ico": pet,
    "laundry.ico": laundry,
    "dishwasher.ico": dishwasher,
    "storage.ico": storage,
    "clubhouse.ico": clubhouse,
    "patio.ico": patio,
}


def main() -> None:
    for filename, draw_icon in ICONS.items():
        save_icon(draw_icon(), filename)
    print(f"Generated {len(ICONS)} icons in {ICON_DIR}")


if __name__ == "__main__":
    main()
