import re
import unicodedata


def clean_description(text: str) -> str:
    if not text:
        return text

    # 1. Replace non-breaking spaces before NFKC (unreliable for \xa0)
    text = text.replace("\xa0", " ")

    # 2. NFKC normalization: curly quotes, em-dashes, bullet chars → ASCII equivalents
    text = unicodedata.normalize("NFKC", text)

    # 3. Unescape LinkedIn markdown backslash escapes (e.g. \- \& \# \*)
    text = re.sub(r"\\([^\n])", r"\1", text)

    # 4. Strip bold/italic markers, then orphaned asterisks
    text = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", text)
    text = re.sub(r"\*+", "", text)

    # 5. Whitespace normalization
    text = re.sub(r"[ \t]+", " ", text)          # multiple spaces/tabs → one space
    text = re.sub(r"\n{3,}", "\n\n", text)        # 3+ newlines → 2
    text = text.strip()

    return text
