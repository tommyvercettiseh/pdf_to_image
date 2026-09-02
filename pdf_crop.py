from pathlib import Path
import argparse
import fitz  # PyMuPDF


def crop_pdf_region(
    pdf_path: Path,
    output_path: Path,
    page_number: int,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    dpi: int = 200,
) -> None:
    """Render een rechthoekig gedeelte van een PDF-pagina naar PNG/JPG."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF niet gevonden: {pdf_path}")

    if page_number < 1:
        raise ValueError("page_number begint bij 1.")

    if x2 <= x1 or y2 <= y1:
        raise ValueError("Ongeldig gebied. x2/y2 moeten groter zijn dan x1/y1.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as document:
        if page_number > document.page_count:
            raise ValueError(
                f"PDF heeft {document.page_count} pagina('s), maar pagina {page_number} werd gevraagd."
            )

        page = document.load_page(page_number - 1)
        page_rect = page.rect

        clip = fitz.Rect(x1, y1, x2, y2) & page_rect
        if clip.is_empty:
            raise ValueError("Het gekozen gebied valt buiten de PDF-pagina.")

        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
        pixmap.save(str(output_path))

    print(f"Opgeslagen: {output_path.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sla een vast gedeelte van een PDF-pagina op als afbeelding."
    )
    parser.add_argument("pdf", type=Path, help="Pad naar het PDF-bestand")
    parser.add_argument("output", type=Path, help="Pad naar de output-afbeelding")
    parser.add_argument("--page", type=int, default=1, help="Paginanummer, standaard 1")
    parser.add_argument("--x1", type=float, required=True, help="Linker X-coordinaat")
    parser.add_argument("--y1", type=float, required=True, help="Bovenste Y-coordinaat")
    parser.add_argument("--x2", type=float, required=True, help="Rechter X-coordinaat")
    parser.add_argument("--y2", type=float, required=True, help="Onderste Y-coordinaat")
    parser.add_argument("--dpi", type=int, default=200, help="Resolutie, standaard 200 DPI")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    crop_pdf_region(
        pdf_path=args.pdf,
        output_path=args.output,
        page_number=args.page,
        x1=args.x1,
        y1=args.y1,
        x2=args.x2,
        y2=args.y2,
        dpi=args.dpi,
    )
