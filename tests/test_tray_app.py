from sentineltray.tray_app import _build_image


def test_build_image_dimensions() -> None:
    image = _build_image()
    assert image.size == (64, 64)
    assert image.mode == "RGB"
    assert image.getpixel((32, 32)) == (0, 166, 81)
