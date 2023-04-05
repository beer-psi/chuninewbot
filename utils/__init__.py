from urllib.parse import quote


def format_level(level: float) -> str:
    return str(level).replace(".0", "").replace(".5", "+")


def yt_search_link(title: str, difficulty: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote(
        f"CHUNITHM {title} {difficulty}"
    )
