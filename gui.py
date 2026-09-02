from __future__ import annotations

import base64
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import fitz

from pdf_crop import crop_pdf_region


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "output"
TEST_DIR = ROOT / "test_files"
TEST_PDF = TEST_DIR / "test_document.pdf"


class PdfCropApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PDF → Image Crop")
        self.geometry("1050x820")
        self.minsize(900, 700)

        DEFAULT_OUTPUT.mkdir(exist_ok=True)
        TEST_DIR.mkdir(exist_ok=True)

        self.pdf_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT))
        self.output_name = tk.StringVar(value="crop.png")
        self.page_number = tk.IntVar(value=1)
        self.dpi = tk.IntVar(value=200)
        self.coords_text = tk.StringVar(value="Sleep een vak over de preview")

        self.document: fitz.Document | None = None
        self.page: fitz.Page | None = None
        self.photo: tk.PhotoImage | None = None
        self.preview_scale = 1.0
        self.selection_start: tuple[float, float] | None = None
        self.selection_rect: int | None = None
        self.pdf_rect: tuple[float, float, float, float] | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="PDF bestand").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.pdf_path).grid(row=1, column=0, columnspan=4, sticky="ew", padx=(0, 8))
        ttk.Button(top, text="Kies PDF", command=self.choose_pdf).grid(row=1, column=4, padx=4)
        ttk.Button(top, text="Maak test PDF", command=self.make_test_pdf).grid(row=1, column=5, padx=4)

        ttk.Label(top, text="Output map").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(top, textvariable=self.output_dir).grid(row=3, column=0, columnspan=3, sticky="ew", padx=(0, 8))
        ttk.Button(top, text="Kies map", command=self.choose_output).grid(row=3, column=3, padx=4)

        ttk.Label(top, text="Bestandsnaam").grid(row=2, column=4, sticky="w", pady=(10, 0))
        ttk.Entry(top, textvariable=self.output_name, width=20).grid(row=3, column=4, columnspan=2, sticky="ew")

        settings = ttk.Frame(top)
        settings.grid(row=4, column=0, columnspan=6, sticky="ew", pady=(12, 0))

        ttk.Label(settings, text="Pagina").pack(side="left")
        ttk.Spinbox(settings, from_=1, to=9999, width=6, textvariable=self.page_number, command=self.load_preview).pack(side="left", padx=(5, 16))
        ttk.Label(settings, text="DPI output").pack(side="left")
        ttk.Spinbox(settings, from_=72, to=600, increment=25, width=7, textvariable=self.dpi).pack(side="left", padx=(5, 16))
        ttk.Button(settings, text="Preview vernieuwen", command=self.load_preview).pack(side="left")
        ttk.Label(settings, textvariable=self.coords_text).pack(side="left", padx=18)
        ttk.Button(settings, text="OPSLAAN ALS AFBEELDING", command=self.save_crop).pack(side="right")

        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)
        top.columnconfigure(2, weight=1)

        canvas_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(canvas_frame, background="#262626", cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.drag_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)
        self.canvas.bind("<Configure>", lambda _event: self.load_preview() if self.document else None)

    def choose_pdf(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF bestanden", "*.pdf")])
        if not path:
            return
        self.pdf_path.set(path)
        self.page_number.set(1)
        self.open_pdf()

    def choose_output(self) -> None:
        path = filedialog.askdirectory(initialdir=self.output_dir.get())
        if path:
            self.output_dir.set(path)

    def open_pdf(self) -> None:
        path = Path(self.pdf_path.get())
        if not path.exists():
            messagebox.showerror("Fout", "PDF bestand bestaat niet.")
            return
        if self.document:
            self.document.close()
        self.document = fitz.open(path)
        self.load_preview()

    def load_preview(self) -> None:
        if not self.document:
            return

        page_index = self.page_number.get() - 1
        if page_index < 0 or page_index >= self.document.page_count:
            return

        self.page = self.document.load_page(page_index)
        rect = self.page.rect

        canvas_w = max(self.canvas.winfo_width() - 30, 300)
        canvas_h = max(self.canvas.winfo_height() - 30, 300)
        self.preview_scale = min(canvas_w / rect.width, canvas_h / rect.height, 2.0)

        pix = self.page.get_pixmap(matrix=fitz.Matrix(self.preview_scale, self.preview_scale), alpha=False)
        png_b64 = base64.b64encode(pix.tobytes("png")).decode("ascii")
        self.photo = tk.PhotoImage(data=png_b64)

        self.canvas.delete("all")
        x = (self.canvas.winfo_width() - self.photo.width()) / 2
        y = (self.canvas.winfo_height() - self.photo.height()) / 2
        self.canvas.create_image(x, y, anchor="nw", image=self.photo, tags="page")
        self.canvas.image_origin = (x, y)
        self.selection_rect = None
        self.pdf_rect = None
        self.coords_text.set("Sleep een vak over de preview")

    def start_selection(self, event: tk.Event) -> None:
        if not self.page:
            return
        self.selection_start = (event.x, event.y)
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        self.selection_rect = self.canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="#ff3030",
            width=3,
        )

    def drag_selection(self, event: tk.Event) -> None:
        if not self.selection_start or not self.selection_rect:
            return
        x0, y0 = self.selection_start
        self.canvas.coords(self.selection_rect, x0, y0, event.x, event.y)

    def end_selection(self, event: tk.Event) -> None:
        if not self.selection_start or not self.page:
            return

        x0, y0 = self.selection_start
        x1, x2 = sorted((x0, event.x))
        y1, y2 = sorted((y0, event.y))
        origin_x, origin_y = self.canvas.image_origin

        page_x1 = max(0, (x1 - origin_x) / self.preview_scale)
        page_y1 = max(0, (y1 - origin_y) / self.preview_scale)
        page_x2 = min(self.page.rect.width, (x2 - origin_x) / self.preview_scale)
        page_y2 = min(self.page.rect.height, (y2 - origin_y) / self.preview_scale)

        if page_x2 - page_x1 < 2 or page_y2 - page_y1 < 2:
            self.pdf_rect = None
            self.coords_text.set("Selectie is te klein")
            return

        self.pdf_rect = (page_x1, page_y1, page_x2, page_y2)
        self.coords_text.set(
            f"x1={page_x1:.1f}  y1={page_y1:.1f}  x2={page_x2:.1f}  y2={page_y2:.1f}"
        )

    def save_crop(self) -> None:
        if not self.pdf_rect:
            messagebox.showwarning("Geen selectie", "Sleep eerst een vak over de PDF preview.")
            return

        name = self.output_name.get().strip() or "crop.png"
        if not name.lower().endswith((".png", ".jpg", ".jpeg")):
            name += ".png"

        output = Path(self.output_dir.get()) / name
        x1, y1, x2, y2 = self.pdf_rect

        try:
            crop_pdf_region(
                Path(self.pdf_path.get()),
                output,
                self.page_number.get(),
                x1,
                y1,
                x2,
                y2,
                self.dpi.get(),
            )
        except Exception as exc:
            messagebox.showerror("Fout", str(exc))
            return

        messagebox.showinfo("Klaar", f"Afbeelding opgeslagen:\n{output}")

    def make_test_pdf(self) -> None:
        TEST_DIR.mkdir(exist_ok=True)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((55, 70), "TEST PDF - PDF TO IMAGE", fontsize=22)
        page.insert_text((55, 105), "Sleep in de app een rood vak om een onderdeel.", fontsize=12)

        boxes = [
            (55, 155, 540, 260, "BLOK 1 - Omzet: EUR 125.000"),
            (55, 300, 540, 405, "BLOK 2 - Kosten: EUR 80.000"),
            (55, 445, 540, 550, "BLOK 3 - Winst: EUR 45.000"),
        ]
        for x1, y1, x2, y2, text in boxes:
            page.draw_rect(fitz.Rect(x1, y1, x2, y2), width=1.5)
            page.insert_text((x1 + 20, y1 + 55), text, fontsize=16)

        doc.save(TEST_PDF)
        doc.close()
        self.pdf_path.set(str(TEST_PDF))
        self.page_number.set(1)
        self.open_pdf()
        messagebox.showinfo("Test PDF", f"Testbestand gemaakt:\n{TEST_PDF}")


if __name__ == "__main__":
    app = PdfCropApp()
    app.mainloop()
