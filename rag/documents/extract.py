# step1: extract text from pdf using unstrcutured to get headers and titles and keep their meaning

from unstructured.partition.pdf import partition_pdf


def extract_pdf_elements(file_path: str):
    elements = partition_pdf(
        filename=file_path,
        strategy="fast"
    )
    return elements


def preview_elements(elements, n=20):
    for i, el in enumerate(elements[:n]):
        text_preview = el.text[:100].replace("\n", " ") if el.text else ""
        print(f"{i+1}. [{el.category}] → {text_preview}")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else input("PDF path: ").strip()
    elements = extract_pdf_elements(path)
    print(f"Extracted {len(elements)} elements")
    preview_elements(elements)