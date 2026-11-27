# ALICE_010 — SÉCURITÉ DES ARCHIVES DOCX / EPUB (F07)

- **Finding :** `F07` — Décompression ZIP non bornée dans les parsers DOCX et EPUB (`alice_rag.py`)
- **Statut :** `FIXED_VERIFIED`

## 1. Limites implémentées (`Jarvis Final - SITE/alice_rag.py`)
- Taille maximale du fichier compressé : `25 Mo` (`MAX_ARCHIVE_FILE_BYTES`).
- Nombre maximal d'entrées par archive : `500` (`MAX_ARCHIVE_ENTRIES`).
- Taille décompressée maximale par entrée : `5 Mo` (`MAX_ENTRY_UNCOMPRESSED_BYTES`), mesurée par lecture par blocs de 64 Ko sur **les octets réels lus** (sans confiance aveugle aux métadonnées ZIP).
- Taille décompressée cumulée maximale : `20 Mo` (`MAX_TOTAL_UNCOMPRESSED_BYTES`).
- Ratio de compression maximal : `100.0` (`MAX_COMPRESSION_RATIO` au-delà de 1 Mo).
- Rejet strict des chemins dangereux (`..`, `/`, `\`, octet nul) via `_is_safe_zip_entry_name()`.

## 2. Preuve
- `TestF07ZipBombAndTraversal` (**PASS**) : rejet vérifié d'un `.docx` avec `../../evil.txt` et d'un `.docx` avec entrée compressée de 6 Mo décompressés.
