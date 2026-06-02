"""One-shot: Docling-convert the IFAB PDF to markdown on CPU (avoids MPS OOM).

Forces the CPU accelerator and disables OCR (the IFAB single-pages PDF has a real
text layer), which keeps memory bounded on a laptop. Writes the markdown to the
``.docling.md`` sidecar that app/rag/ingest.py reads as its cache.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

pdf = Path(sys.argv[1])
out = pdf.with_suffix(".docling.md")

opts = PdfPipelineOptions()
opts.accelerator_options = AcceleratorOptions(device=AcceleratorDevice.CPU)
opts.do_ocr = False  # digital text layer present; skip the heavy OCR model

t = time.time()
print("converting on CPU (OCR off)...", flush=True)
conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
md = conv.convert(str(pdf)).document.export_to_markdown()
out.write_text(md)
print(f"done in {time.time() - t:.0f}s | chars: {len(md)} | -> {out}", flush=True)
