import base64
import io
import json
import mimetypes
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from pypdf import PdfReader


FIELDS = [
    "Belge_turu",
    "Tarih",
    "Belge_No",
    "Firma_Kisi_Adi",
    "VergiNo_TCKN",
    "Aciklama",
    "AraToplam_Matrah",
    "KDV_Orani",
    "KDV_Tutari",
    "Genel_Toplam",
    "Odeme_Sekli",
    "Doviz_Tutari",
    "TL_Karsiligi",
    "Not_Supheli_Alan",
]


SYSTEM_PROMPT = """Sen bir mali musavir yardimcisi gibi calisan belge okuma ve veri cikarma uzmansin.
Sadece belgedeki gorunur veriyi cikart.
Asla uydurma veri uretme.
El yazisi, kose/imza ve sonradan eklenmis notlari ana veri sayma.
Belgede celiski varsa Not_Supheli_Alan alaninda acikca belirt.
Eksik bilgi varsa bos birak ve Not_Supheli_Alan alanina yaz.
Bir belge icinde birden fazla kalem varsa once toplam verileri doldur.
Tum cikti tek bir JSON object olsun.
JSON object sadece su anahtarlari icersin:
Belge_turu, Tarih, Belge_No, Firma_Kisi_Adi, VergiNo_TCKN, Aciklama, AraToplam_Matrah,
KDV_Orani, KDV_Tutari, Genel_Toplam, Odeme_Sekli, Doviz_Tutari, TL_Karsiligi, Not_Supheli_Alan
Degerler metin olmalidir. Bilgi yoksa bos string ver.
"""


@dataclass
class ExtractionResult:
    file_name: str
    row: Dict[str, str]


class DocumentExtractor:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def extract_from_file(self, file_path: Path) -> ExtractionResult:
        mime_type, _ = mimetypes.guess_type(str(file_path))
        file_bytes = file_path.read_bytes()
        return self.extract_from_bytes(file_path.name, file_bytes, mime_type)

    def extract_from_bytes(
        self, file_name: str, file_bytes: bytes, mime_type: Optional[str] = None
    ) -> ExtractionResult:
        content_parts = [{"type": "text", "text": self._user_instruction(file_name)}]
        content_parts.extend(self._build_content(file_name, file_bytes, mime_type))

        raw = self._chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content_parts},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        parsed = self._safe_json(raw)
        normalized = {k: str(parsed.get(k, "") or "") for k in FIELDS}
        return ExtractionResult(file_name=file_name, row=normalized)

    def validate_api_key(self) -> None:
        # Hafif bir endpoint ile anahtarin gecerliligini kontrol eder.
        self._request_json(url="https://api.openai.com/v1/models", method="GET")

    def _chat_completion(self, messages: List[Dict[str, object]], temperature: float, response_format: Dict[str, str]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": response_format,
        }
        result = self._request_json(
            url="https://api.openai.com/v1/chat/completions",
            method="POST",
            payload=payload,
        )
        try:
            return result["choices"][0]["message"]["content"] or "{}"
        except Exception as exc:
            raise RuntimeError(f"Beklenmeyen API cevabi: {result}") from exc

    def _request_json(self, url: str, method: str, payload: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="ignore")
            error_code = ""
            error_message = ""
            try:
                parsed = json.loads(body_text)
                error_obj = parsed.get("error", {})
                error_code = str(error_obj.get("code", "") or "")
                error_message = str(error_obj.get("message", "") or "")
            except Exception:
                pass

            if error_code == "invalid_api_key":
                raise RuntimeError("OpenAI API key gecersiz. Lutfen dogru key girin.") from exc
            if exc.code == 401:
                raise RuntimeError("OpenAI API yetkilendirme hatasi (401). API key'i kontrol edin.") from exc
            if exc.code == 429:
                raise RuntimeError("OpenAI API kota/limit hatasi (429). Billing ve limitleri kontrol edin.") from exc
            if error_message:
                raise RuntimeError(f"OpenAI API hatasi ({exc.code}): {error_message}") from exc
            raise RuntimeError(f"OpenAI API hatasi ({exc.code}).") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI API baglanti hatasi: {exc}") from exc

    def _build_content(
        self, file_name: str, file_bytes: bytes, mime_type: Optional[str]
    ) -> List[Dict[str, object]]:
        parts: List[Dict[str, object]] = []
        suffix = Path(file_name).suffix.lower()

        if mime_type and mime_type.startswith("image/"):
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._bytes_to_data_url(file_bytes, mime_type)},
                }
            )
            return parts

        if suffix == ".pdf":
            text = self._extract_pdf_text(file_bytes)
            if text.strip():
                parts.append({"type": "text", "text": f"PDF metni:\n{text[:18000]}"})
            else:
                parts.append(
                    {
                        "type": "text",
                        "text": "PDF icinde secilebilir metin bulunamadi. Gorsel tabanli olabilir.",
                    }
                )

            image_data_url = self._extract_pdf_image_data_url(file_bytes)
            if image_data_url:
                parts.append({"type": "image_url", "image_url": {"url": image_data_url}})
            return parts

        text = file_bytes.decode("utf-8", errors="ignore")
        parts.append({"type": "text", "text": f"Belge metni:\n{text[:18000]}"})
        return parts

    @staticmethod
    def _extract_pdf_text(file_bytes: bytes) -> str:
        reader = PdfReader(io.BytesIO(file_bytes))
        chunks: List[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                chunks.append(page_text)
        return "\n\n".join(chunks)

    def _extract_pdf_image_data_url(self, file_bytes: bytes) -> Optional[str]:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            try:
                images = list(page.images)
            except Exception:
                images = []
            for image in images:
                data = getattr(image, "data", None)
                if not data:
                    continue
                ext = Path(getattr(image, "name", "")).suffix.lower()
                mime = self._mime_from_ext(ext)
                return self._bytes_to_data_url(data, mime)

        # Fallback: bazı PDF'lerde gömülü JPEG doğrudan stream içinde olur.
        jpg = self._extract_embedded_jpeg(file_bytes)
        if jpg:
            return self._bytes_to_data_url(jpg, "image/jpeg")
        return None

    @staticmethod
    def _extract_embedded_jpeg(file_bytes: bytes) -> Optional[bytes]:
        start = file_bytes.find(b"\xff\xd8")
        if start == -1:
            return None
        end = file_bytes.find(b"\xff\xd9", start + 2)
        if end == -1:
            return None
        end += 2
        candidate = file_bytes[start:end]
        if len(candidate) < 1024:
            return None
        return candidate

    @staticmethod
    def _mime_from_ext(ext: str) -> str:
        if ext == ".png":
            return "image/png"
        if ext in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if ext == ".webp":
            return "image/webp"
        return "image/jpeg"

    @staticmethod
    def _user_instruction(file_name: str) -> str:
        return (
            f"Dosya adi: {file_name}\n"
            "Belgeyi oku ve alanlari doldur. Yazim bicimini belgeye sadik tut.\n"
            "Belge turunu acik yaz (fatura, perakende fis, serbest meslek makbuzu, banka dekontu, Z raporu vb.)."
        )

    @staticmethod
    def _bytes_to_data_url(file_bytes: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(file_bytes).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    @staticmethod
    def _safe_json(payload: str) -> Dict[str, str]:
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            start = payload.find("{")
            end = payload.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(payload[start : end + 1])
                except json.JSONDecodeError:
                    pass
        return {}
