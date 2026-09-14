#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 TEKNOFEST 2026 — AKILLI FABRİKA SİSTEMLERİ PROGRAMLAMA
🌐 STATİK WEB SİTESİ DERLEYİCİSİ (build_static_site.py)

Bu script, arama motorundaki tüm verileri (34 revizyon, kılavuz, hakem soruları, kaynak kodlar)
herhangi bir sunucuya ihtiyaç duymadan GitHub Pages'te veya herhangi bir web hosting'de
çalışabilen tek parça bağımsız bir 'index.html' dosyasına dönüştürür.
"""

import json
from pathlib import Path
from arama_motoru import DocumentIndexer, BASE_DIR

def build():
    print("📦 Dokümanlar ve kaynak kodlar indeksleniyor...")
    idx = DocumentIndexer(BASE_DIR)
    idx.reload()
    items = [item.to_dict() for item in idx.items]
    print(f"✓ Toplam {len(items)} adet kart hazırlandı.")

    db_json = json.dumps(items, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TEKNOFEST 2026 — Dokümantasyon & Revizyon Arama Motoru</title>
    <meta name="description" content="TEKNOFEST 2026 Akıllı Fabrika Sistemleri Programlama Saha Arama Motoru ve Revizyon Rehberi">
    <style>
        :root {{
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
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }}
        body {{ background: var(--bg-main); color: var(--text-main); min-height: 100vh; padding: 24px 16px; }}
        .container {{ max-width: 1050px; margin: 0 auto; }}

        /* HEADER */
        .header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }}
        .logo-area {{ display: flex; align-items: center; gap: 12px; }}
        .logo-badge {{ background: linear-gradient(135deg, #0284c7, #2563eb); color: #fff; font-weight: 800; font-size: 14px; padding: 6px 12px; border-radius: 8px; letter-spacing: 0.5px; }}
        .title-text h1 {{ font-size: 20px; font-weight: 700; color: #fff; }}
        .title-text p {{ font-size: 12px; color: var(--text-muted); }}
        .status-badge {{ font-size: 12px; color: var(--green); background: rgba(34, 197, 94, 0.1); padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(34, 197, 94, 0.2); }}

        /* SEARCH BOX */
        .search-wrapper {{ position: relative; margin-bottom: 16px; }}
        .search-input {{
            width: 100%;
            background: var(--bg-card);
            border: 2px solid var(--border);
            color: var(--text-main);
            font-size: 16px;
            padding: 16px 20px 16px 48px;
            border-radius: 12px;
            outline: none;
            transition: all 0.2s ease;
        }}
        .search-input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-glow); }}
        .search-icon {{ position: absolute; left: 18px; top: 18px; color: var(--text-muted); font-size: 18px; }}

        /* CATEGORY FILTER TABS */
        .tabs {{ display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 20px; }}
        .tab-btn {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.15s;
        }}
        .tab-btn:hover {{ background: var(--bg-card-hover); color: #fff; }}
        .tab-btn.active {{ background: var(--accent); color: #0f172a; font-weight: 700; border-color: var(--accent); }}

        /* QUICK SUGGESTIONS */
        .suggestions {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; font-size: 12px; align-items: center; color: var(--text-muted); }}
        .tag-pill {{ background: rgba(56, 189, 248, 0.1); color: var(--accent); padding: 3px 8px; border-radius: 6px; cursor: pointer; border: 1px solid rgba(56, 189, 248, 0.2); }}
        .tag-pill:hover {{ background: rgba(56, 189, 248, 0.2); }}

        /* RESULTS AREA */
        .results-meta {{ font-size: 13px; color: var(--text-muted); margin-bottom: 14px; display: flex; justify-content: space-between; }}
        .cards-list {{ display: flex; flex-direction: column; gap: 14px; }}

        /* RESULT CARD */
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 18px;
            transition: border-color 0.2s;
        }}
        .card:hover {{ border-color: #475569; }}
        .card.top-hit {{ border-color: var(--accent); background: linear-gradient(180deg, rgba(56, 189, 248, 0.05), var(--bg-card) 40%); }}

        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }}
        .card-badges {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }}
        .badge {{ font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; text-transform: uppercase; }}
        .badge-rev {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
        .badge-hakem {{ background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }}
        .badge-kilavuz {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
        .badge-file {{ background: rgba(148, 163, 184, 0.1); color: #cbd5e1; font-family: monospace; }}
        .badge-score {{ background: rgba(34, 197, 94, 0.15); color: #4ade80; }}
        .badge-code {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}
        .badge-conf {{ background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }}

        .card-title {{ font-size: 16px; font-weight: 700; color: #fff; line-height: 1.4; }}
        
        .target-box {{
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
        }}
        .target-path {{ color: var(--green); font-weight: 600; }}
        .target-line {{ color: var(--yellow); }}

        .instruction-box {{
            background: rgba(30, 41, 59, 0.7);
            border-left: 3px solid var(--yellow);
            padding: 10px 14px;
            border-radius: 0 8px 8px 0;
            margin: 10px 0;
            font-size: 13px;
            color: #cbd5e1;
            line-height: 1.5;
        }}

        .code-container {{ position: relative; margin: 12px 0; }}
        .code-header {{
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
        }}
        pre.code-block {{
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
        }}

        .copy-btn {{
            background: var(--border);
            color: #fff;
            border: none;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .copy-btn:hover {{ background: var(--accent); color: #0f172a; font-weight: 700; }}

        .defense-box {{
            background: rgba(234, 179, 8, 0.08);
            border: 1px solid rgba(234, 179, 8, 0.2);
            border-radius: 8px;
            padding: 10px 14px;
            margin: 10px 0;
            font-size: 13px;
            color: #fef08a;
            line-height: 1.4;
        }}
        .defense-label {{ font-size: 11px; font-weight: 800; color: #facc15; text-transform: uppercase; margin-bottom: 4px; }}

        .empty-state {{ text-align: center; padding: 60px 20px; color: var(--text-muted); }}
        .empty-state h3 {{ color: #fff; margin-bottom: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <div class="logo-area">
                <span class="logo-badge">TEKNOFEST 2026</span>
                <div class="title-text">
                    <h1>Arama Motoru & Saha Kokpiti</h1>
                    <p>Akıllı Fabrika Dokümantasyon, Kılavuz & Revizyon Bilgi Tabanı</p>
                </div>
            </div>
            <div class="status-badge">● Çevrimdışı Web Portalı</div>
        </div>

        <!-- SEARCH INPUT -->
        <div class="search-wrapper">
            <span class="search-icon">🔍</span>
            <input type="text" id="searchInput" class="search-input" placeholder="Revizyon, parametre veya konu arayın (örn: mavi küp, viraj hız, camera exposure, mqtt, pid)..." autofocus autocomplete="off">
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
            <span id="resultsCount">Yükleniyor...</span>
            <span id="updateTime">Statik Bağımsız Web Portalı</span>
        </div>

        <!-- RESULTS -->
        <div id="resultsList" class="cards-list"></div>
    </div>

    <script>
        // TÜM İÇERİK VERİTABANI
        const DATABASE = {db_json};

        // TÜRKÇE NORMALİZASYON
        const TR_MAP = {{
            'ç': 'c', 'Ç': 'c', 'ğ': 'g', 'Ğ': 'g',
            'ı': 'i', 'I': 'i', 'İ': 'i', 'i': 'i',
            'ö': 'o', 'Ö': 'o', 'ş': 's', 'Ş': 's',
            'ü': 'u', 'Ü': 'u'
        }};

        function normalizeText(text) {{
            if (!text) return '';
            let res = '';
            for (let i = 0; i < text.length; i++) {{
                const ch = text[i];
                res += TR_MAP[ch] || ch.toLowerCase();
            }}
            return res;
        }}

        function tokenize(text) {{
            const norm = normalizeText(text);
            const matches = norm.match(/[a-z0-9_]{{2,}}/g);
            return matches ? new Set(matches) : new Set();
        }}

        // VERİTABANI ÖN İŞLEME (HIZLI ARAMA İÇİN)
        DATABASE.forEach(item => {{
            item._norm_title = normalizeText(item.title || '');
            item._norm_inst = normalizeText(item.instructions || '');
            item._norm_code = normalizeText(item.code_diff || '');
            item._norm_full = normalizeText(item.snippet || '') + ' ' + normalizeText(item.target_file || '');
            item._tokens_title = tokenize(item.title || '');
            item._tokens_all = tokenize((item.title || '') + ' ' + (item.instructions || '') + ' ' + (item.target_file || '') + ' ' + (item.snippet || ''));
        }});

        let currentCategory = "Tümü";
        let debounceTimer;

        const input = document.getElementById("searchInput");
        input.addEventListener("input", () => {{
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(doSearch, 80);
        }});

        function setCategory(cat) {{
            currentCategory = cat;
            document.querySelectorAll(".tab-btn").forEach(btn => {{
                btn.classList.toggle("active", btn.innerText.includes(cat));
            }});
            doSearch();
        }}

        function quickSearch(text) {{
            input.value = text;
            doSearch();
        }}

        function doSearch() {{
            const q = input.value.trim();
            if (!q) {{
                document.getElementById("resultsList").innerHTML = `
                    <div class="empty-state">
                        <h3>Arama Yapmaya Başlayın</h3>
                        <p>Hakemin istediği revizyonu, bir kuralı veya bir dosya/fonksiyon adını yazın.</p>
                    </div>`;
                document.getElementById("resultsCount").innerText = "Toplam " + DATABASE.length + " kart indekste hazır.";
                return;
            }}

            const qNorm = normalizeText(q);
            const qTokens = tokenize(q);
            const scoredResults = [];

            for (let i = 0; i < DATABASE.length; i++) {{
                const item = DATABASE[i];

                if (currentCategory !== "Tümü") {{
                    if (!item.category.toLowerCase().includes(currentCategory.toLowerCase())) {{
                        continue;
                    }}
                }}

                let score = 0;

                // 1. Başlıkta tam ifade
                if (item._norm_title.includes(qNorm)) score += 80;

                // 2. Hakem talimatında tam ifade
                if (item._norm_inst.includes(qNorm)) score += 50;

                // 3. Kod bloğunda tam ifade
                if (item._norm_code.includes(qNorm)) score += 35;

                // 4. Genel metinde tam ifade
                if (item._norm_full.includes(qNorm)) score += 20;

                // 5. Kelime eşleşmesi
                let matchedTokens = 0;
                qTokens.forEach(t => {{
                    if (item._tokens_title.has(t)) {{
                        score += 25;
                        matchedTokens++;
                    }} else if (item._tokens_all.has(t)) {{
                        score += 8;
                        matchedTokens++;
                    }}
                }});

                if (qTokens.size > 1 && matchedTokens === qTokens.size) {{
                    score += 30;
                }}

                if (score > 0) {{
                    if (item.category.toLowerCase().includes("revizyon")) {{
                        score += 5;
                    }}
                    scoredResults.push({{ item: item, score: score }});
                }}
            }}

            scoredResults.sort((a, b) => b.score - a.score);
            const topResults = scoredResults.slice(0, 20).map((r, idx) => {{
                return {{ ...r.item, score: r.score, rank: idx + 1 }};
            }});

            renderResults(topResults);
        }}

        function escapeHtml(str) {{
            if (!str) return '';
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }}

        function copyText(text, btn) {{
            navigator.clipboard.writeText(text).then(() => {{
                const old = btn.innerText;
                btn.innerText = "✓ Kopyalandı!";
                setTimeout(() => {{ btn.innerText = old; }}, 1500);
            }});
        }}

        function renderResults(results) {{
            const list = document.getElementById("resultsList");
            const countLabel = document.getElementById("resultsCount");

            if (!results || results.length === 0) {{
                countLabel.innerText = "Eşleşen sonuç bulunamadı.";
                list.innerHTML = `
                    <div class="empty-state">
                        <h3>Sonuç Bulunamadı</h3>
                        <p>Farklı bir anahtar kelime deneyin veya kategori filtresini 'Tümü' yapın.</p>
                    </div>`;
                return;
            }}

            countLabel.innerText = results.length + " sonuç bulundu (alaka sırasına göre)";
            
            list.innerHTML = results.map((item, idx) => {{
                const isTop = idx === 0;
                let badgeClass = "badge-rev";
                if (item.category.includes("Hakem")) badgeClass = "badge-hakem";
                else if (item.category.includes("Kılavuz")) badgeClass = "badge-kilavuz";
                else if (item.category.includes("Şartname")) badgeClass = "badge-score";
                else if (item.category.includes("Kaynak Kod")) badgeClass = "badge-code";
                else if (item.category.includes("Konfigürasyon")) badgeClass = "badge-conf";

                let html = `
                <div class="card ${{isTop ? 'top-hit' : ''}}">
                    <div class="card-header">
                        <div>
                            <div class="card-badges">
                                <span class="badge ${{badgeClass}}">${{escapeHtml(item.category)}}</span>
                                <span class="badge badge-file">${{escapeHtml(item.source_file)}}</span>
                                <span class="badge badge-score">Skor: ${{item.score}}</span>
                                ${{isTop ? '<span class="badge" style="background:#0284c7;color:#fff;">★ En İyi Eşleşme</span>' : ''}}
                            </div>
                            <h2 class="card-title">${{escapeHtml(item.title)}}</h2>
                        </div>
                    </div>`;

                if (item.target_file) {{
                    html += `
                    <div class="target-box">
                        <div>
                            <span>📂 Hedef Dosya: </span>
                            <span class="target-path">${{escapeHtml(item.target_file)}}</span>
                            ${{item.target_line ? `<span class="target-line">(${{escapeHtml(item.target_line)}})</span>` : ''}}
                        </div>
                        <button class="copy-btn" onclick="copyText('${{escapeHtml(item.target_file)}}', this)">Dosya Adını Kopyala</button>
                    </div>`;
                }}

                if (item.instructions) {{
                    html += `
                    <div class="instruction-box">
                        <strong>🗣️ Hakem Talimatı:</strong>
                        <div>"${{escapeHtml(item.instructions)}}"</div>
                    </div>`;
                }}

                if (item.code_diff) {{
                    html += `
                    <div class="code-container">
                        <div class="code-header">
                            <span>💻 Kod Değişikliği / Diff</span>
                            <button class="copy-btn" onclick="copyText(decodeURIComponent('${{encodeURIComponent(item.code_diff)}}'), this)">📋 Kodu Kopyala</button>
                        </div>
                        <pre class="code-block"><code>${{escapeHtml(item.code_diff)}}</code></pre>
                    </div>`;
                }}

                if (item.test_cmd) {{
                    html += `
                    <div class="code-container">
                        <div class="code-header">
                            <span>⏱️ 30 Saniyelik Hızlı Test Komutu</span>
                            <button class="copy-btn" onclick="copyText(decodeURIComponent('${{encodeURIComponent(item.test_cmd)}}'), this)">📋 Komutu Kopyala</button>
                        </div>
                        <pre class="code-block" style="max-height:80px;"><code>${{escapeHtml(item.test_cmd)}}</code></pre>
                    </div>`;
                }}

                if (item.presentation) {{
                    html += `
                    <div class="defense-box">
                        <div class="defense-label">🏆 Hakeme Sunulacak Profesyonel Açıklama</div>
                        <div>"${{escapeHtml(item.presentation)}}"</div>
                    </div>`;
                }}

                if (!item.code_diff && !item.instructions && item.snippet) {{
                    html += `
                    <div style="font-size:13px; color:#94a3b8; line-height:1.5; margin-top:8px;">
                        ${{escapeHtml(item.snippet)}}
                    </div>`;
                }}

                html += `</div>`;
                return html;
            }}).join("");
        }}

        window.addEventListener("load", () => {{
            quickSearch("mavi küp ıskarta");
        }});
    </script>
</body>
</html>
"""

    out_path = BASE_DIR / "index.html"
    out_path.write_text(html_content, encoding="utf-8")
    print(f"🚀 'index.html' başarıyla üretildi! Dosya boyutu: {out_path.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
