from urllib.parse import quote


def format_level(level: float) -> str:
    return str(level).replace(".0", "").replace(".5", "+")


def yt_search_link(title: str, difficulty: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote(
        f"CHUNITHM {title} {difficulty}"
    )


def sdvxin_link(id: str, difficulty: str) -> str:
    if "ULT" not in difficulty and "WE" not in difficulty:
        if difficulty == "MAS":
            difficulty = "MST"
        elif difficulty == "BAS":
            difficulty = "BSC"
        return f"https://sdvx.in/chunithm/{id[:2]}/{id}{difficulty.lower()}.htm"
    else:
        difficulty = difficulty.replace("WE", "end")
        return f"https://sdvx.in/chunithm/{difficulty.lower()[:3]}/{id}{difficulty.lower()}.htm"
