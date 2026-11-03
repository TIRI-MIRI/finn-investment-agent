from pypdf import PdfReader

r = PdfReader("data/filings/doc-2ae36f62af8bd4862f70629b.pdf")
print("Pages:", len(r.pages))
for i in range(len(r.pages)):
    print(f"=== PAGE {i+1} ===")
    print(r.pages[i].extract_text())
