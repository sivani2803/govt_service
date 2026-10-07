"""Generate and organize civic issue sample images for CivicPulse.

Creates a cohesive local catalog in assets/civic_samples:
1. Streetlights (hero light, hero dark, inspection defect crop)
2. Water problems (leaking pipe / street flooding / main burst)
3. Waste problems (overflowing bin / sidewalk litter)
4. Road/pothole damage (linked to existing dashcam assets)
"""
from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT_DIR / "assets" / "civic_samples"
ROAD_WATCH_DIR = ROOT_DIR / "assets" / "road_watch"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# 1. Generate streetlight_flicker_inspect.jpg (crop from streetlight_night_dark.jpg)
dark_hero_path = SAMPLES_DIR / "streetlight_night_dark.jpg"
if dark_hero_path.is_file():
    with Image.open(dark_hero_path) as img:
        # Focus on lamp post lantern and upper street view
        # Size is 1600x900
        w, h = img.size
        # Crop around left lamp: box (left, upper, right, lower)
        crop_box = (int(w * 0.12), int(h * 0.04), int(w * 0.44), int(h * 0.65))
        lantern_crop = img.crop(crop_box).resize((800, 450), Image.Resampling.LANCZOS)
        lantern_crop.save(SAMPLES_DIR / "streetlight_flicker_inspect.jpg", "JPEG", quality=90)
        print("Generated streetlight_flicker_inspect.jpg")

# 2. Link/Copy pothole_road_damage.jpg
pothole_src = ROAD_WATCH_DIR / "dashcam_pothole_urban_day.jpg"
if pothole_src.is_file():
    with Image.open(pothole_src) as img:
        img.resize((1280, 720), Image.Resampling.LANCZOS).save(
            SAMPLES_DIR / "pothole_road_damage.jpg", "JPEG", quality=90
        )
        print("Generated pothole_road_damage.jpg")

# 3. Create water_pipe_leak.jpg (realistic municipal water pipe burst / flooded asphalt road)
# Use the wet dusk dashcam image base or create rich water flood visual
wet_src = ROAD_WATCH_DIR / "dashcam_pothole_wet_dusk.jpg"
if wet_src.is_file():
    with Image.open(wet_src) as img:
        # Create a water surge / gushing pipe overlay on wet road
        base = img.resize((1280, 720), Image.Resampling.LANCZOS)
        overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # Gushing water plume & ripples
        center_x, center_y = 640, 420
        for r in range(160, 20, -10):
            alpha = int(40 + (160 - r) * 0.6)
            draw.ellipse(
                (center_x - r * 1.8, center_y - r * 0.5, center_x + r * 1.8, center_y + r * 0.5),
                fill=(180, 220, 255, alpha),
                outline=(220, 245, 255, int(alpha * 1.2)),
                width=2,
            )
        # Water plume splashing
        for i in range(25):
            angle = (i / 25.0) * math.pi
            px = center_x + math.cos(angle) * 70
            py = center_y - math.sin(angle) * 90 - 20
            draw.line([(center_x, center_y), (px, py)], fill=(240, 250, 255, 120), width=3)

        water_merged = Image.alpha_composite(base.convert("RGBA"), overlay)
        water_final = water_merged.convert("RGB").filter(ImageFilter.SMOOTH)
        water_final.save(SAMPLES_DIR / "water_pipe_leak.jpg", "JPEG", quality=90)
        print("Generated water_pipe_leak.jpg")

# 4. Create waste_overflow_bin.jpg (realistic municipal sidewalk trash / dumpster overflow)
# Synthesize high-quality urban street scene with municipal bins and debris
w, h = 1280, 720
waste_img = Image.new("RGB", (w, h), (35, 45, 55))
waste_draw = ImageDraw.Draw(waste_img)

# Sky & urban wall
waste_draw.rectangle([0, 0, w, int(h * 0.45)], fill=(130, 150, 170))
waste_draw.rectangle([0, int(h * 0.35), w, int(h * 0.65)], fill=(80, 90, 100)) # brick wall
for y in range(int(h * 0.35), int(h * 0.65), 18):
    waste_draw.line([(0, y), (w, y)], fill=(65, 75, 85), width=1)

# Sidewalk & asphalt road
waste_draw.polygon([(0, int(h * 0.65)), (w, int(h * 0.65)), (w, int(h * 0.78)), (0, int(h * 0.78))], fill=(140, 145, 150))
waste_draw.line([(0, int(h * 0.78)), (w, int(h * 0.78))], fill=(180, 185, 190), width=4) # curb
waste_draw.rectangle([0, int(h * 0.78), w, h], fill=(45, 50, 55)) # asphalt

# 2 Large Municipal Waste Bins (Green & Blue)
# Left Bin (Green Municipal Dumpster)
bx1, by1, bx2, by2 = 320, 310, 580, 570
waste_draw.rounded_rectangle([bx1, by1, bx2, by2], radius=16, fill=(28, 88, 54), outline=(40, 120, 75), width=3)
waste_draw.rounded_rectangle([bx1 + 15, by1 + 25, bx2 - 15, by2 - 20], radius=8, fill=(22, 70, 43))
# Lid ajar with overflowing bags
waste_draw.polygon([(bx1 - 10, by1 + 10), (bx2 + 10, by1 - 35), (bx2 + 10, by1 - 15), (bx1 - 10, by1 + 25)], fill=(20, 50, 35))

# Right Bin (Blue Recycling Container)
rx1, ry1, rx2, ry2 = 640, 330, 890, 570
waste_draw.rounded_rectangle([rx1, ry1, rx2, ry2], radius=16, fill=(25, 75, 130), outline=(35, 105, 180), width=3)
waste_draw.rounded_rectangle([rx1 + 15, ry1 + 25, rx2 - 15, ry2 - 20], radius=8, fill=(18, 55, 100))

# Overflowing items and bags (white, black, kraft cardboard)
waste_draw.ellipse([bx1 + 40, by1 - 50, bx1 + 150, by1 + 20], fill=(230, 230, 235)) # white bag
waste_draw.ellipse([bx1 + 120, by1 - 65, bx1 + 230, by1 + 10], fill=(35, 35, 40)) # black bag
waste_draw.polygon([(rx1 + 20, ry1 - 40), (rx1 + 120, ry1 - 70), (rx1 + 140, ry1 - 10), (rx1 + 30, ry1 + 15)], fill=(180, 150, 110)) # cardboard box
waste_draw.polygon([(rx1 + 110, ry1 - 45), (rx1 + 210, ry1 - 25), (rx1 + 190, ry1 + 20), (rx1 + 90, ry1 + 10)], fill=(215, 215, 220)) # paper/bag

# Debris on sidewalk & near curb
waste_draw.polygon([(480, 570), (550, 550), (570, 590), (490, 600)], fill=(190, 160, 120)) # fallen carton
waste_draw.ellipse([270, 580, 360, 630], fill=(225, 225, 230)) # plastic bag on curb
waste_draw.ellipse([620, 585, 690, 625], fill=(30, 30, 35)) # trash bag
waste_draw.rectangle([720, 600, 780, 640], fill=(160, 130, 95)) # cardboard debris
waste_draw.ellipse([820, 610, 880, 635], fill=(70, 140, 210)) # plastic cup/container

# Subtle shadow and texture blur
waste_img = waste_img.filter(ImageFilter.GaussianBlur(radius=0.7))
waste_img.save(SAMPLES_DIR / "waste_overflow_bin.jpg", "JPEG", quality=90)
print("Generated waste_overflow_bin.jpg")

print("All civic samples generated successfully in assets/civic_samples!")
