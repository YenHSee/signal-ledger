"""Deterministic company-news relevance checks shared by live and sample contexts."""

NEWS_ALIASES = {
    "AAPL": ("aapl", "apple"),
    "MSFT": ("msft", "microsoft"),
    "NVDA": ("nvda", "nvidia"),
    "GOOGL": ("googl", "alphabet", "google"),
    "AMZN": ("amzn", "amazon"),
    "META": ("meta", "facebook", "instagram", "whatsapp"),
    "TSLA": ("tsla", "tesla"),
    "AMD": ("amd", "advanced micro devices"),
    "JPM": ("jpm", "jpmorgan", "jp morgan"),
    "WMT": ("wmt", "walmart", "sam's club", "sams club"),
}


def headline_matches_ticker(ticker: str, headline: str) -> bool:
    normalized = "".join(
        character if character.isalnum() else " " for character in headline.casefold()
    )
    padded = f" {' '.join(normalized.split())} "
    return any(
        f" {alias.casefold()} " in padded
        for alias in NEWS_ALIASES.get(ticker.upper(), (ticker,))
    )
