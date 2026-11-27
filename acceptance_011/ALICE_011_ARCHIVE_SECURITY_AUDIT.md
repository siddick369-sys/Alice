# ALICE_011 — AUDIT SÉCURITÉ DES ARCHIVES ZIP/DOCX/EPUB (F07)

- **Statut F07 :** **`FIXED_VERIFIED`**
- **Inspection (`Jarvis Final - SITE/alice_rag.py`) :**
  - Limites appliquées sur le flux réellement décompressé par blocs de 64 Ko (`_safe_read_zip_entry`), sans se fier aux seules métadonnées ZIP : `25 Mo` compressé, `500` entrées, `5 Mo` par entrée, `20 Mo` cumulés, ratio `100.0` (> 1 Mo), rejet des chemins (`..`, `/`, `\`, `\x00`).
- **Preuves (`independent_probe.py` + `TestF07ZipBombAndTraversal`) :**
  - Rejet vérifié : archive 501 entrées, traversée Windows (`..\..\evil.txt`) et POSIX (`../../evil.txt`), XML malformé, bombe DOCX 6 Mo, EPUB 22,5 Mo cumulés ; ingestion DOCX valide (`Hello Audit 011`) réussie.
