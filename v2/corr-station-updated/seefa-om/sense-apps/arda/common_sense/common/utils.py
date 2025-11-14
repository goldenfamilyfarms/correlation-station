import re


def remove_api_key(string: str) -> str:
    """Clean API keys from strings so they don't return in aborts"""
    return re.sub(r"api_key=\S{40}", "api_key=<key>", string)
