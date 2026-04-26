import re


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("￾", "-")

    # fix hyphen line breaks
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    # join broken lines
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # normalize spacing
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)

    return text.strip()


def remove_noise(text: str) -> str:
    if not text:
        return ""

    # remove URLs
    text = re.sub(r"http\S+|www\.\S+", "", text)

    # remove citations like (Smith et al., 2020)
    text = re.sub(r"\([^)]*et al\.,?\s*\d{4}[^)]*\)", "", text)

    # remove numeric citations
    text = re.sub(r"(,\s*\d{2,5})+", "", text)
    text = re.sub(r"\b\d{3,5}\b", "", text)

    # remove percentage clutter
    text = re.sub(r"\b\d+%\s*<?\d*%?\b", "", text)

    # remove (n=)
    text = re.sub(r"\(n=\)", "", text)

    # remove trailing citations like ".53"
    text = re.sub(r"\.\d+\b", ".", text)

    # fix broken "In ,"
    text = re.sub(r"\bIn\s*,", "", text)

    # remove standalone page numbers
    text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)

    # remove placeholders
    text = re.sub(r"\(\s*(page|figure|stage)?\s*\)", "", text, flags=re.IGNORECASE)

    # remove headers/footers
    text = re.sub(
        r"^.{5,80}\|\s*(page\s*)?\d+\s*$",
        "",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    return text.strip()


def normalize_lists(text: str) -> str:
    text = re.sub(r"\s*•\s*", "\n• ", text)
    return text.strip()


def clean_element_text(text: str) -> str:
    text = normalize_text(text)
    text = remove_noise(text)
    text = normalize_lists(text)
    return text.strip()


def is_valid_title(text: str) -> bool:
    text = text.strip()

    if len(text) < 5:
        return False
    if text.endswith("."):
        return False
    if text[0].islower():
        return False
    if len(text.split()) > 12:
        return False

    return True


def fix_structure(elements):
    fixed = []

    for el in elements:
        text = clean_element_text(el.text or "")
        el_type = el.category

        if not text:
            continue

        if el_type == "Title" and not is_valid_title(text):
            el_type = "NarrativeText"

        fixed.append({"type": el_type, "text": text})

    return fixed


def merge_fragments(elements):
    merged = []
    i = 0

    while i < len(elements):
        current = elements[i]

        if i + 1 < len(elements):
            next_el = elements[i + 1]

            if current["type"] == next_el["type"]:
                if (
                    not current["text"].endswith((".", ":", "?", "!"))
                    and next_el["text"][0].islower()
                ):
                    merged.append({
                        "type": current["type"],
                        "text": current["text"] + " " + next_el["text"]
                    })
                    i += 2
                    continue

        merged.append(current)
        i += 1

    return merged


def clean_elements(elements):
    cleaned = fix_structure(elements)
    cleaned = merge_fragments(cleaned)
    return cleaned


if __name__ == "__main__":
    import sys
    from extract import extract_pdf_elements
    path = sys.argv[1] if len(sys.argv) > 1 else input("PDF path: ").strip()
    raw = extract_pdf_elements(path)
    cleaned = clean_elements(raw)
    print(f"Cleaned: {len(cleaned)} elements")
    for el in cleaned[:5]:
        print(f"\n[{el['type']}] {el['text'][:120]}")