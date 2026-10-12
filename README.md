# Telegram Handwriting Bot

MVP bot Telegram berbasis `aiogram` yang mengubah teks menjadi tulisan tangan di atas template buku, menampilkan preview, lalu mengekspor PNG atau PDF multi-halaman. Core renderer bekerja lokal tanpa LLM.

## Fitur

- Dua gaya tulisan berbasis 400+ raster glyph variants dan ligature bahasa Indonesia: `Agak Berantakan` dan `Rapih`. `Rapih` adalah default baru.
- Template buku garis, kotak, HVS, folio, serta upload template custom.
- Pilihan buku built-in dikelola dari folder `menu_buku/` melalui registry `config/books.py`; template custom tetap tersedia.
- Identitas 4 baris, tanggal hari ini/custom/disembunyikan, dan empat warna tinta.
- Word wrapping, preservasi paragraf/baris kosong, serta page breaking otomatis.
- Preview ringan dan final render A4 2480×3508 px.
- SQLite hanya menyimpan preferensi dan hash teks pada riwayat; teks asli tidak disimpan permanen.
- Rendering blocking dijalankan melalui `asyncio.to_thread()`.

## Menjalankan

Prasyarat: Python 3.12 atau lebih baru.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Isi `BOT_TOKEN` di `.env`, lalu:

```bash
python main.py
```

Bot menggunakan long polling. Buat token lewat BotFather dan jangan pernah memasukkan `.env` ke Git.

## Font dan template

Template bawaan ada di `assets/papers/`. Untuk membuat ulang aset tersebut:

```bash
python scripts/generate_assets.py
```

Masukkan font `.ttf` berlisensi ke `assets/fonts/` dengan nama `neat.ttf`, `semi_neat.ttf`, `student.ttf`, `slanted.ttf`, atau `messy.ttf`. Jika tidak ada, renderer mencoba font sistem. Font tulisan tangan sungguhan sangat disarankan untuk hasil realistis.

Style `natural_student_01` tidak memerlukan font saat runtime. Common lowercase dan ligature dibangun dari stroke/path vocabulary prosedural (loop, arch, bowl, stem, entry/exit), bukan sekadar transformasi satu font; uppercase, angka, dan punctuation tetap memakai fallback asset font-derived. Asset raster dan metadata-nya berada di `assets/handwriting/natural_student_01/`. Untuk membangun ulang asset pada mesin pengembangan yang memiliki font sumber lokal:

```bash
python scripts/generate_natural_student_assets.py
python scripts/render_handwriting_reference_test.py
python scripts/render_phase3_audits.py
```

Perintah audit menghasilkan `outputs/glyph_audit.png`, `outputs/word_audit.png`, dan `outputs/phase3_metrics.json`.

Template baru dapat ditambahkan di `renderer/paper.py`, atau diunggah user melalui menu Custom template. Upload custom dinormalisasi menjadi PNG A4 dan dibatasi 12 MB.

## Konfigurasi

| Variabel | Default | Keterangan |
|---|---:|---|
| `BOT_TOKEN` | wajib | Token Telegram bot |
| `DATABASE_PATH` | `data/bot.db` | Lokasi SQLite |
| `OUTPUT_DIR` | `outputs` | File final sementara |
| `MAX_TEXT_LENGTH` | `15000` | Batas karakter input |
| `MAX_OUTPUT_BYTES` | `50000000` | Batas total file hasil |
| `LOG_LEVEL` | `INFO` | Level logging |

Warna tinta dan parameter variasi tulisan terpusat di `config/settings.py`.

## Test

```bash
pytest -q
```

Test mencakup wrapping, page breaking, validasi tanggal, parsing identitas, preferensi SQLite, dan basic output renderer.

## Struktur penting

```text
bot/          handler, keyboard, dan FSM aiogram
renderer/     layout, handwriting, paper, dan export engine
database/     schema SQLite dan repository async
services/     validasi user dan orkestrasi rendering
config/       konfigurasi environment dan style
assets/       template kertas dan font
tests/        unit test
```

File final dihapus sesudah berhasil/gagal dikirim. Untuk PNG multi-halaman, setiap halaman dikirim sebagai dokumen agar resolusi tidak dikompresi Telegram.
