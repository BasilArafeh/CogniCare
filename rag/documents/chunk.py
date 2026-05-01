# Hybrid chunker using LangChain
# Keeps sections + uses splitter + avoids cutting sentences
from langchain_text_splitters import RecursiveCharacterTextSplitter


def clean_leading_noise(text):
    lines = text.strip().split("\n")
    if lines and lines[0].lower() in ["document", "section"]:
        return "\n".join(lines[1:]).strip()
    return text

def group_by_sections(elements):
    sections = []
    current_title = ""
    buffer = []

    for el in elements:
        text = (el.get("text") or "").strip()
        if not text:
            continue

        if el.get("type") == "Title":
            if buffer:
                sections.append({
                    "title": current_title,
                    "content": " ".join(buffer)
                })
            current_title = text if text.lower() != "document" else ""
            buffer = []
            continue

        buffer.append(text)

    if buffer:
        sections.append({
            "title": current_title,
            "content": " ".join(buffer)
        })

    return sections


def is_valid_chunk(text):
    words = text.split()

    if len(words) < 40:
        return False
    if len(words) > 400:
        return False
    if not any(c.isalpha() for c in text):
        return False
    if text.strip().startswith(("(", ",", "-")):
        return False
    if text[0].islower():
        return False

    return True


def clean_chunk_boundaries(text):
    text = text.strip()

    if not text.endswith((".", "!", "?")):
        last_punct = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
        if last_punct > 100:
            text = text[: last_punct + 1]

    return text


def remove_title_overlap(title, text):
    if title and text.lower().startswith(title.lower()):
        return text[len(title):].strip()
    return text


def chunk_elements(elements, chunk_size=400, overlap=80):
    sections = group_by_sections(elements)
    chunks = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". "],
    )

    for section in sections:
        text = clean_leading_noise(section["content"])
        title = section["title"]

        split_chunks = splitter.split_text(text)

        for chunk in split_chunks:
            chunk = clean_chunk_boundaries(chunk)

            chunk = remove_title_overlap(title, chunk)

            if not is_valid_chunk(chunk):
                continue

            content = chunk if not title else f"{title}\n\n{chunk}"

            chunks.append({
                "section": title,
                "content": content
            })

    return chunks


if __name__ == "__main__":
    import sys
    from extract import extract_pdf_elements
    from clean import clean_elements
    path = sys.argv[1] if len(sys.argv) > 1 else input("PDF path: ").strip()
    elements = clean_elements(extract_pdf_elements(path))
    chunks = chunk_elements(elements)
    print(f"Generated {len(chunks)} chunks")
    for c in chunks[:3]:
        print(f"\n[{c['section']}]\n{c['content'][:200]}")