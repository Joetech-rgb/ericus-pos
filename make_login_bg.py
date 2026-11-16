from PIL import Image

src = r'static\img\Modern Supermarket Fresh Produce Aisle.png'
dst = r'static\img\login_bg.jpg'

im = Image.open(src).convert('RGB')
if im.width > 1920:
    resample = getattr(Image, 'Resampling', Image).LANCZOS
    im = im.resize((1920, int(im.height * 1920 / im.width)), resample)
im.save(dst, 'JPEG', quality=82, optimize=True)
print('Saved login_bg.jpg:', im.size[0], 'x', im.size[1])
