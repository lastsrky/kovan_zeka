#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 TEKNOFEST 2026 — AKILLI FABRİKA SİSTEMLERİ PROGRAMLAMA
🔍 DOKÜMANTASYON VE REVİZYON ARAMA MOTORU (arama_motoru.py)

Özellikler:
- %100 Çevrimdışı (Offline) & Sıfır Harici Kütüphane (Yalnızca Python Standard Library)
- Hem Terminalden (CLI / İnteraktif) hem Görsel Web Arayüzünden (UI) Çalışma
- Canlı Dosya İzleme (mtime takibi ile dosya düzenlendiğinde otomatik güncellenir)
- Çoklu Sonuç Sıralaması (Alaka puanına göre sıralanmış sonuç listesi)
- Kılavuz, Revizyon Bankası, Hakem Soruları ve Şartnameleri Tek Çatıda İndeksleme
"""

import sys
import os
import re
import json
import ast
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
import threading
import socket
from pathlib import Path

# Windows terminal UTF-8 ve ANSI renk desteği
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.system("")


# ==============================================================================
# 1. TÜRKÇE KARAKTER VE METİN NORMALİZASYONU
# ==============================================================================

TR_MAP = {
    'ç': 'c', 'Ç': 'c',
    'ğ': 'g', 'Ğ': 'g',
    'ı': 'i', 'I': 'i', 'İ': 'i', 'i': 'i',
    'ö': 'o', 'Ö': 'o',
    'ş': 's', 'Ş': 's',
    'ü': 'u', 'Ü': 'u',
}

def normalize_text(text: str) -> str:
    """Türkçe karakterleri ve büyük/küçük harf farklarını arama için normalize eder."""
    if not text:
        return ""
    res = []
    for ch in text:
        if ch in TR_MAP:
            res.append(TR_MAP[ch])
        else:
            res.append(ch.lower())
    return "".join(res)

def tokenize(text: str):
    """Metni arama kelimelerine böler."""
    norm = normalize_text(text)
    return set(re.findall(r'[a-z0-9_]{2,}', norm))

# ==============================================================================
# 2. VERİ YAPISI VE DÖKÜMAN AYRIŞTIRICILAR (PARSERS)
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent

class DocItem:
    def __init__(self, item_id: str, title: str, category: str, source_file: str,
                 instructions: str = "", target_file: str = "", target_line: str = "",
                 code_diff: str = "", test_cmd: str = "", presentation: str = "",
                 full_content: str = ""):
        self.item_id = item_id
        self.title = title
        self.category = category
        self.source_file = source_file
        self.instructions = instructions
        self.target_file = target_file
        self.target_line = target_line
        self.code_diff = code_diff
        self.test_cmd = test_cmd
        self.presentation = presentation
        self.full_content = full_content
        
        # Arama için önceden hesaplanan normalleştirilmiş alanlar
        self._norm_title = normalize_text(title)
        self._norm_instructions = normalize_text(instructions)
        self._norm_code = normalize_text(code_diff)
        self._norm_full = normalize_text(full_content)
        self._tokens_title = tokenize(title)
        self._tokens_all = tokenize(title + " " + instructions + " " + target_file + " " + full_content)

    def to_dict(self):
        return {
            "id": self.item_id,
            "title": self.title,
            "category": self.category,
            "source_file": self.source_file,
            "instructions": self.instructions,
            "target_file": self.target_file,
            "target_line": self.target_line,
            "code_diff": self.code_diff,
            "test_cmd": self.test_cmd,
            "presentation": self.presentation,
            "snippet": self.full_content[:350] + ("..." if len(self.full_content) > 350 else "")
        }

class DocumentIndexer:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.items = []
        self._file_mtimes = {}

    def needs_reload(self) -> bool:
        """İzlenen dosyaların değiştirilip değiştirilmediğini milisaniyede kontrol eder."""
        current_files = self._get_tracked_files()
        if set(current_files.keys()) != set(self._file_mtimes.keys()):
            return True
        for path, mtime in current_files.items():
            if self._file_mtimes.get(path) != mtime:
                return True
        return False

    def _get_tracked_files(self):
        files = {}
        target_patterns = [
            "*.md", "*/*.md",
            "otonomarac/*.py", "otonomarac/*.yaml", "otonomarac/*.yml",
            "robotkol/*.py",
            "plc/*.py", "plc/*.yaml",
            "simulasyon/*.py",
            "simulator/*.py", "simulator/*/*.py",
            "run_simulator.py", "simulasyon_baslat.py"
        ]
        for pattern in target_patterns:
            for p in self.base_dir.glob(pattern):
                if p.is_file() and "venv" not in p.parts and ".git" not in p.parts and "__pycache__" not in p.parts:
                    try:
                        files[str(p)] = p.stat().st_mtime
                    except OSError:
                        pass
        return files

    def reload_if_needed(self):
        if self.needs_reload() or not self.items:
            self.reload()

    def reload(self):
        """Tüm dökümanları ve kaynak kodları tarar ve kartlara ayrıştırır."""
        items = []
        self._file_mtimes = self._get_tracked_files()

        # Özel işlenecek dosyalar
        handled_paths = set()

        # 1. REVIZYON_SENARYO_BANKASI.md (Özel Ayrıştırma)
        rev_file = self.base_dir / "REVIZYON_SENARYO_BANKASI.md"
        if rev_file.exists():
            items.extend(self._parse_revizyon_bankasi(rev_file))
            handled_paths.add(str(rev_file.resolve()))

        # 2. ORNEK_HAKEM_SORULARI.md (Özel Ayrıştırma)
        hakem_file = self.base_dir / "ORNEK_HAKEM_SORULARI.md"
        if hakem_file.exists():
            items.extend(self._parse_hakem_sorulari(hakem_file))
            handled_paths.add(str(hakem_file.resolve()))

        # 3. KILAVUZ.md ve Diğer Tüm Markdown Dokümanları + Kaynak Kodlar (Dinamik Keşif)
        for path_str in self._file_mtimes.keys():
            p = Path(path_str)
            resolved = str(p.resolve())
            if resolved in handled_paths:
                continue

            # Markdown Dosyaları
            if p.suffix.lower() == ".md":
                fname = p.name.lower()
                if "kilavuz" in fname:
                    cat = "Kılavuz"
                elif "sartname" in fname:
                    cat = "Şartname"
                elif "hakem" in fname:
                    cat = "Hakem Soruları"
                elif "revizyon" in fname:
                    cat = "Revizyon"
                elif "project" in fname:
                    cat = "Proje Mimarisi"
                elif "docs" in p.parts:
                    cat = "Dokümantasyon"
                else:
                    cat = "Genel Bilgi"

                items.extend(self._parse_generic_markdown(p, cat))
                handled_paths.add(resolved)

            # Python Kaynak Kodları
            elif p.suffix.lower() == ".py" and p.name != "arama_motoru.py":
                items.extend(self._parse_python_source(p))
                handled_paths.add(resolved)

            # YAML Konfigürasyon Dosyaları
            elif p.suffix.lower() in [".yaml", ".yml"]:
                items.extend(self._parse_yaml_config(p))
                handled_paths.add(resolved)

        self.items = items

    def _parse_revizyon_bankasi(self, path: Path):
        items = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return items

        # ### `[REV-...] veya ### [REV-...] bloklarını yakala
        scenario_blocks = re.split(r'\n(?=###\s+.*REV-)', content)
        for block in scenario_blocks:
            if not ('REV-' in block and block.strip().startswith('###')):
                continue
            
            lines = block.strip().splitlines()
            header = lines[0].replace('###', '').replace('`', '').strip()
            
            # ID ve Başlık ayrıştırma
            match_id = re.search(r'\[(REV-[A-Z0-9ÇĞİÖŞÜ\-]+)\]\s*(.*)', header)
            item_id = match_id.group(1) if match_id else "REV"
            title = header

            # Kategori
            cat_match = re.search(r'\*\s*\*\*Kategori:\*\*\s*(.*)', block)
            category = "Revizyon"
            if cat_match:
                category = f"Revizyon ({cat_match.group(1).strip()})"

            # Hakemin Talimatı
            inst_match = re.search(r'####\s*1\.\s*🗣️\s*Hakemin Talimatı\s*\n+>?(.*?)(?=####|\Z)', block, re.DOTALL)
            instructions = inst_match.group(1).replace('>', '').strip() if inst_match else ""

            # Müdahale Edilecek Dosya ve Konum
            file_match = re.search(r'\*\s*\*\*Dosya:\*\*\s*\[?([^\n\]]+)', block)
            target_file = file_match.group(1).strip() if file_match else ""
            
            line_match = re.search(r'\*\s*\*\*Konum:\*\*\s*([^\n]+)', block)
            target_line = line_match.group(1).strip() if line_match else ""

            # Kod Bloğu (Diff)
            code_match = re.search(r'####\s*4\.\s*💻\s*Kod Değişikliği[^\n]*\n+```[a-z]*\n(.*?)```', block, re.DOTALL)
            code_diff = code_match.group(1).strip() if code_match else ""

            # Test Komutu
            test_match = re.search(r'####\s*5\.\s*⏱️\s*30 Saniyelik[^\n]*\n+```bash\n(.*?)```', block, re.DOTALL)
            test_cmd = test_match.group(1).strip() if test_match else ""

            # Hakem Sunum Cümlesi
            pres_match = re.search(r'####\s*6\.\s*🏆\s*Hakeme Sunum Cümlesi\s*\n+>?(.*?)(?=---|###|\Z)', block, re.DOTALL)
            presentation = pres_match.group(1).replace('>', '').strip() if pres_match else ""

            item = DocItem(
                item_id=item_id,
                title=title,
                category=category,
                source_file="REVIZYON_SENARYO_BANKASI.md",
                instructions=instructions,
                target_file=target_file,
                target_line=target_line,
                code_diff=code_diff,
                test_cmd=test_cmd,
                presentation=presentation,
                full_content=block
            )
            items.append(item)
        return items

    def _parse_hakem_sorulari(self, path: Path):
        items = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return items

        # ## 2. HAKEM SENARYOSU vb. bloklar
        sections = re.split(r'\n(?=##\s+\d+\.\s+HAKEM SENARYOSU)', content)
        for i, sec in enumerate(sections):
            if not re.search(r'##\s+\d+\.\s+HAKEM SENARYOSU', sec):
                continue
            lines = sec.strip().splitlines()
            title = lines[0].replace('##', '').strip()
            item_id = f"HAKEM-TALEP-0{i}"

            # Talimat
            inst_match = re.search(r'###\s*.*Hakemin Birebir Ağzından Çıkan Talimat\s*\n+>?(.*?)(?=###|---|##|\Z)', sec, re.DOTALL)
            instructions = inst_match.group(1).replace('>', '').strip() if inst_match else ""

            # Dosya / Parametre
            file_match = re.search(r'otonomarac/config\.yaml', sec)
            target_file = "otonomarac/config.yaml" if file_match else ""

            # Kod / YAML Değişikliği
            code_match = re.search(r'```yaml\n(.*?)```', sec, re.DOTALL)
            code_diff = code_match.group(1).strip() if code_match else ""

            # Test Komutu
            test_match = re.search(r'```bash\n(.*?)```', sec, re.DOTALL)
            test_cmd = test_match.group(1).strip() if test_match else ""

            item = DocItem(
                item_id=item_id,
                title=title,
                category="Hakem Soruları & Senaryoları",
                source_file="ORNEK_HAKEM_SORULARI.md",
                instructions=instructions,
                target_file=target_file,
                target_line="config.yaml",
                code_diff=code_diff,
                test_cmd=test_cmd,
                presentation=instructions,
                full_content=sec
            )
            items.append(item)
        return items

    def _parse_generic_markdown(self, path: Path, default_cat: str):
        items = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return items

        # Dosyayı ## veya ### başlıklarına göre mantıksal kartlara ayır
        sections = re.split(r'\n(?=##+\s+)', content)
        rel_name = path.name
        for i, sec in enumerate(sections):
            sec_clean = sec.strip()
            if not sec_clean or len(sec_clean) < 30:
                continue
            lines = sec_clean.splitlines()
            first_line = lines[0].strip()
            title = re.sub(r'^#+\s*', '', first_line).strip()
            
            if title.lower() in ["i̇çindekiler", "icindekiler", "table of contents"]:
                continue

            # Kod bloğu var mı?
            code_match = re.search(r'```[a-z]*\n(.*?)```', sec_clean, re.DOTALL)
            code_snippet = code_match.group(1).strip() if code_match else ""

            item = DocItem(
                item_id=f"{path.stem.upper()}-{i+1}",
                title=f"{path.stem.replace('_', ' ')}: {title}",
                category=default_cat,
                source_file=rel_name,
                instructions="",
                target_file=rel_name,
                target_line="",
                code_diff=code_snippet,
                test_cmd="",
                presentation="",
                full_content=sec_clean
            )
            items.append(item)
        return items

    def _parse_python_source(self, path: Path):
        items = []
        try:
            rel_path = str(path.relative_to(self.base_dir)).replace("\\", "/")
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
        except Exception:
            return items

        # Kategori
        if "otonomarac" in rel_path:
            cat = "Kaynak Kod (Otonom Araç)"
        elif "robotkol" in rel_path:
            cat = "Kaynak Kod (Robot Kol)"
        elif "plc" in rel_path:
            cat = "Kaynak Kod (PLC)"
        elif "simulator" in rel_path or "simulasyon" in rel_path:
            cat = "Kaynak Kod (Simülatör)"
        else:
            cat = "Kaynak Kod"

        # AST ile sınıfları ve fonksiyonları tara
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = node.name
                    if name.startswith("__") and name != "__init__":
                        continue
                    
                    line_start = node.lineno
                    line_end = getattr(node, "end_lineno", min(len(lines), line_start + 25))
                    doc = ast.get_docstring(node) or ""
                    
                    snippet_lines = lines[line_start - 1 : min(line_end, line_start + 22)]
                    snippet = "\n".join(snippet_lines)
                    
                    kind = "class" if isinstance(node, ast.ClassDef) else "def"
                    title = f"{rel_path}: {kind} {name}"
                    
                    item = DocItem(
                        item_id=f"CODE-{path.stem}-{name}-L{line_start}",
                        title=title,
                        category=cat,
                        source_file=rel_path,
                        instructions=f"Tanım: {kind} {name}() | Dosya: {rel_path} (Satır {line_start})" + (f"\nAçıklama: {doc}" if doc else ""),
                        target_file=rel_path,
                        target_line=f"Satır {line_start}",
                        code_diff=snippet,
                        test_cmd=f"python -m py_compile {rel_path}",
                        presentation="",
                        full_content=snippet + " " + doc
                    )
                    items.append(item)
        except Exception:
            # AST başarısız olursa regex fallback
            for i, line in enumerate(lines):
                m = re.match(r'^(?:async\s+)?(def|class)\s+([a-zA-Z0-9_]+)', line.strip())
                if m:
                    kind, name = m.group(1), m.group(2)
                    snippet = "\n".join(lines[i : min(len(lines), i + 20)])
                    items.append(DocItem(
                        item_id=f"CODE-{path.stem}-{name}-L{i+1}",
                        title=f"{rel_path}: {kind} {name}",
                        category=cat,
                        source_file=rel_path,
                        instructions=f"{kind} {name} (Satır {i+1})",
                        target_file=rel_path,
                        target_line=f"Satır {i+1}",
                        code_diff=snippet,
                        test_cmd=f"python -m py_compile {rel_path}",
                        presentation="",
                        full_content=snippet
                    ))
        return items

    def _parse_yaml_config(self, path: Path):
        items = []
        try:
            rel_path = str(path.relative_to(self.base_dir)).replace("\\", "/")
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
        except Exception:
            return items

        curr_section = None
        curr_lines = []
        start_line = 1

        for i, line in enumerate(lines):
            m = re.match(r'^([a-zA-Z0-9_]+)\s*:', line)
            if m and not line.startswith(" "):
                if curr_section and curr_lines:
                    snippet = "\n".join(curr_lines[:30])
                    items.append(DocItem(
                        item_id=f"CONF-{path.stem}-{curr_section}-L{start_line}",
                        title=f"{rel_path}: [{curr_section}] Parametre Bloğu",
                        category="Konfigürasyon (YAML)",
                        source_file=rel_path,
                        instructions=f"{rel_path} içerisindeki '{curr_section}' ayar bloğu (Satır {start_line})",
                        target_file=rel_path,
                        target_line=f"Satır {start_line}",
                        code_diff=snippet,
                        test_cmd="",
                        presentation="",
                        full_content=snippet
                    ))
                curr_section = m.group(1)
                curr_lines = [line]
                start_line = i + 1
            else:
                if curr_section:
                    curr_lines.append(line)

        if curr_section and curr_lines:
            snippet = "\n".join(curr_lines[:30])
            items.append(DocItem(
                item_id=f"CONF-{path.stem}-{curr_section}-L{start_line}",
                title=f"{rel_path}: [{curr_section}] Parametre Bloğu",
                category="Konfigürasyon (YAML)",
                source_file=rel_path,
                instructions=f"{rel_path} içerisindeki '{curr_section}' ayar bloğu (Satır {start_line})",
                target_file=rel_path,
                target_line=f"Satır {start_line}",
                code_diff=snippet,
                test_cmd="",
                presentation="",
                full_content=snippet
            ))

        return items

# ==============================================================================
# 3. ARAMA MOTORU VE ALAKA PUANLAMA (SEARCH & RANKING)
# ==============================================================================

class SearchEngine:
    def __init__(self, indexer: DocumentIndexer):
        self.indexer = indexer

    def search(self, query: str, category_filter: str = "Tümü", limit: int = 15):
        self.indexer.reload_if_needed()
        
        q_norm = normalize_text(query.strip())
        if not q_norm:
            return []

        q_tokens = tokenize(q_norm)
        if not q_tokens:
            q_tokens = {q_norm}

        scored_results = []

        for item in self.indexer.items:
            # Kategori Filtresi
            if category_filter != "Tümü":
                if category_filter.lower() not in item.category.lower():
                    continue

            score = 0

            # 1. Başlıkta Birebir Tam İfade Eşleşmesi (En Yüksek Puan)
            if q_norm in item._norm_title:
                score += 80
            
            # 2. Hakem Talimatında veya Açıklamada Tam İfade
            if q_norm in item._norm_instructions:
                score += 50

            # 3. Kod Bloğu / Diff İçinde Tam İfade
            if q_norm in item._norm_code:
                score += 35

            # 4. Genel Metinde Tam İfade
            if q_norm in item._norm_full:
                score += 20

            # 5. Kelime Kapsama Puanlaması (Her sorgu kelimesi için)
            matched_tokens = 0
            for t in q_tokens:
                if t in item._tokens_title:
                    score += 25
                    matched_tokens += 1
                elif t in item._tokens_all:
                    score += 8
                    matched_tokens += 1

            # Eğer tüm sorgu kelimeleri kartta geçiyorsa ekstra bonus
            if len(q_tokens) > 1 and matched_tokens == len(q_tokens):
                score += 30

            # Revizyon Önceliği Bonusu (Sadece eşleşme varsa eklenir)
            if score > 0:
                if "revizyon" in item.category.lower():
                    score += 5
                scored_results.append((score, item))

        # Puana göre çoktan aza sırala
        scored_results.sort(key=lambda x: x[0], reverse=True)

        results = []
        for rank, (sc, itm) in enumerate(scored_results[:limit], 1):
            d = itm.to_dict()
            d["score"] = sc
            d["rank"] = rank
            results.append(d)

        return results

# ==============================================================================
# 4. TERMİNAL / CLI ARAYÜZÜ
# ==============================================================================

# ANSI Renk Kodları (Terminal için)
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_GRAY = "\033[90m"

def print_cli_banner():
    print(f"\n{C_CYAN}{C_BOLD}======================================================================{C_RESET}")
    print(f"{C_YELLOW}{C_BOLD} 🏆 TEKNOFEST 2026 — AKILLI FABRİKA DOKÜMANTASYON & REVİZYON ARAMA MOTORU{C_RESET}")
    print(f"{C_GRAY} Tamamen Yerel • Sıfır Harici Kütüphane • Canlı İndeksleme{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}======================================================================{C_RESET}\n")

def display_cli_results(query: str, results: list):
    if not results:
        print(f"{C_RED}❌ '{query}' ile ilgili herhangi bir eşleşme bulunamadı.{C_RESET}")
        print(f"{C_GRAY}İpucu: 'mavi', 'hız', 'ıskarta', 'trafik', 'pid', 'konveyör' gibi anahtar kelimeler deneyin.{C_RESET}\n")
        return

    top = results[0]
    total = len(results)

    print(f"{C_GREEN}{C_BOLD}🎯 TOPLAM {total} SONUÇ BULUNDU. (EN ALAKALI SONUÇ ÖNE ÇIKARILDI):{C_RESET}\n")
    
    # 1. En Alakalı Kart
    print(f"{C_CYAN}┌────────────────────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}│{C_RESET} {C_YELLOW}{C_BOLD}[#1 EN YÜKSEK ALAKA] {top['title']}{C_RESET}")
    print(f"{C_CYAN}│{C_RESET} {C_GRAY}Kategori: {top['category']} | Kaynak: {top['source_file']}{C_RESET}")
    print(f"{C_CYAN}├────────────────────────────────────────────────────────────────────────┘{C_RESET}")

    if top.get("target_file"):
        print(f"  {C_BOLD}📂 Değiştirilecek Dosya:{C_RESET} {C_GREEN}{top['target_file']}{C_RESET} {C_YELLOW}({top.get('target_line', '')}){C_RESET}")

    if top.get("instructions"):
        print(f"\n  {C_BOLD}🗣️ Hakem Talimatı:{C_RESET}\n  {C_GRAY}\"{top['instructions']}\"{C_RESET}")

    if top.get("code_diff"):
        print(f"\n  {C_BOLD}💻 Hazır Kod Değişikliği (Diff):{C_RESET}")
        for line in top["code_diff"].splitlines()[:15]:
            if line.startswith("+") or "YENİ KOD" in line:
                print(f"    {C_GREEN}{line}{C_RESET}")
            elif line.startswith("-") or "ESKİ KOD" in line:
                print(f"    {C_RED}{line}{C_RESET}")
            else:
                print(f"    {C_GRAY}{line}{C_RESET}")
        if len(top["code_diff"].splitlines()) > 15:
            print(f"    {C_GRAY}... (devamı arayüzde veya dosyada){C_RESET}")

    if top.get("test_cmd"):
        print(f"\n  {C_BOLD}⏱️ Hızlı Test Komutu:{C_RESET}")
        print(f"    {C_CYAN}{top['test_cmd']}{C_RESET}")

    if top.get("presentation"):
        print(f"\n  {C_BOLD}🏆 Hakeme Sunum Cümlesi:{C_RESET}")
        print(f"    {C_YELLOW}\"{top['presentation']}\"{C_RESET}")

    # 2. Diğer Alternatif Sonuçlar
    if total > 1:
        print(f"\n{C_BOLD}📑 DİĞER OLASI EŞLEŞMELER:{C_RESET}")
        for res in results[1:6]:
            print(f"  {C_CYAN}• [#{res['rank']} - Puan: {res['score']}]{C_RESET} {C_BOLD}{res['title']}{C_RESET}")
            print(f"    {C_GRAY}Kaynak: {res['source_file']} | Kategori: {res['category']}{C_RESET}")
            if res.get("target_file"):
                print(f"    {C_GRAY}Hedef Dosya: {res['target_file']}{C_RESET}")
    print()

def run_cli_mode(engine: SearchEngine, initial_query: str = None, interactive: bool = False):
    print_cli_banner()
    if initial_query:
        res = engine.search(initial_query)
        display_cli_results(initial_query, res)
        if not interactive:
            return

    try:
        while True:
            q = input(f"{C_YELLOW}{C_BOLD}Arama Terimi (Çıkmak için 'q') > {C_RESET}").strip()
            if not q or q.lower() in ['q', 'exit', 'cikis', 'quit']:
                print(f"{C_GREEN}Arama motorundan çıkıldı.{C_RESET}")
                break
            res = engine.search(q)
            display_cli_results(q, res)
    except (KeyboardInterrupt, EOFError):
        print(f"\n{C_GREEN}Görüşmek üzere.{C_RESET}")

# ==============================================================================
# 5. GÖRSEL WEB ARAYÜZÜ (WEB UI)
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arama Motoru — TEKNOFEST Akıllı Fabrika</title>
    <style>
        :root {
            --bg-main: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #24344d;
            --border: #334155;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.15);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --green: #22c55e;
            --red: #ef4444;
            --yellow: #eab308;
            --purple: #a855f7;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }
        body { background: var(--bg-main); color: var(--text-main); min-height: 100vh; padding: 24px 16px; }
        .container { max-width: 1050px; margin: 0 auto; }

        /* HEADER */
        .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
        .logo-area { display: flex; align-items: center; gap: 12px; }
        .logo-badge { background: linear-gradient(135deg, #0284c7, #2563eb); color: #fff; font-weight: 800; font-size: 14px; padding: 6px 12px; border-radius: 8px; letter-spacing: 0.5px; }
        .title-text h1 { font-size: 20px; font-weight: 700; color: #fff; }
        .title-text p { font-size: 12px; color: var(--text-muted); }
        .status-badge { font-size: 12px; color: var(--green); background: rgba(34, 197, 94, 0.1); padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(34, 197, 94, 0.2); }

        /* SEARCH BOX */
        .search-wrapper { position: relative; margin-bottom: 16px; }
        .search-input {
            width: 100%;
            background: var(--bg-card);
            border: 2px solid var(--border);
            color: var(--text-main);
            font-size: 16px;
            padding: 16px 20px 16px 48px;
            border-radius: 12px;
            outline: none;
            transition: all 0.2s ease;
        }
        .search-input:focus { border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-glow); }
        .search-icon { position: absolute; left: 18px; top: 18px; color: var(--text-muted); font-size: 18px; }

        /* CATEGORY FILTER TABS */
        .tabs { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 20px; }
        .tab-btn {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.15s;
        }
        .tab-btn:hover { background: var(--bg-card-hover); color: #fff; }
        .tab-btn.active { background: var(--accent); color: #0f172a; font-weight: 700; border-color: var(--accent); }

        /* QUICK SUGGESTIONS */
        .suggestions { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; font-size: 12px; align-items: center; color: var(--text-muted); }
        .tag-pill { background: rgba(56, 189, 248, 0.1); color: var(--accent); padding: 3px 8px; border-radius: 6px; cursor: pointer; border: 1px solid rgba(56, 189, 248, 0.2); }
        .tag-pill:hover { background: rgba(56, 189, 248, 0.2); }

        /* RESULTS AREA */
        .results-meta { font-size: 13px; color: var(--text-muted); margin-bottom: 14px; display: flex; justify-content: space-between; }
        .cards-list { display: flex; flex-direction: column; gap: 14px; }

        /* RESULT CARD */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 18px;
            transition: border-color 0.2s;
        }
        .card:hover { border-color: #475569; }
        .card.top-hit { border-color: var(--accent); background: linear-gradient(180deg, rgba(56, 189, 248, 0.05), var(--bg-card) 40%); }

        .card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
        .card-badges { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
        .badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; text-transform: uppercase; }
        .badge-rev { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge-hakem { background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }
        .badge-kilavuz { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
        .badge-file { background: rgba(148, 163, 184, 0.1); color: #cbd5e1; font-family: monospace; }
        .badge-score { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
        .badge-code { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
        .badge-conf { background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }

        .card-title { font-size: 16px; font-weight: 700; color: #fff; line-height: 1.4; }
        
        .target-box {
            background: rgba(15, 23, 42, 0.6);
            border-left: 3px solid var(--accent);
            padding: 10px 14px;
            border-radius: 0 8px 8px 0;
            margin: 12px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-family: monospace;
            font-size: 13px;
        }
        .target-path { color: var(--green); font-weight: 600; }
        .target-line { color: var(--yellow); }

        .instruction-box {
            background: rgba(30, 41, 59, 0.7);
            border-left: 3px solid var(--yellow);
            padding: 10px 14px;
            border-radius: 0 8px 8px 0;
            margin: 10px 0;
            font-size: 13px;
            color: #cbd5e1;
            line-height: 1.5;
        }

        .code-container { position: relative; margin: 12px 0; }
        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #090d16;
            padding: 6px 12px;
            border-radius: 8px 8px 0 0;
            border: 1px solid #1e293b;
            border-bottom: none;
            font-size: 11px;
            color: var(--text-muted);
        }
        pre.code-block {
            background: #090d16;
            border: 1px solid #1e293b;
            border-radius: 0 0 8px 8px;
            padding: 12px;
            overflow-x: auto;
            font-family: "JetBrains Mono", Consolas, Menlo, monospace;
            font-size: 12px;
            color: #e2e8f0;
            line-height: 1.45;
            max-height: 280px;
        }

        .copy-btn {
            background: var(--border);
            color: #fff;
            border: none;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.15s;
        }
        .copy-btn:hover { background: var(--accent); color: #0f172a; font-weight: 700; }

        .defense-box {
            background: rgba(234, 179, 8, 0.08);
            border: 1px solid rgba(234, 179, 8, 0.2);
            border-radius: 8px;
            padding: 10px 14px;
            margin: 10px 0;
            font-size: 13px;
            color: #fef08a;
            line-height: 1.4;
        }
        .defense-label { font-size: 11px; font-weight: 800; color: #facc15; text-transform: uppercase; margin-bottom: 4px; }

        .empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); }
        .empty-state h3 { color: #fff; margin-bottom: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <div class="logo-area">
                <span class="logo-badge">TEKNOFEST 2026</span>
                <div class="title-text">
                    <h1>Arama Motoru</h1>
                    <p>Akıllı Fabrika Dokümantasyon, Kılavuz & Revizyon Bilgi Tabanı</p>
                </div>
            </div>
            <div class="status-badge">● Çevrimdışı & Canlı İndeks</div>
        </div>

        <!-- SEARCH INPUT -->
        <div class="search-wrapper">
            <span class="search-icon">🔍</span>
            <input type="text" id="searchInput" class="search-input" placeholder="Revizyon, parametre veya konu arayın (örn: mavi küp, araç hız, mqtt, pid, plc)..." autofocus autocomplete="off">
        </div>

        <!-- FILTER TABS -->
        <div class="tabs">
            <button class="tab-btn active" onclick="setCategory('Tümü')">Tümü</button>
            <button class="tab-btn" onclick="setCategory('Revizyon')">🚨 Revizyon Bankası (34)</button>
            <button class="tab-btn" onclick="setCategory('Hakem')">🗣️ Hakem Soruları</button>
            <button class="tab-btn" onclick="setCategory('Kılavuz')">📘 Kılavuz & Donanım</button>
            <button class="tab-btn" onclick="setCategory('Şartname')">📋 Şartname</button>
            <button class="tab-btn" onclick="setCategory('Kaynak Kod')">💻 Kaynak Kod (Python)</button>
            <button class="tab-btn" onclick="setCategory('Konfigürasyon')">⚙️ YAML Parametreleri</button>
        </div>

        <!-- QUICK PILLS -->
        <div class="suggestions">
            <span>Hızlı Arama:</span>
            <span class="tag-pill" onclick="quickSearch('mavi küp ıskarta')">mavi küp ıskarta</span>
            <span class="tag-pill" onclick="quickSearch('viraj hız düşür')">viraj hız düşür</span>
            <span class="tag-pill" onclick="quickSearch('camera exposure')">camera exposure (kod)</span>
            <span class="tag-pill" onclick="quickSearch('pid osilasyon')">pid osilasyon</span>
            <span class="tag-pill" onclick="quickSearch('renk_algila')">renk_algila (fonksiyon)</span>
            <span class="tag-pill" onclick="quickSearch('mqtt topic')">mqtt topic</span>
            <span class="tag-pill" onclick="quickSearch('plc sayaç duruş')">plc sayaç duruş</span>
        </div>

        <!-- META -->
        <div class="results-meta">
            <span id="resultsCount">Aramak için yukarıya bir kelime yazın.</span>
            <span id="updateTime">Canlı Dosya Takibi Aktif</span>
        </div>

        <!-- RESULTS -->
        <div id="resultsList" class="cards-list"></div>
    </div>

    <script>
        let currentCategory = "Tümü";
        let debounceTimer;

        const input = document.getElementById("searchInput");
        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(doSearch, 120);
        });

        function setCategory(cat) {
            currentCategory = cat;
            document.querySelectorAll(".tab-btn").forEach(btn => {
                btn.classList.toggle("active", btn.innerText.includes(cat));
            });
            doSearch();
        }

        function quickSearch(text) {
            input.value = text;
            doSearch();
        }

        async function doSearch() {
            const q = input.value.trim();
            if (!q) {
                document.getElementById("resultsList").innerHTML = `
                    <div class="empty-state">
                        <h3>Arama Yapmaya Başlayın</h3>
                        <p>Hakemin istediği revizyonu, bir kuralı veya bir dosya/parametre adını yazın.</p>
                    </div>`;
                document.getElementById("resultsCount").innerText = "";
                return;
            }

            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&cat=${encodeURIComponent(currentCategory)}`);
                const data = await res.json();
                renderResults(data);
            } catch (err) {
                console.error("Arama hatası:", err);
            }
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }

        function copyText(text, btn) {
            navigator.clipboard.writeText(text).then(() => {
                const old = btn.innerText;
                btn.innerText = "✓ Kopyalandı!";
                setTimeout(() => { btn.innerText = old; }, 1500);
            });
        }

        function renderResults(results) {
            const list = document.getElementById("resultsList");
            const countLabel = document.getElementById("resultsCount");

            if (!results || results.length === 0) {
                countLabel.innerText = "Eşleşen sonuç bulunamadı.";
                list.innerHTML = `
                    <div class="empty-state">
                        <h3>Sonuç Bulunamadı</h3>
                        <p>Farklı bir anahtar kelime deneyin veya kategori filtresini 'Tümü' yapın.</p>
                    </div>`;
                return;
            }

            countLabel.innerText = `${results.length} sonuç bulundu (alaka sırasına göre)`;
            
            list.innerHTML = results.map((item, idx) => {
                const isTop = idx === 0;
                let badgeClass = "badge-rev";
                if (item.category.includes("Hakem")) badgeClass = "badge-hakem";
                else if (item.category.includes("Kılavuz")) badgeClass = "badge-kilavuz";
                else if (item.category.includes("Şartname")) badgeClass = "badge-score";
                else if (item.category.includes("Kaynak Kod")) badgeClass = "badge-code";
                else if (item.category.includes("Konfigürasyon")) badgeClass = "badge-conf";

                let html = `
                <div class="card ${isTop ? 'top-hit' : ''}">
                    <div class="card-header">
                        <div>
                            <div class="card-badges">
                                <span class="badge ${badgeClass}">${escapeHtml(item.category)}</span>
                                <span class="badge badge-file">${escapeHtml(item.source_file)}</span>
                                <span class="badge badge-score">Skor: ${item.score}</span>
                                ${isTop ? '<span class="badge" style="background:#0284c7;color:#fff;">★ En İyi Eşleşme</span>' : ''}
                            </div>
                            <h2 class="card-title">${escapeHtml(item.title)}</h2>
                        </div>
                    </div>`;

                if (item.target_file) {
                    html += `
                    <div class="target-box">
                        <div>
                            <span>📂 Hedef Dosya: </span>
                            <span class="target-path">${escapeHtml(item.target_file)}</span>
                            ${item.target_line ? `<span class="target-line">(${escapeHtml(item.target_line)})</span>` : ''}
                        </div>
                        <button class="copy-btn" onclick="copyText('${escapeHtml(item.target_file)}', this)">Dosya Adını Kopyala</button>
                    </div>`;
                }

                if (item.instructions) {
                    html += `
                    <div class="instruction-box">
                        <strong>🗣️ Hakem Talimatı:</strong>
                        <div>"${escapeHtml(item.instructions)}"</div>
                    </div>`;
                }

                if (item.code_diff) {
                    html += `
                    <div class="code-container">
                        <div class="code-header">
                            <span>💻 Kod Değişikliği / Diff</span>
                            <button class="copy-btn" onclick="copyText(decodeURIComponent('${encodeURIComponent(item.code_diff)}'), this)">📋 Kodu Kopyala</button>
                        </div>
                        <pre class="code-block"><code>${escapeHtml(item.code_diff)}</code></pre>
                    </div>`;
                }

                if (item.test_cmd) {
                    html += `
                    <div class="code-container">
                        <div class="code-header">
                            <span>⏱️ 30 Saniyelik Hızlı Test Komutu</span>
                            <button class="copy-btn" onclick="copyText(decodeURIComponent('${encodeURIComponent(item.test_cmd)}'), this)">📋 Komutu Kopyala</button>
                        </div>
                        <pre class="code-block" style="max-height:80px;"><code>${escapeHtml(item.test_cmd)}</code></pre>
                    </div>`;
                }

                if (item.presentation) {
                    html += `
                    <div class="defense-box">
                        <div class="defense-label">🏆 Hakeme Sunulacak Profesyonel Açıklama</div>
                        <div>"${escapeHtml(item.presentation)}"</div>
                    </div>`;
                }

                if (!item.code_diff && !item.instructions && item.snippet) {
                    html += `
                    <div style="font-size:13px; color:#94a3b8; line-height:1.5; margin-top:8px;">
                        ${escapeHtml(item.snippet)}
                    </div>`;
                }

                html += `</div>`;
                return html;
            }).join("");
        }

        // Sayfa açıldığında boş kalmaması için popüler bir arama önerisi ile başlat
        window.addEventListener("load", () => {
            quickSearch("mavi küp ıskarta");
        });
    </script>
</body>
</html>
"""

class SearchHTTPHandler(BaseHTTPRequestHandler):
    engine = None

    def log_message(self, format, *args):
        # Konsolu gereksiz HTTP loglarıyla boğmamak için sessiz tut
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        elif path == "/api/search":
            qs = urllib.parse.parse_qs(parsed.query)
            query = qs.get("q", [""])[0]
            cat = qs.get("cat", ["Tümü"])[0]

            results = self.engine.search(query, category_filter=cat)
            
            payload = json.dumps(results, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
            return

        else:
            self.send_response(404)
            self.end_headers()

def run_web_ui(engine: SearchEngine, port: int = 8080):
    SearchHTTPHandler.engine = engine

    # Boş bir port bul
    chosen_port = port
    while True:
        try:
            server = HTTPServer(("127.0.0.1", chosen_port), SearchHTTPHandler)
            break
        except OSError:
            chosen_port += 1

    url = f"http://127.0.0.1:{chosen_port}"
    print(f"\n{C_GREEN}{C_BOLD}🚀 Arama Motoru Arayüzü Başlatıldı!{C_RESET}")
    print(f"🔗 Tarayıcı adresi: {C_CYAN}{C_BOLD}{url}{C_RESET}")
    print(f"{C_GRAY}(Durdurmak için terminalde Ctrl + C tuşlayın){C_RESET}\n")

    # Tarayıcıyı otomatik aç
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}Arama motoru sunucusu durduruldu.{C_RESET}")
        server.server_close()

# ==============================================================================
# 6. ANA ÇALIŞTIRMA NOKTASI (ENTRYPOINT)
# ==============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="TEKNOFEST Akıllı Fabrika Dokümantasyon & Revizyon Arama Motoru")
    parser.add_argument("query", nargs="?", default=None, help="Aranacak anahtar kelime veya revizyon cümlesi")
    parser.add_argument("-i", "--cli", action="store_true", help="İnteraktif terminal arama modunu başlat")
    parser.add_argument("--ui", action="store_true", help="Web tarayıcı arayüzünü başlat")
    parser.add_argument("--port", type=int, default=8080, help="Web UI portu (Varsayılan: 8080)")

    args = parser.parse_args()

    # İndeksleyiciyi başlat
    indexer = DocumentIndexer(BASE_DIR)
    engine = SearchEngine(indexer)

    # 1. Eğer doğrudan arama sorgusu verildiyse terminale yazdır
    if args.query:
        run_cli_mode(engine, initial_query=args.query, interactive=args.cli)
    # 2. Eğer --cli parametresi verildiyse interaktif terminal modunu başlat
    elif args.cli:
        run_cli_mode(engine, interactive=True)
    # 3. Parametresiz çalıştırıldıysa veya --ui istendiyse web arayüzünü aç
    else:
        run_web_ui(engine, port=args.port)

if __name__ == "__main__":
    main()
