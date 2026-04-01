# Muhasebe Belge Cikarim Uygulamasi (Desktop + Web)

Bu proje evraklardan muhasebe on hazirlik verilerini cikarir ve Excel uyumlu CSV uretir.
OpenAI baglantisi resmi HTTP API uzerinden yapilir (SDK zorunlu degil).

## Desteklenen Arayuzler
- Masaustu uygulama (Tkinter): `app.py`
- Web uygulama (Streamlit): `web_app.py`

## Ozellikler
- PDF, PNG, JPG, JPEG belge isleme
- Belge turu, tarih, belge no, firma, vergi no, KDV, toplam gibi alanlari cikarma
- Supheli/eksik alanlari `Not_Supheli_Alan` kolonunda isaretleme
- Tek satir/sutun mantiginda CSV cikti
- Masaustu surumde klasor izleme otomasyonu
- Gorsel tabanli PDF'lerde (scan) goruntu fallback okuma
- Isleme baslamadan API key dogrulama

## Kurulum
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Web arayuzu da kullanacaksan:
```powershell
pip install -r requirements-web.txt
```

## Masaustu Calistirma
```powershell
python app.py
```
veya
```powershell
powershell -ExecutionPolicy Bypass -File .\run_desktop.ps1
```
veya (en kolay):
- `BASLAT_DESKTOP.bat` dosyasina cift tikla.

## Web Calistirma
```powershell
streamlit run web_app.py
```
veya
```powershell
powershell -ExecutionPolicy Bypass -File .\run_web.ps1
```

## EXE Paketleme (Windows)
```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Olusan dosya:
- `dist\MuhasebeBelgeCikarim.exe`

## CSV Kolonlari
`Dosya, Belge_turu, Tarih, Belge_No, Firma_Kisi_Adi, VergiNo_TCKN, Aciklama, AraToplam_Matrah, KDV_Orani, KDV_Tutari, Genel_Toplam, Odeme_Sekli, Doviz_Tutari, TL_Karsiligi, Not_Supheli_Alan`

## Is Kurallari
- Belgede yazmayan bilgi eklenmez.
- El yazisi, kase, imza, cizik ve kullanici notlari ana veri sayilmaz.
- Cok kalemli belgelerde once toplam alanlar onceliklendirilir.
- Celiski varsa not kolonuna acikca yazilir.

## En Kolay Kullanim (Mali Musavir Modu)
1. `BASLAT_DESKTOP.bat` dosyasina cift tikla.
2. OpenAI key'i bir kere gir.
3. `API Key Test Et` butonuna bas.
4. `Ayarlari Kaydet` butonuna bas (bir daha key girmezsin).
5. Tek seferlik islem icin:
   - `Belge Sec` -> `Secilenleri Isle` -> `CSV Disa Aktar`
6. Surekli otomasyon icin:
   - `Izleme Klasoru` sec -> `CSV Cikti` sec -> `Otomasyon Baslat`
