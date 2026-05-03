import pytest

pytest.importorskip("PIL")

_ONE_BY_ONE_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/P8K7WQAAAABJRU5ErkJggg=="
)


def _png_data_uri() -> str:
    return f"data:image/png;base64,{_ONE_BY_ONE_PNG_BASE64}"


@pytest.mark.asyncio
async def test_results_card_endpoint_returns_png(client):
    img = _png_data_uri()
    payload = {
        "edition": "anime",
        "mode": "blind",
        "keep_images": [img, img, img, img],
        "cut_images": [img, img, img, img],
        "width": 900,
    }
    r = await client.post("/images/results-card", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"

