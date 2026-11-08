from PIL import Image

img = Image.open(r"C:/Users/Sysx/.gemini/antigravity/brain/04487f19-ac72-4d76-acc2-9297a34021f9/.user_uploaded/media_1793621063380_4d42cd0e.png")
# Crop center bottom (Branch 5 and Branch 3/4)
w, h = img.size
# Crop around cursor
crop1 = img.crop((w * 0.3, h * 0.5, w * 0.7, h * 0.95))
crop1.save(".aulatex-temp/crop_bottom.png")
print("Saved crop_bottom.png")

# Crop left side (Branch 1 and Branch 3)
crop2 = img.crop((w * 0.05, h * 0.2, w * 0.45, h * 0.85))
crop2.save(".aulatex-temp/crop_left.png")
print("Saved crop_left.png")

