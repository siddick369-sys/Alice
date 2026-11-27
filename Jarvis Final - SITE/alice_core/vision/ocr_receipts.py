#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 17 — SMART OCR RECEIPTS (ALICE-VISION-017, Wave 4).
Extrait tickets et factures via Tesseract 5.5 + OpenCV, vérifie la cohérence
arithmétique HT + TVA = TTC, bloque l'enregistrement silencieux des montants incertains,
permet la correction manuelle et exporte vers un classeur XLSX natif traçable.
"""

import os
import re
import time
import uuid
import json
import zipfile
import threading
from xml.sax.saxutils import escape
import numpy as np
import cv2
import pytesseract
from typing import Dict, Any, List, Optional
from alice_core.ops.observability import OBSERVABILITY


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class SmartReceiptOCR:
    """Extracteur comptable vérifiable de tickets et factures."""

    def __init__(self, storage_file: Optional[str] = None, tessdata_dir: Optional[str] = None):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.storage_file = storage_file or os.path.join(base_dir, "alice_outputs", "receipts_ledger.json")
        self.tessdata_dir = tessdata_dir or os.path.join(base_dir, "tessdata")
        self.receipts: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self.receipts = json.load(f)
            except Exception:
                self.receipts = {}

    def _save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            tmp = f"{self.storage_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.receipts, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.storage_file)

    @staticmethod
    def preprocess_receipt_image(image_path: str) -> Optional[np.ndarray]:
        img = cv2.imread(image_path)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Upscale x2 si petite image pour améliorer la précision Tesseract
        h, w = gray.shape
        if w < 1000:
            gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def run_ocr(self, image_path: str) -> str:
        proc = self.preprocess_receipt_image(image_path)
        if proc is None:
            raise FileNotFoundError(f"Impossible de lire l'image : {image_path}")
        if os.path.exists(self.tessdata_dir):
            os.environ["TESSDATA_PREFIX"] = self.tessdata_dir
        langs = "fra+eng"
        try:
            avail = pytesseract.get_languages()
            if "fra" not in avail:
                langs = "eng"
        except Exception:
            langs = "eng"
        return pytesseract.image_to_string(proc, lang=langs, config="--psm 6").strip()

    @staticmethod
    def _parse_amount(val_str: str) -> Optional[float]:
        try:
            cleaned = val_str.replace(",", ".").replace(" ", "").strip()
            return round(float(cleaned), 2)
        except Exception:
            return None

    def parse_receipt_text(self, raw_text: str) -> Dict[str, Any]:
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        merchant = lines[0][:80] if lines else None

        date_m = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", raw_text)
        date_val = date_m.group(1) if date_m else None

        inv_m = re.search(r"(?:facture|ticket|n[°o]|ref|invoice)\s*[:#]?\s*([A-Z0-9-]{4,24})", raw_text, re.IGNORECASE)
        invoice_num = inv_m.group(1) if inv_m else None

        currency = "EUR"
        if "$" in raw_text or "USD" in raw_text.upper():
            currency = "USD"
        elif "CHF" in raw_text.upper():
            currency = "CHF"

        ht_m = re.search(r"(?:total\s*ht|sous[- ]total|montant\s*ht|ht)\s*[:=]?\s*(\d+[.,]\d{2})", raw_text, re.IGNORECASE)
        tva_m = re.search(r"(?:tva|taxe|vat)[^\n\d]*?(\d+[.,]\d{2})", raw_text, re.IGNORECASE)
        ttc_m = re.search(r"(?:total\s*ttc|net\s*[àa]\s*payer|total|ttc)\s*[:=]?\s*(\d+[.,]\d{2})", raw_text, re.IGNORECASE)

        ht = self._parse_amount(ht_m.group(1)) if ht_m else None
        tva = self._parse_amount(tva_m.group(1)) if tva_m else None
        ttc = self._parse_amount(ttc_m.group(1)) if ttc_m else None

        items = []
        for l in lines:
            if any(k in l.lower() for k in ("total", "tva", "merci", "carte", "cb", "rendu")):
                continue
            im = re.match(r"^(.+?)\s+(\d+[.,]\d{2})\s*(?:€|eur|\$)?$", l, re.IGNORECASE)
            if im:
                p = self._parse_amount(im.group(2))
                if p is not None:
                    items.append({"description": im.group(1).strip(), "amount": p})

        # Vérification stricte de cohérence arithmétique
        inconsistencies = []
        if ht is not None and tva is not None and ttc is not None:
            expected_ttc = round(ht + tva, 2)
            if abs(expected_ttc - ttc) > 0.05:
                inconsistencies.append(f"Incohérence arithmétique : HT ({ht}) + TVA ({tva}) = {expected_ttc} != TTC ({ttc}).")
        elif ttc is None:
            inconsistencies.append("Montant TTC non détecté avec certitude.")

        if items and ttc is not None and ht is None:
            items_sum = round(sum(i["amount"] for i in items), 2)
            if abs(items_sum - ttc) > 0.15 and abs(items_sum - (ttc - (tva or 0.0))) > 0.15:
                inconsistencies.append(f"Somme des lignes ({items_sum}) différente du TTC ({ttc}).")

        validation_status = "VERIFIED" if (not inconsistencies and ttc is not None) else "NEEDS_MANUAL_REVIEW"

        return {
            "commercant": merchant,
            "date": date_val,
            "numero_facture": invoice_num,
            "devise": currency,
            "montant_ht": ht,
            "tva": tva,
            "montant_ttc": ttc,
            "lignes_achat": items,
            "validation_status": validation_status,
            "inconsistencies": inconsistencies,
            "raw_text_excerpt": raw_text[:400],
        }

    def process_receipt(
        self,
        image_path: str,
        owner_id: str,
        confirmed_save: bool = False,
        save_source_copy: bool = True,
    ) -> Dict[str, Any]:
        """Exécute OCR + extraction et n'enregistre jamais silencieusement un ticket incohérent."""
        t0 = time.perf_counter()
        raw_text = self.run_ocr(image_path)
        parsed = self.parse_receipt_text(raw_text)
        lat_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        OBSERVABILITY.record_latency("ocr_latency_ms", lat_ms)

        receipt_id = f"rcpt_{uuid.uuid4().hex[:10]}"
        parsed["receipt_id"] = receipt_id
        parsed["owner_id"] = owner_id
        parsed["provenance"] = os.path.basename(image_path) if save_source_copy else "source_purged"
        parsed["created_at"] = time.time()
        parsed["ocr_latency_ms"] = lat_ms

        # Si montant incertain ou incohérent et non confirmé manuellement -> PAS d'enregistrement définitif
        if parsed["validation_status"] != "VERIFIED" and not confirmed_save:
            parsed["saved"] = False
            return parsed

        with self._lock:
            parsed["saved"] = True
            self.receipts[receipt_id] = parsed
            self._save()
        return parsed

    def correct_and_save(self, receipt_data: Dict[str, Any], owner_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        rec = dict(receipt_data)
        for k in ("commercant", "date", "numero_facture", "devise", "montant_ht", "tva", "montant_ttc"):
            if k in updates:
                rec[k] = updates[k]
        rec["validation_status"] = "MANUALLY_VERIFIED"
        rec["inconsistencies"] = []
        rec["saved"] = True
        rec["owner_id"] = owner_id
        rid = rec.setdefault("receipt_id", f"rcpt_{uuid.uuid4().hex[:10]}")
        with self._lock:
            self.receipts[rid] = rec
            self._save()
        return rec

    def export_xlsx(self, owner_id: str, output_path: str) -> str:
        """Génère un vrai classeur Excel .xlsx natif sans dépendance tierce."""
        with self._lock:
            rows = [
                ["ID", "Date", "Commercant", "Facture", "HT", "TVA", "TTC", "Devise", "Statut", "Provenance"]
            ]
            for r in self.receipts.values():
                if r.get("owner_id") == owner_id or owner_id == "owner_local":
                    rows.append([
                        r.get("receipt_id", ""), r.get("date") or "", r.get("commercant") or "",
                        r.get("numero_facture") or "", str(r.get("montant_ht") or ""),
                        str(r.get("tva") or ""), str(r.get("montant_ttc") or ""),
                        r.get("devise") or "EUR", r.get("validation_status", ""), r.get("provenance", "")
                    ])

        # Construction OpenXML minimale conforme (xl/sharedStrings.xml + xl/worksheets/sheet1.xml)
        strings = []
        str_idx = {}

        def _s_id(s: str) -> int:
            if s not in str_idx:
                str_idx[s] = len(strings)
                strings.append(s)
            return str_idx[s]

        row_xml = []
        for r_i, row in enumerate(rows, 1):
            cells = []
            for c_i, val in enumerate(row):
                col = chr(65 + c_i)
                sid = _s_id(str(val))
                cells.append(f'<c r="{col}{r_i}" t="s"><v>{sid}</v></c>')
            row_xml.append(f'<row r="{r_i}">{"".join(cells)}</row>')

        si_xml = "".join(f"<si><t>{escape(s)}</t></si>" for s in strings)
        shared_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(strings)}" uniqueCount="{len(strings)}">{si_xml}</sst>'
        sheet_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(row_xml)}</sheetData></worksheet>'
        ct_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.sharedStrings+xml"/></Types>'
        rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        wb_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Tickets" sheetId="1" r:id="rId1"/></sheets></workbook>'
        wb_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>'

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ct_xml)
            z.writestr("_rels/.rels", rels_xml)
            z.writestr("xl/workbook.xml", wb_xml)
            z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
            z.writestr("xl/sharedStrings.xml", shared_xml)
            z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        return output_path


RECEIPT_OCR = SmartReceiptOCR()
