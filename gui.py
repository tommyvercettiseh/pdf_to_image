from __future__ import annotations

import base64
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import fitz

from pdf_crop import crop_pdf_region


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "input"
DEFAULT_OUTPUT = ROOT / "output"
TEST_DIR = ROOT / "test_files"
TEST_PDF = TEST_DIR / "test_document.pdf"


class PdfCropApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Crop Watcher")
        self.geometry("1120x860")
        self.minsize(980, 720)

        DEFAULT_INPUT.mkdir(exist_ok=True)
        DEFAULT_OUTPUT.mkdir(exist_ok=True)
        TEST_DIR.mkdir(exist_ok=True)

        self.mode = tk.StringVar(value="test")
        self.pdf_path = tk.StringVar()
        self.input_dir = tk.StringVar(value=str(DEFAULT_INPUT))
        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT))
        self.page_number = tk.IntVar(value=1)
        self.dpi = tk.IntVar(value=200)
        self.coords_text = tk.StringVar(value="Sleep een vak over de preview")
        self.status_text = tk.StringVar(value="Klaar")
        self.watch_interval = tk.DoubleVar(value=2.0)

        self.document: fitz.Document | None = None
        self.page: fitz.Page | None = None
        self.photo: tk.PhotoImage | None = None
        self.preview_scale = 1.0
        self.selection_start: tuple[float, float] | None = None
        self.selection_rect: int | None = None
        self.pdf_rect: tuple[float, float, float, float] | None = None
        self.watching = False
        self.processed: dict[str, tuple[int, float]] = {}

        self._build_ui()
        self._refresh_mode()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="PDF Crop Watcher", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, text="Test één PDF of bewaak continu een inputmap", foreground="#666").pack(side="left", padx=14)

        mode_frame = ttk.LabelFrame(outer, text="1. Kies werkwijze", padding=10)
        mode_frame.pack(fill="x", pady=(12, 8))
        ttk.Radiobutton(mode_frame, text="Testmodus", variable=self.mode, value="test", command=self._refresh_mode).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="Mapmodus / continu verwerken", variable=self.mode, value="folder", command=self._refresh_mode).pack(side="left")

        self.test_frame = ttk.LabelFrame(outer, text="2. Testomgeving", padding=10)
        self.test_frame.pack(fill="x", pady=8)
        ttk.Label(self.test_frame, text="Test PDF").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.test_frame, textvariable=self.pdf_path).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(self.test_frame, text="Kies PDF", command=self.choose_pdf).grid(row=1, column=1, padx=4)
        ttk.Button(self.test_frame, text="Maak test PDF", command=self.make_test_pdf).grid(row=1, column=2, padx=4)
        self.test_frame.columnconfigure(0, weight=1)

        self.folder_frame = ttk.LabelFrame(outer, text="2. Mappen voor automatische verwerking", padding=10)
        self.folder_frame.pack(fill="x", pady=8)
        ttk.Label(self.folder_frame, text="Input map  •  nieuwe PDF's worden hier gelezen").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.folder_frame, textvariable=self.input_dir).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(self.folder_frame, text="Kies input map", command=self.choose_input).grid(row=1, column=1, padx=4)
        ttk.Label(self.folder_frame, text="Output map  •  exports komen hier terecht").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(self.folder_frame, textvariable=self.output_dir).grid(row=3, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(self.folder_frame, text="Kies output map", command=self.choose_output).grid(row=3, column=1, padx=4)
        self.folder_frame.columnconfigure(0, weight=1)

        settings = ttk.LabelFrame(outer, text="3. Crop instellen", padding=10)
        settings.pack(fill="x", pady=8)
        ttk.Label(settings, text="Pagina").pack(side="left")
        ttk.Spinbox(settings, from_=1, to=9999, width=6, textvariable=self.page_number, command=self.load_preview).pack(side="left", padx=(5, 16))
        ttk.Label(settings, text="DPI").pack(side="left")
        ttk.Spinbox(settings, from_=72, to=600, increment=25, width=7, textvariable=self.dpi).pack(side="left", padx=(5, 16))
        ttk.Label(settings, textvariable=self.coords_text).pack(side="left", padx=12)
        ttk.Button(settings, text="Preview vernieuwen", command=self.load_preview).pack(side="right")

        canvas_frame = ttk.LabelFrame(outer, text="Preview  •  sleep met je muis het gebied dat je wilt exporteren", padding=8)
        canvas_frame.pack(fill="both", expand=True, pady=8)
        self.canvas = tk.Canvas(canvas_frame, background="#262626", cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.drag_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)
        self.canvas.bind("<Configure>", lambda _event: self.load_preview() if self.document else None)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Label(actions, textvariable=self.status_text).pack(side="left")
        self.test_save_button = ttk.Button(actions, text="TEST CROP OPSLAAN", command=self.save_test_crop)
        self.test_save_button.pack(side="right")

        self.watch_controls = ttk.Frame(actions)
        self.watch_controls.pack(side="right", padx=8)
        ttk.Label(self.watch_controls, text="Check elke").pack(side="left")
        ttk.Spinbox(self.watch_controls, from_=1, to=60, increment=1, width=5, textvariable=self.watch_interval).pack(side="left", padx=4)
        ttk.Label(self.watch_controls, text="sec").pack(side="left", padx=(0, 8))
        self.watch_button = ttk.Button(self.watch_controls, text="START MAP BEWAKEN", command=self.toggle_watch)
        self.watch_button.pack(side="left")

    def _refresh_mode(self) -> None:
        folder = self.mode.get() == "folder"
        if folder:
            self.test_frame.pack_forget()
            self.folder_frame.pack(fill="x", pady=8, after=self.test_frame.master.winfo_children()[1])
            self.test_save_button.pack_forget()
            self.watch_controls.pack(side="right", padx=8)
        else:
            self.folder_frame.pack_forget()
            self.test_frame.pack(fill="x", pady=8, after=self.test_frame.master.winfo_children()[1])
            self.watch_controls.pack_forget()
            self.test_save_button.pack(side="right")

    def choose_pdf(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF bestanden", "*.pdf")])
        if path:
            self.pdf_path.set(path)
            self.page_number.set(1)
            self.open_pdf(Path(path))

    def choose_input(self) -> None:
        path = filedialog.askdirectory(initialdir=self.input_dir.get())
        if path:
            self.input_dir.set(path)
            pdfs = sorted(Path(path).glob("*.pdf"))
            if pdfs:
                self.pdf_path.set(str(pdfs[0]))
                self.open_pdf(pdfs[0])

    def choose_output(self) -> None:
        path = filedialog.askdirectory(initialdir=self.output_dir.get())
        if path:
            self.output_dir.set(path)

    def open_pdf(self, path: Path) -> None:
        if not path.exists():
            return
        if self.document:
            self.document.close()
        try:
            self.document = fitz.open(path)
            self.pdf_path.set(str(path))
            self.load_preview()
            self.status_text.set(f"Preview: {path.name}")
        except Exception as exc:
            messagebox.showerror("PDF fout", str(exc))

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
        self.canvas.create_image(x, y, anchor="nw", image=self.photo)
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
        self.selection_rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="#ff3030", width=3)

    def drag_selection(self, event: tk.Event) -> None:
        if self.selection_start and self.selection_rect:
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
        self.coords_text.set(f"x1={page_x1:.1f}  y1={page_y1:.1f}  x2={page_x2:.1f}  y2={page_y2:.1f}")

    def output_name_for(self, pdf_path: Path) -> str:
        return f"{pdf_path.stem}_crop.png"

    def save_test_crop(self) -> None:
        if not self.pdf_rect:
            messagebox.showwarning("Geen selectie", "Sleep eerst een vak over de PDF preview.")
            return
        pdf = Path(self.pdf_path.get())
        output = Path(self.output_dir.get()) / self.output_name_for(pdf)
        self._crop_one(pdf, output, show_message=True)

    def _crop_one(self, pdf: Path, output: Path, show_message: bool = False) -> bool:
        if not self.pdf_rect:
            return False
        x1, y1, x2, y2 = self.pdf_rect
        try:
            crop_pdf_region(pdf, output, self.page_number.get(), x1, y1, x2, y2, self.dpi.get())
            if show_message:
                messagebox.showinfo("Klaar", f"Afbeelding opgeslagen:\n{output}")
            return True
        except Exception as exc:
            if show_message:
                messagebox.showerror("Fout", str(exc))
            return False

    def toggle_watch(self) -> None:
        if self.watching:
            self.watching = False
            self.watch_button.config(text="START MAP BEWAKEN")
            self.status_text.set("Mapbewaking gestopt")
            return
        if not self.pdf_rect:
            messagebox.showwarning("Geen crop", "Open eerst een voorbeeld-PDF en selecteer het vaste cropgebied.")
            return
        input_dir = Path(self.input_dir.get())
        output_dir = Path(self.output_dir.get())
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.watching = True
        self.processed.clear()
        self.watch_button.config(text="STOP MAP BEWAKEN")
        self.status_text.set("Mapbewaking actief")
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def _watch_loop(self) -> None:
        while self.watching:
            input_dir = Path(self.input_dir.get())
            output_dir = Path(self.output_dir.get())
            for pdf in sorted(input_dir.glob("*.pdf")):
                try:
                    stat = pdf.stat()
                except OSError:
                    continue
                signature = (stat.st_size, stat.st_mtime)
                if self.processed.get(str(pdf)) == signature:
                    continue
                output = output_dir / self.output_name_for(pdf)
                ok = self._crop_one(pdf, output)
                if ok:
                    self.processed[str(pdf)] = signature
                    self.after(0, lambda n=pdf.name, o=output.name: self.status_text.set(f"Verwerkt: {n} → {o}"))
            time.sleep(max(1.0, float(self.watch_interval.get())))

    def make_test_pdf(self) -> None:
        TEST_DIR.mkdir(exist_ok=True)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((55, 70), "TEST PDF - PDF TO IMAGE", fontsize=22)
        page.insert_text((55, 105), "Gebruik dit bestand om je vaste cropgebied te bepalen.", fontsize=12)
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
        self.open_pdf(TEST_PDF)
        messagebox.showinfo("Test PDF", f"Testbestand gemaakt:\n{TEST_PDF}")


if __name__ == "__main__":
    PdfCropApp().mainloop()
