"""演示封面：本地 SVG data URI，避免请求 picsum 等远程图床。"""
from urllib.parse import quote


def local_cover_uri(kind: str, seed: int) -> str:
    """生成纯色占位封面（不访问网络）。"""
    hue = (seed * 37) % 360
    label = f"{kind}{seed}"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="300">'
        f'<rect width="100%" height="100%" fill="hsl({hue},42%,52%)"/>'
        f'<text x="50%" y="50%" fill="#fff" font-size="22" text-anchor="middle" '
        f'dominant-baseline="middle" font-family="sans-serif">{label}</text>'
        f"</svg>"
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg)
