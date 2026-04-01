import csv
import json
import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from extractor import DocumentExtractor, ExtractionResult, FIELDS

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
DEFAULT_MODEL = "gpt-4o-mini"


def app_config_path() -> Path:
    base = Path(os.getenv("APPDATA", str(Path.home())))
    cfg_dir = base / "MuhasebeBelgeCikarim"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "settings.json"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Muhasebe Belge Cikarim Otomasyonu")
        self.geometry("1320x760")

        self.config_path = app_config_path()
        self.settings = self._load_settings()

        self.selected_files: List[Path] = []
        self.rows: List[ExtractionResult] = []
        self.auto_thread: Optional[threading.Thread] = None
        self.auto_stop = threading.Event()
        self.processed_in_automation = set()

        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="OpenAI API Key").grid(row=0, column=0, sticky="w")
        api_key_default = self.settings.get("api_key") or os.getenv("OPENAI_API_KEY", "")
        self.api_key_var = tk.StringVar(value=api_key_default)
        ttk.Entry(top, textvariable=self.api_key_var, width=64, show="*").grid(
            row=0, column=1, sticky="we", padx=8
        )

        ttk.Label(top, text="Model").grid(row=0, column=2, sticky="w")
        self.model_var = tk.StringVar(value=self.settings.get("model", DEFAULT_MODEL))
        ttk.Entry(top, textvariable=self.model_var, width=18).grid(row=0, column=3, sticky="w")

        ttk.Label(top, text="Izleme Klasoru").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.watch_dir_var = tk.StringVar(value=self.settings.get("watch_dir", str(Path.cwd())))
        ttk.Entry(top, textvariable=self.watch_dir_var, width=64).grid(
            row=1, column=1, sticky="we", padx=8, pady=(8, 0)
        )
        ttk.Button(top, text="Sec", command=self.choose_watch_dir).grid(row=1, column=2, sticky="w", pady=(8, 0))

        ttk.Label(top, text="CSV Cikti").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.csv_path_var = tk.StringVar(value=self.settings.get("csv_path", str(Path.cwd() / "cikti.csv")))
        ttk.Entry(top, textvariable=self.csv_path_var, width=64).grid(
            row=2, column=1, sticky="we", padx=8, pady=(8, 0)
        )
        ttk.Button(top, text="Sec", command=self.choose_csv_path).grid(row=2, column=2, sticky="w", pady=(8, 0))

        settings_row = ttk.Frame(self, padding=(10, 0))
        settings_row.pack(fill="x")
        ttk.Button(settings_row, text="API Key Test Et", command=self.test_api_key).pack(side="left")
        ttk.Button(settings_row, text="Ayarlari Kaydet", command=self.save_settings_from_ui).pack(side="left", padx=8)
        ttk.Button(settings_row, text="Tabloyu Temizle", command=self.clear_rows).pack(side="left")

        button_row = ttk.Frame(self, padding=(10, 8))
        button_row.pack(fill="x")
        ttk.Button(button_row, text="Belge Sec", command=self.select_files).pack(side="left")
        ttk.Button(button_row, text="Secilenleri Isle", command=self.process_selected).pack(side="left", padx=6)
        ttk.Button(button_row, text="CSV Disa Aktar", command=self.export_csv).pack(side="left")
        ttk.Button(button_row, text="Otomasyon Baslat", command=self.start_automation).pack(side="left", padx=20)
        ttk.Button(button_row, text="Otomasyon Durdur", command=self.stop_automation).pack(side="left")

        self.status_var = tk.StringVar(value="Hazir")
        ttk.Label(self, textvariable=self.status_var, padding=(10, 8)).pack(fill="x")

        table_frame = ttk.Frame(self, padding=10)
        table_frame.pack(fill="both", expand=True)

        columns = ["Dosya"] + FIELDS
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            width = 150 if col != "Not_Supheli_Alan" else 320
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        top.columnconfigure(1, weight=1)

    def _load_settings(self) -> Dict[str, str]:
        if not self.config_path.exists():
            return {}
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_settings(self, payload: Dict[str, str]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _current_settings_payload(self) -> Dict[str, str]:
        return {
            "api_key": self.api_key_var.get().strip(),
            "model": self.model_var.get().strip() or DEFAULT_MODEL,
            "watch_dir": self.watch_dir_var.get().strip() or str(Path.cwd()),
            "csv_path": self.csv_path_var.get().strip() or str(Path.cwd() / "cikti.csv"),
        }

    def save_settings_from_ui(self) -> None:
        payload = self._current_settings_payload()
        self._save_settings(payload)
        self.settings = payload
        self.status_var.set(f"Ayarlar kaydedildi: {self.config_path}")
        messagebox.showinfo("Basarili", "Ayarlar kaydedildi. Artik tekrar girmen gerekmez.")

    def _save_settings_silent(self) -> None:
        payload = self._current_settings_payload()
        self._save_settings(payload)
        self.settings = payload

    def choose_watch_dir(self) -> None:
        directory = filedialog.askdirectory(initialdir=self.watch_dir_var.get() or str(Path.cwd()))
        if directory:
            self.watch_dir_var.set(directory)

    def choose_csv_path(self) -> None:
        output = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=Path(self.csv_path_var.get()).name,
        )
        if output:
            self.csv_path_var.set(output)

    def clear_rows(self) -> None:
        self.rows = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.status_var.set("Tablo temizlendi.")

    def select_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Belgeleri sec",
            filetypes=[
                ("Belgeler", "*.pdf *.png *.jpg *.jpeg"),
                ("Tum Dosyalar", "*.*"),
            ],
        )
        picked = [Path(p) for p in paths]
        self.selected_files = [path for path in picked if self._is_supported_document(path)]
        skipped_count = len(picked) - len(self.selected_files)
        if skipped_count > 0:
            self.status_var.set(
                f"{len(self.selected_files)} belge secildi. {skipped_count} desteklenmeyen dosya atlandi."
            )
        else:
            self.status_var.set(f"{len(self.selected_files)} belge secildi.")

    def test_api_key(self) -> None:
        api_key = self.api_key_var.get().strip()
        model = self.model_var.get().strip() or DEFAULT_MODEL
        if not api_key:
            messagebox.showerror("Hata", "OpenAI API Key gerekli.")
            return
        try:
            self.status_var.set("API key test ediliyor...")
            self.update_idletasks()
            DocumentExtractor(api_key=api_key, model=model).validate_api_key()
            self.status_var.set("API key dogrulandi.")
            messagebox.showinfo("Basarili", "API key gecerli. Kaydetmek icin 'Ayarlari Kaydet' butonuna bas.")
        except Exception as exc:
            self.status_var.set("API key testi basarisiz.")
            messagebox.showerror("Hata", str(exc))

    def process_selected(self) -> None:
        if not self.selected_files:
            messagebox.showwarning("Uyari", "Once belge secin.")
            return
        self._process_files(self.selected_files)

    def _prepare_extractor(self) -> Optional[DocumentExtractor]:
        api_key = self.api_key_var.get().strip()
        model = self.model_var.get().strip() or DEFAULT_MODEL
        if not api_key:
            messagebox.showerror("Hata", "OpenAI API Key gerekli.")
            return None

        extractor = DocumentExtractor(api_key=api_key, model=model)
        try:
            self.status_var.set("API key dogrulaniyor...")
            self.update_idletasks()
            extractor.validate_api_key()
        except Exception as exc:
            messagebox.showerror("Hata", str(exc))
            self.status_var.set("API key dogrulama basarisiz.")
            return None
        return extractor

    def _process_files(self, files: List[Path]) -> bool:
        files = [path for path in files if self._is_supported_document(path)]
        if not files:
            messagebox.showwarning("Uyari", "Islenecek destekli belge bulunamadi (pdf/png/jpg/jpeg).")
            return False

        extractor = self._prepare_extractor()
        if extractor is None:
            return False

        self._save_settings_silent()
        total = len(files)
        for idx, file_path in enumerate(files, start=1):
            try:
                self.status_var.set(f"Isleniyor ({idx}/{total}): {file_path.name}")
                self.update_idletasks()
                result = extractor.extract_from_file(file_path)
                self.rows.append(result)
                self._insert_row(result)
            except Exception as exc:
                error_text = str(exc)
                if "API key" in error_text or "yetkilendirme" in error_text:
                    messagebox.showerror("Hata", error_text)
                    self.status_var.set("Islem durduruldu: API key sorunu.")
                    return False
                error_row = {k: "" for k in FIELDS}
                error_row["Not_Supheli_Alan"] = f"Hata: {error_text}"
                result = ExtractionResult(file_name=file_path.name, row=error_row)
                self.rows.append(result)
                self._insert_row(result)

        self.status_var.set(f"Tamamlandi. {total} dosya islendi.")
        return True

    def _insert_row(self, result: ExtractionResult) -> None:
        values = [result.file_name] + [result.row.get(k, "") for k in FIELDS]
        self.tree.insert("", "end", values=values)

    def export_csv(self) -> None:
        if not self.rows:
            messagebox.showwarning("Uyari", "Disa aktarilacak veri yok.")
            return
        output = Path(self.csv_path_var.get()).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)

        with output.open("w", newline="", encoding="utf-8-sig") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=["Dosya"] + FIELDS)
            writer.writeheader()
            for item in self.rows:
                payload = {"Dosya": item.file_name}
                payload.update(item.row)
                writer.writerow(payload)

        self.status_var.set(f"CSV yazildi: {output}")
        messagebox.showinfo("Basarili", f"CSV olusturuldu:\n{output}")

    def start_automation(self) -> None:
        if self.auto_thread and self.auto_thread.is_alive():
            messagebox.showinfo("Bilgi", "Otomasyon zaten calisiyor.")
            return

        watch_dir = Path(self.watch_dir_var.get()).expanduser()
        if not watch_dir.exists():
            messagebox.showerror("Hata", "Izleme klasoru bulunamadi.")
            return

        self._save_settings_silent()
        self.auto_stop.clear()
        self.auto_thread = threading.Thread(target=self._automation_loop, daemon=True)
        self.auto_thread.start()
        self.status_var.set(f"Otomasyon basladi: {watch_dir}")

    def stop_automation(self) -> None:
        self.auto_stop.set()
        self.status_var.set("Otomasyon durduruldu.")

    def _automation_loop(self) -> None:
        while not self.auto_stop.is_set():
            watch_dir = Path(self.watch_dir_var.get()).expanduser()
            if not watch_dir.exists():
                time.sleep(15)
                continue

            files = [
                file_path
                for file_path in watch_dir.iterdir()
                if (
                    file_path.is_file()
                    and self._is_supported_document(file_path)
                    and str(file_path) not in self.processed_in_automation
                )
            ]
            if files:
                self.after(0, lambda count=len(files): self.status_var.set(f"Otomasyon: {count} yeni belge bulundu."))
                self.after(0, lambda file_list=files: self._process_automation_batch(file_list))
            time.sleep(15)

    def _process_automation_batch(self, files: List[Path]) -> None:
        success = self._process_files(files)
        if not success:
            self.status_var.set("Otomasyon beklemede: API key/ayar kontrol et.")
            return

        for file_path in files:
            self.processed_in_automation.add(str(file_path))
        self.export_csv()

    @staticmethod
    def _is_supported_document(file_path: Path) -> bool:
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


if __name__ == "__main__":
    app = App()
    app.mainloop()
