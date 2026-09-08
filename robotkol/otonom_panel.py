#!/usr/bin/env python3
"""
Robot kolun arayüzü ve programın giriş noktası.

Tek pencerede üç sekme: EGITIM (kolu elle sür, konum öğret),
KAMERA/KALIBRASYON (canlı görüntü, ROI çiz, renk eşiklerini ayarla),
OTONOM (başlat / durdur / acil dur, durum ve log).

Kamerayı, Arduino bağlantısını ve MQTT'yi bu dosya kurar; otonom döngüyü
ayrı bir thread olarak başlatır.

Çalıştır: python3 otonom_panel.py
"""

from __future__ import annotations

import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import cv2
from PIL import Image, ImageTk

from robot_link import (
    RobotLink, JOINT_NAMES, LIMITS_DEG, JOG_STEP_DEG, HOMING_DIRS,
    GRIP_OPEN, GRIP_CLOSE, GRIP_DEFAULT, GRIP_MAX,
    DEFAULT_SPEED_STEPS, DEFAULT_ACCEL_STEPS, DEFAULT_PORT, DEFAULT_BAUD,
)
from renk_algila import (
    RenkAlgilayici, RenkKalibrasyon, kamera_ac, kare_oku,
    hsv_araligi_ogren, RENKLER, ISLEM_BOYUT, _roi_kirp,
)
from konum_yonetici import KonumYonetici, ZORUNLU, TUM_ISIMLER
from arac_haberlesme import MqttIstemci, VARSAYILAN_BROKER
from otonom_dongu import OtonomDongu, AyarOtonom

BG, PANEL, FG, ACCENT = "#1e1e2e", "#2a2a3c", "#e0e0e0", "#4a9eff"
OK_CLR, WARN, DANGER, MUTED = "#3ec77a", "#ffb84a", "#ff4a4a", "#8a8a9a"
JOG_REPEAT_MS = 180
CW, CH = ISLEM_BOYUT


class Panel:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.port = os.environ.get("ROBOT_PORT", DEFAULT_PORT)
        self.baud = int(os.environ.get("ROBOT_BAUD", DEFAULT_BAUD))
        self.robot = RobotLink(port=self.port, baud=self.baud)
        self.konumlar = KonumYonetici()
        self.kalib = RenkKalibrasyon.yukle()
        self.alg = RenkAlgilayici(self.kalib)
        self.mqtt = MqttIstemci(broker=os.environ.get("BROKER", VARSAYILAN_BROKER),
                                client_id="robot_kol")
        self.ayar = AyarOtonom(grip_ac=GRIP_OPEN, grip_kapat=GRIP_CLOSE)

        self.kam_index = int(os.environ.get("KAMERA", "0"))
        self.cap = None
        self._son_kare = None
        self._kare_lock = threading.Lock()
        self._kam_calis = False
        self._plc_onay = False
        self._son_git = None
        self._gorme_son = None
        self._panel_log_q = queue.Queue(maxsize=200)
        self._sim_basla = False

        self.dongu = OtonomDongu(self.robot, self.alg, self._son_kare_al,
                                 self.mqtt, self.konumlar,
                                 lambda: self._sim_basla, self.ayar)

        self._jog_jobs = {}
        self._roi_ciz_bas = None

        root.title("Akilli Fabrika - Robot Kol Otonom Panel")
        root.configure(bg=BG)
        root.geometry("1000x820")
        self._stil()
        self._ust_bar()
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=6, pady=4)
        self.nb = nb
        self.tab_egitim = tk.Frame(nb, bg=BG)
        self.tab_kamera = tk.Frame(nb, bg=BG)
        self.tab_otonom = tk.Frame(nb, bg=BG)
        nb.add(self.tab_egitim, text="  EGITIM  ")
        nb.add(self.tab_kamera, text="  KAMERA / KALIBRASYON  ")
        nb.add(self.tab_otonom, text="  OTONOM  ")
        self._build_egitim()
        self._build_kamera()
        self._build_otonom()
        self._alt_konsol()

        self._kamera_baslat()
        threading.Thread(target=self.mqtt.baglan, daemon=True).start()

        self._poll()
        root.protocol("WM_DELETE_WINDOW", self._kapat)

    def _stil(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=PANEL, foreground=FG,
                    padding=(14, 8), font=("Sans", 11, "bold"))
        s.map("TNotebook.Tab", background=[("selected", ACCENT)],
              foreground=[("selected", "white")])

    def _ust_bar(self):
        bar = tk.Frame(self.root, bg=PANEL)
        bar.pack(fill="x", padx=6, pady=(6, 0))
        self.conn_btn = tk.Button(bar, text="ROBOT BAGLAN", width=14, bg=ACCENT,
                                  fg="white", font=("Sans", 10, "bold"), relief="flat",
                                  command=self._toggle_robot)
        self.conn_btn.pack(side="left", padx=6, pady=6)
        self.conn_lbl = tk.Label(bar, text=f"Robot: yok ({self.port})", bg=PANEL,
                                 fg=WARN, font=("Sans", 10))
        self.conn_lbl.pack(side="left", padx=6)
        self.mqtt_lbl = tk.Label(bar, text="MQTT: ...", bg=PANEL, fg=MUTED,
                                 font=("Sans", 10))
        self.mqtt_lbl.pack(side="right", padx=10)
        self.kam_lbl = tk.Label(bar, text="Kamera: ...", bg=PANEL, fg=MUTED,
                                font=("Sans", 10))
        self.kam_lbl.pack(side="right", padx=10)

    def _build_egitim(self):
        p = self.tab_egitim
        top = tk.Frame(p, bg=BG); top.pack(fill="x", pady=4)
        tk.Label(top, text="Jog adim (derece):", bg=BG, fg=MUTED).pack(side="left", padx=6)
        self.jog_amt = tk.Entry(top, width=5, bg="#1a1a28", fg=FG, relief="flat",
                                justify="right", insertbackground=FG)
        self.jog_amt.insert(0, str(JOG_STEP_DEG)); self.jog_amt.pack(side="left")

        wrap = tk.LabelFrame(p, text=" Eklemler ", bg=BG, fg=ACCENT,
                             font=("Sans", 11, "bold"))
        wrap.pack(fill="x", padx=6, pady=4)
        hdr = tk.Frame(wrap, bg=BG); hdr.pack(fill="x", pady=(4, 0))
        for txt, w in (("Eklem", 11), ("Pozisyon", 12), ("Anahtar", 10),
                       ("Homed", 7), ("Jog", 8)):
            tk.Label(hdr, text=txt, bg=BG, fg=MUTED, font=("Sans", 8),
                     width=w, anchor="w").pack(side="left", padx=2)
        self.pos_lbls = []
        self.sw_lbls = []
        self.homed_lbls = []
        for j in range(4):
            self._joint_row(wrap, j)

        sf = tk.Frame(p, bg=BG); sf.pack(fill="x", padx=6, pady=4)
        tk.Label(sf, text="Hiz", bg=BG, fg=FG, width=5).pack(side="left")
        self.speed = tk.Scale(sf, from_=100, to=4000, resolution=50, orient="horizontal",
                              bg=BG, fg=FG, troughcolor=PANEL, highlightthickness=0,
                              length=200, command=lambda v: self._apply_motion())
        self.speed.set(DEFAULT_SPEED_STEPS); self.speed.pack(side="left", padx=4)
        tk.Label(sf, text="Ivme", bg=BG, fg=FG, width=5).pack(side="left", padx=(10, 0))
        self.accel = tk.Scale(sf, from_=100, to=4000, resolution=50, orient="horizontal",
                              bg=BG, fg=FG, troughcolor=PANEL, highlightthickness=0,
                              length=200, command=lambda v: self._apply_motion())
        self.accel.set(DEFAULT_ACCEL_STEPS); self.accel.pack(side="left", padx=4)

        gf = tk.LabelFrame(p, text=" Gripper ", bg=BG, fg=ACCENT, font=("Sans", 11, "bold"))
        gf.pack(fill="x", padx=6, pady=4)
        self.grip = tk.Scale(gf, from_=0, to=GRIP_MAX, orient="horizontal", bg=BG, fg=FG,
                             troughcolor=PANEL, highlightthickness=0, length=360,
                             command=self._grip_slide)
        self.grip.set(GRIP_DEFAULT); self.grip.pack(side="left", padx=8, pady=4)
        tk.Button(gf, text="AC", bg="#3a4c3a", fg=FG, width=6, relief="flat",
                  command=lambda: self.grip.set(GRIP_OPEN)).pack(side="left", padx=4)
        tk.Button(gf, text="KAPAT", bg="#4c3a3a", fg=FG, width=6, relief="flat",
                  command=lambda: self.grip.set(GRIP_CLOSE)).pack(side="left", padx=4)

        kf = tk.LabelFrame(p, text=" Konum Ogret (kolu getir, KAYDET) ", bg=BG,
                           fg=OK_CLR, font=("Sans", 11, "bold"))
        kf.pack(fill="x", padx=6, pady=6)
        self.konum_durum = {}
        for isim in TUM_ISIMLER:
            row = tk.Frame(kf, bg=PANEL); row.pack(fill="x", padx=6, pady=3)
            zorunlu = " *" if isim in ZORUNLU else " (ops.)"
            tk.Label(row, text=isim + zorunlu, bg=PANEL, fg=FG, width=14,
                     font=("Sans", 10, "bold"), anchor="w").pack(side="left", padx=4)
            st = tk.Label(row, text="- kayitli degil", bg=PANEL, fg=MUTED, width=26,
                          anchor="w"); st.pack(side="left", padx=4)
            self.konum_durum[isim] = st
            tk.Button(row, text="KAYDET", bg=ACCENT, fg="white", width=8, relief="flat",
                      command=lambda i=isim: self._konum_kaydet(i)).pack(side="left", padx=3)
            tk.Button(row, text="GIT", bg="#3a4c3a", fg=FG, width=5, relief="flat",
                      command=lambda i=isim: self._konum_git(i)).pack(side="left", padx=3)
            tk.Button(row, text="Sil", bg="#4c3a3a", fg=FG, width=4, relief="flat",
                      command=lambda i=isim: self._konum_sil(i)).pack(side="left", padx=3)
        self._konum_durum_guncelle()

    def _joint_row(self, parent, j):
        row = tk.Frame(parent, bg=PANEL); row.pack(fill="x", padx=6, pady=2)
        tk.Label(row, text=f"{j} {JOINT_NAMES[j]}", bg=PANEL, fg=FG, width=10,
                 font=("Sans", 10, "bold"), anchor="w").pack(side="left", padx=2)
        pos = tk.Label(row, text="---.- deg", bg=PANEL, fg=OK_CLR, width=11,
                       font=("Mono", 10), anchor="w"); pos.pack(side="left", padx=2)
        self.pos_lbls.append(pos)
        sw = tk.Label(row, text="?", bg=PANEL, fg=MUTED, width=10,
                      font=("Sans", 9, "bold"), anchor="w"); sw.pack(side="left", padx=2)
        self.sw_lbls.append(sw)
        hm = tk.Label(row, text="-", bg=PANEL, fg=MUTED, width=7,
                      font=("Sans", 9), anchor="w"); hm.pack(side="left", padx=2)
        self.homed_lbls.append(hm)
        bminus = tk.Button(row, text="◀", bg="#3a3a4c", fg=FG, width=3, relief="flat")
        bminus.pack(side="left", padx=1)
        bplus = tk.Button(row, text="▶", bg="#3a3a4c", fg=FG, width=3, relief="flat")
        bplus.pack(side="left", padx=1)
        bminus.bind("<ButtonPress-1>", lambda e, jj=j: self._jog_start(jj, -1))
        bminus.bind("<ButtonRelease-1>", lambda e, jj=j: self._jog_stop(jj))
        bplus.bind("<ButtonPress-1>", lambda e, jj=j: self._jog_start(jj, +1))
        bplus.bind("<ButtonRelease-1>", lambda e, jj=j: self._jog_stop(jj))
        tk.Button(row, text="HOME", bg="#3a4c3a", fg=FG, width=6, relief="flat",
                  command=lambda jj=j: self._home(jj)).pack(side="left", padx=4)
        ent = tk.Entry(row, width=7, bg="#1a1a28", fg=FG, relief="flat", justify="right",
                       insertbackground=FG); ent.insert(0, "0")
        ent.pack(side="left", padx=2)
        lo, hi = LIMITS_DEG[j]
        tk.Button(row, text="Git", bg=ACCENT, fg="white", width=4, relief="flat",
                  command=lambda jj=j, e=ent: self._move_joint(jj, e)).pack(side="left", padx=1)
        tk.Label(row, text=f"[{lo:.0f},{hi:.0f}]", bg=PANEL, fg=MUTED,
                 font=("Sans", 8)).pack(side="left")
        if j == 0:
            tk.Button(row, text="HOME ALL", bg="#3a4c3a", fg=FG, width=9, relief="flat",
                      command=lambda: self._home(None)).pack(side="right", padx=4)

    def _build_kamera(self):
        p = self.tab_kamera
        sol = tk.Frame(p, bg=BG); sol.pack(side="left", padx=6, pady=6)
        self.canvas = tk.Canvas(sol, width=CW, height=CH, bg="#000", highlightthickness=1,
                                highlightbackground=ACCENT)
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self._roi_bas)
        self.canvas.bind("<B1-Motion>", self._roi_surukle)
        self.canvas.bind("<ButtonRelease-1>", self._roi_birak)
        altrow = tk.Frame(sol, bg=BG); altrow.pack(fill="x", pady=4)
        tk.Label(altrow, text="ROI: fareyle dikdortgen surukle", bg=BG, fg=MUTED,
                 font=("Sans", 9)).pack(side="left")
        tk.Button(altrow, text="KAMERA YENILE", bg=ACCENT, fg="white", relief="flat",
                  command=self._kamera_baslat).pack(side="right", padx=4)
        self.kam_durum_lbl = tk.Label(sol, text="", bg=BG, fg=WARN, font=("Sans", 9))
        self.kam_durum_lbl.pack()

        sag = tk.Frame(p, bg=BG); sag.pack(side="left", fill="y", padx=6, pady=6)
        tk.Label(sag, text="Renk Ogret", bg=BG, fg=ACCENT,
                 font=("Sans", 12, "bold")).pack(anchor="w")
        tk.Label(sag, text="Kutuyu ROI'ye getir, ilgili rengi ogret:",
                 bg=BG, fg=MUTED, font=("Sans", 9)).pack(anchor="w", pady=(0, 4))
        for renk, clr in (("RED", DANGER), ("GREEN", OK_CLR), ("BLUE", ACCENT)):
            tk.Button(sag, text=f"{renk} OGREN", bg=clr, fg="white", width=18,
                      font=("Sans", 10, "bold"), relief="flat",
                      command=lambda r=renk: self._renk_ogren(r)).pack(pady=3)

        tk.Label(sag, text="Esikler", bg=BG, fg=ACCENT,
                 font=("Sans", 11, "bold")).pack(anchor="w", pady=(12, 0))
        tk.Label(sag, text="Doluluk esigi (%)", bg=BG, fg=FG).pack(anchor="w")
        self.doluluk_sc = tk.Scale(sag, from_=10, to=90, orient="horizontal", bg=BG, fg=FG,
                                   troughcolor=PANEL, highlightthickness=0, length=200,
                                   command=self._esik_guncelle)
        self.doluluk_sc.set(int(self.kalib.doluluk_esigi * 100)); self.doluluk_sc.pack()
        tk.Label(sag, text="Emin marji (%)", bg=BG, fg=FG).pack(anchor="w")
        self.marj_sc = tk.Scale(sag, from_=0, to=50, orient="horizontal", bg=BG, fg=FG,
                                troughcolor=PANEL, highlightthickness=0, length=200,
                                command=self._esik_guncelle)
        self.marj_sc.set(int(self.kalib.marj * 100)); self.marj_sc.pack()

        self.tespit_lbl = tk.Label(sag, text="Tespit: -", bg=BG, fg=FG,
                                   font=("Mono", 12, "bold")); self.tespit_lbl.pack(pady=10)
        tk.Button(sag, text="KALIBRASYONU KAYDET", bg=OK_CLR, fg="white", width=22,
                  font=("Sans", 10, "bold"), relief="flat",
                  command=self._kalib_kaydet).pack(pady=6)
        self.mask_var = tk.BooleanVar(value=False)
        tk.Checkbutton(sag, text="Maske goster (secili rengin)", var=self.mask_var,
                       bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG).pack(anchor="w")
        self.mask_renk = tk.StringVar(value="RED")
        ttk.Combobox(sag, textvariable=self.mask_renk, values=list(RENKLER),
                     width=8, state="readonly").pack(anchor="w", pady=2)

    def _build_otonom(self):
        p = self.tab_otonom
        bf = tk.Frame(p, bg=BG); bf.pack(fill="x", padx=8, pady=8)
        tk.Button(bf, text="BASLA", bg=OK_CLR, fg="white", font=("Sans", 16, "bold"),
                  relief="flat", height=2, width=10,
                  command=self._otonom_basla).pack(side="left", padx=6)
        tk.Button(bf, text="DUR", bg=WARN, fg="black", font=("Sans", 14, "bold"),
                  relief="flat", height=2, width=8,
                  command=self.dongu.durdur).pack(side="left", padx=6)
        tk.Button(bf, text="ACIL DURDUR", bg=DANGER, fg="white", font=("Sans", 14, "bold"),
                  relief="flat", height=2, width=12,
                  command=self.dongu.acil).pack(side="left", padx=6)

        df = tk.LabelFrame(p, text=" Durum ", bg=BG, fg=ACCENT, font=("Sans", 11, "bold"))
        df.pack(fill="x", padx=8, pady=4)
        self.durum_lbl = tk.Label(df, text="BOSTA", bg=BG, fg=OK_CLR,
                                  font=("Sans", 16, "bold")); self.durum_lbl.grid(row=0, column=0, padx=14, pady=6)
        self.cevrim_lbl = tk.Label(df, text="Cevrim: 0", bg=BG, fg=FG,
                                   font=("Sans", 13)); self.cevrim_lbl.grid(row=0, column=1, padx=14)
        self.sonrenk_lbl = tk.Label(df, text="Son renk: -", bg=BG, fg=FG,
                                    font=("Sans", 13)); self.sonrenk_lbl.grid(row=0, column=2, padx=14)

        gf = tk.LabelFrame(p, text=" PLC 'BASLA' Sinyali ", bg=BG, fg=ACCENT,
                           font=("Sans", 11, "bold"))
        gf.pack(fill="x", padx=8, pady=4)
        self.basla_lbl = tk.Label(gf, text="● pasif", bg=BG, fg=MUTED,
                                  font=("Sans", 13, "bold")); self.basla_lbl.pack(side="left", padx=10, pady=4)
        self.sim_btn = tk.Button(gf, text="BASLA (SIM) - bas/birak", bg="#3a3a4c", fg=FG,
                                 relief="flat", width=22)
        self.sim_btn.pack(side="left", padx=10)
        self.sim_btn.bind("<ButtonPress-1>", lambda e: setattr(self, "_sim_basla", True))
        self.sim_btn.bind("<ButtonRelease-1>", lambda e: setattr(self, "_sim_basla", False))
        tk.Label(gf, text="(gercek haber Arduino A5'ten; bu buton sadece test icin)",
                 bg=BG, fg=MUTED, font=("Sans", 9)).pack(side="left", padx=8)

        hf = tk.LabelFrame(p, text=" PLC HABER (manuel kontrol) ", bg=BG, fg=ACCENT,
                           font=("Sans", 11, "bold"))
        hf.pack(fill="x", padx=8, pady=4)
        self.haber_lbl = tk.Label(hf, text="○ HABER YOK", bg=BG, fg=MUTED,
                                  font=("Sans", 15, "bold"))
        self.haber_lbl.pack(side="left", padx=12, pady=8)
        self.devam_btn = tk.Button(hf, text="DEVAM ▶", bg="#3a3a4c", fg=MUTED,
                                   font=("Sans", 13, "bold"), relief="flat", width=12,
                                   state="disabled", command=self._plc_devam)
        self.devam_btn.pack(side="left", padx=12)
        tk.Label(hf, text="(haber gelmeden buton pasif; gelince aktif olur)",
                 bg=BG, fg=MUTED, font=("Sans", 9)).pack(side="left", padx=8)

        of = tk.LabelFrame(p, text=" Secenekler ", bg=BG, fg=ACCENT, font=("Sans", 11, "bold"))
        of.pack(fill="x", padx=8, pady=4)
        self.dogrula_var = tk.BooleanVar(value=self.ayar.dogrula)
        tk.Checkbutton(of, text="Kavrama dogrula (kamerayla 'aldim mi')",
                       var=self.dogrula_var, bg=BG, fg=FG, selectcolor=PANEL,
                       activebackground=BG,
                       command=self._ayar_guncelle).pack(side="left", padx=8)
        tk.Label(of, text="Grip ac:", bg=BG, fg=FG).pack(side="left", padx=(14, 2))
        self.gripac_e = tk.Entry(of, width=4, bg="#1a1a28", fg=FG, relief="flat",
                                 justify="right"); self.gripac_e.insert(0, "0")
        self.gripac_e.pack(side="left")
        tk.Label(of, text="Grip kapat:", bg=BG, fg=FG).pack(side="left", padx=(10, 2))
        self.gripkapat_e = tk.Entry(of, width=4, bg="#1a1a28", fg=FG, relief="flat",
                                    justify="right"); self.gripkapat_e.insert(0, str(GRIP_CLOSE))
        self.gripkapat_e.pack(side="left")
        tk.Button(of, text="Uygula", bg=ACCENT, fg="white", relief="flat",
                  command=self._ayar_guncelle).pack(side="left", padx=10)

        lf = tk.LabelFrame(p, text=" Otonom Log ", bg=BG, fg=MUTED, font=("Sans", 10))
        lf.pack(fill="both", expand=True, padx=8, pady=6)
        self.otolog = tk.Text(lf, height=10, bg="#12121c", fg="#a0d0a0",
                              font=("Mono", 9), relief="flat"); self.otolog.pack(fill="both", expand=True, padx=4, pady=4)

    def _alt_konsol(self):
        cf = tk.LabelFrame(self.root, text=" Robot Konsolu ", bg=BG, fg=MUTED,
                           font=("Sans", 9))
        cf.pack(fill="x", padx=6, pady=(0, 6))
        self.konsol = tk.Text(cf, height=5, bg="#12121c", fg="#8ab4f8",
                              font=("Mono", 9), relief="flat"); self.konsol.pack(fill="x", padx=4, pady=4)

    def _require(self):
        if not self.robot.is_connected():
            messagebox.showwarning("Baglanti yok", "Once ROBOT BAGLAN.")
            return False
        return True

    def _apply_motion(self):
        if self.robot.is_connected():
            self.robot.set_motion(self.speed.get(), self.accel.get())

    def _jog_amount(self):
        try:
            return float(self.jog_amt.get())
        except ValueError:
            return JOG_STEP_DEG

    def _jog_start(self, j, yon):
        if not self._require():
            return
        self._jog_stop(j)
        amt = self._jog_amount() * yon
        def tick():
            st = self.robot.snapshot()
            if (st.limits_mask & (1 << j)) and yon == HOMING_DIRS[j]:
                self._otolog(f"{JOINT_NAMES[j]}: ANAHTAR BASILI - o yone jog engellendi "
                             "(anahtari korumak icin)")
                self._jog_jobs.pop(j, None)
                return
            self.robot.jog_deg(j, amt)
            self._jog_jobs[j] = self.root.after(JOG_REPEAT_MS, tick)
        tick()

    def _jog_stop(self, j):
        job = self._jog_jobs.pop(j, None)
        if job is not None:
            self.root.after_cancel(job)

    def _home(self, j):
        if self._require():
            self.robot.home(j)

    def _move_joint(self, j, ent):
        if not self._require():
            return
        try:
            a = float(ent.get())
        except ValueError:
            messagebox.showerror("Hata", "Aci sayisal olmali."); return
        lo, hi = LIMITS_DEG[j]
        if not (lo <= a <= hi):
            messagebox.showwarning("Limit", f"{JOINT_NAMES[j]} [{lo:.0f},{hi:.0f}]"); return
        t = list(self.robot.snapshot().angles); t[j] = a
        self.robot.move_deg(t)

    def _grip_slide(self, v):
        if self.robot.is_connected():
            self.robot.grip(int(float(v)))

    def _konum_kaydet(self, isim):
        if not self._require():
            return
        st = self.robot.snapshot()
        self.konumlar.kaydet(isim, st.angles, int(self.grip.get()))
        self._konum_durum_guncelle()
        self._otolog(f"Konum kaydedildi: {isim} = "
                     + ", ".join(f"{a:.1f}" for a in st.angles) + f"  grip={int(self.grip.get())}")

    def _konum_git(self, isim):
        if not self._require():
            return
        k = self.konumlar.al(isim)
        if k is None:
            messagebox.showinfo("Yok", f"{isim} kayitli degil."); return
        self._ayar_guncelle()
        threading.Thread(target=self._git_seq, args=(isim, k), daemon=True).start()

    def _move_bekle(self, timeout=20):
        import time as _t
        t0 = _t.time(); _t.sleep(0.3)
        while _t.time() - t0 < timeout:
            if not self.robot.snapshot().moving:
                return
            _t.sleep(0.05)

    def _git_seq(self, isim, k):
        onceki = getattr(self, "_son_git", None)
        hiz, ivme = self.speed.get(), self.accel.get()
        if isim == "AL":
            self.robot.grip(self.ayar.grip_ac)
            self.robot.set_motion(hiz, ivme)
            self.robot.move_deg(k.angles)
            self._move_bekle()
            self.robot.grip(k.gripper)
        elif isim == "YUKLE":
            omuz = self.ayar.omuz_kaldir_aci
            self.robot.set_motion(hiz, ivme)
            a1 = list(self.robot.snapshot().angles); a1[1] = omuz
            self.robot.move_deg(a1); self._move_bekle()
            a2 = list(a1); a2[0] = k.angles[0]; a2[1] = omuz
            self.robot.move_deg(a2); self._move_bekle()
            self.robot.move_deg(list(k.angles)); self._move_bekle()
            self.robot.grip(self.ayar.grip_ac)
            if self.mqtt is not None:
                gonderildi = self.mqtt.basla_gonder()
                self._plog("YUKLE'de araca BASLA gonderildi -> arac baslasin"
                           if gonderildi else "UYARI: BASLA gonderilemedi (MQTT?)")
        elif isim == "GORME" and onceki == "YUKLE":
            self.robot.grip(self.ayar.grip_ac)
            self.robot.set_motion(hiz, ivme)
            lift = list(self.robot.snapshot().angles)
            lift[1] = self.ayar.omuz_kaldir_aci
            self.robot.move_deg(lift); self._move_bekle()
            self.robot.move_deg(list(k.angles)); self._move_bekle()
        else:
            self.robot.grip(self.ayar.grip_ac)
            self.robot.set_motion(hiz, ivme)
            self.robot.move_deg(k.angles)
        self._son_git = isim

    def _gorme_renk_kontrol(self):
        if self.dongu.durum().get("calisiyor"):
            return
        gk = self.konumlar.al("GORME")
        if gk is None or not self.robot.is_connected():
            self._gorme_son = None
            return
        st = self.robot.snapshot()
        if any(abs(st.angles[j] - gk.angles[j]) > 4.0 for j in range(4)):
            self._gorme_son = None
            return
        frame = self._son_kare_al()
        if frame is None:
            return
        s = self.alg.algila(frame)
        if s.renk in ("RED", "GREEN", "BLUE") and s.renk != self._gorme_son:
            if self.mqtt is not None and self.mqtt.renk_gonder(s.renk):
                self._gorme_son = s.renk
                self._otolog(f"GORME'de renk gonderildi -> {s.renk}")

    def _konum_sil(self, isim):
        self.konumlar.sil(isim); self._konum_durum_guncelle()

    def _konum_durum_guncelle(self):
        for isim, lbl in self.konum_durum.items():
            k = self.konumlar.al(isim)
            if k:
                lbl.config(text="✓ " + ", ".join(f"{a:.0f}" for a in k.angles)
                           + f" g{k.gripper}", fg=OK_CLR)
            else:
                lbl.config(text="- kayitli degil", fg=MUTED)

    def _kamera_baslat(self):
        self._kam_calis = False
        time.sleep(0.15)
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        if hasattr(self, "kam_durum_lbl"):
            self.kam_durum_lbl.config(text="Kamera aciliyor...", fg=WARN)
            self.kam_durum_lbl.update_idletasks()
        self.cap = kamera_ac(self.kam_index)
        if not self.cap.isOpened():
            self.kam_lbl.config(text="Kamera: ACILAMADI", fg=DANGER)
            if hasattr(self, "kam_durum_lbl"):
                self.kam_durum_lbl.config(
                    text="ACILAMADI - kamera takili/bos mu? 'KAMERA YENILE' dene",
                    fg=DANGER)
            return
        self._son_kare = None
        self._kam_calis = True
        threading.Thread(target=self._kamera_loop, daemon=True).start()
        if hasattr(self, "kam_durum_lbl"):
            self.kam_durum_lbl.config(text="Kamera acildi ✓", fg=OK_CLR)

    def _kamera_loop(self):
        while self._kam_calis:
            ok, f = kare_oku(self.cap)
            if ok:
                with self._kare_lock:
                    self._son_kare = f
            else:
                time.sleep(0.02)

    def _son_kare_al(self):
        with self._kare_lock:
            return None if self._son_kare is None else self._son_kare.copy()

    def _roi_bas(self, e):
        self._roi_ciz_bas = (e.x, e.y)

    def _roi_surukle(self, e):
        if self._roi_ciz_bas:
            self.canvas.delete("roidraw")
            x0, y0 = self._roi_ciz_bas
            self.canvas.create_rectangle(x0, y0, e.x, e.y, outline="#ffff00",
                                         width=2, tags="roidraw")

    def _roi_birak(self, e):
        if not self._roi_ciz_bas:
            return
        x0, y0 = self._roi_ciz_bas
        x1, y1 = e.x, e.y
        x, y = min(x0, x1), min(y0, y1)
        w, h = abs(x1 - x0), abs(y1 - y0)
        if w > 8 and h > 8:
            self.kalib.roi = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
            self._otolog(f"ROI: {self.kalib.roi}")
        self._roi_ciz_bas = None
        self.canvas.delete("roidraw")

    def _renk_ogren(self, renk):
        f = self._son_kare_al()
        if f is None:
            messagebox.showwarning("Kamera", "Goruntu yok."); return
        roi = _roi_kirp(f, self.kalib.roi)
        self.kalib.hsv[renk] = hsv_araligi_ogren(roi)
        self.alg.kalib = self.kalib
        self._otolog(f"{renk} ogrenildi: {self.kalib.hsv[renk]}")
        messagebox.showinfo("Ogrenildi", f"{renk} HSV araligi guncellendi.\n"
                            "Kaydetmek icin 'KALIBRASYONU KAYDET'.")

    def _esik_guncelle(self, *_):
        self.kalib.doluluk_esigi = self.doluluk_sc.get() / 100.0
        self.kalib.marj = self.marj_sc.get() / 100.0

    def _kalib_kaydet(self):
        self._esik_guncelle()
        self.kalib.kaydet()
        self._otolog("Renk kalibrasyonu kaydedildi -> renk_kalibrasyon.json")
        messagebox.showinfo("Kaydedildi", "renk_kalibrasyon.json guncellendi.")

    def _ayar_guncelle(self):
        self.ayar.dogrula = self.dogrula_var.get()
        try:
            self.ayar.grip_ac = int(self.gripac_e.get())
            self.ayar.grip_kapat = int(self.gripkapat_e.get())
        except ValueError:
            pass
        self.ayar.hiz = int(self.speed.get())
        self.ayar.ivme = int(self.accel.get())

    def _otonom_basla(self):
        self._ayar_guncelle()
        if not self.dongu.baslat():
            d = self.dongu.durum()
            messagebox.showwarning("Baslamadi", d.get("hata") or "Baslatilamadi.")

    def _otolog(self, msg):
        self.otolog.insert("end", msg + "\n"); self.otolog.see("end")

    def _plog(self, msg):
        try:
            self._panel_log_q.put_nowait(msg)
        except queue.Full:
            pass

    def _plc_devam(self):
        self._plc_onay = True
        self._otolog("PLC HABER onaylandi -> DEVAM basildi.")

    def _poll(self):
        st = self.robot.snapshot()
        for j in range(4):
            self.pos_lbls[j].config(text=f"{st.angles[j]:7.1f} deg")
            basili = bool(st.limits_mask & (1 << j))
            self.sw_lbls[j].config(text="● BASILI" if basili else "○ acik",
                                   fg=DANGER if basili else OK_CLR)
            homed = bool(st.homed_mask & (1 << j))
            self.homed_lbls[j].config(text="✓ evet" if homed else "hayir",
                                      fg=OK_CLR if homed else MUTED)

        if st.estop:
            self.conn_lbl.config(text="!! ESTOP - DEVAM(R) gerekli", fg=DANGER)
        elif st.connected:
            self.conn_lbl.config(text=f"Robot: BAGLI {self.port}"
                                 + ("  [hareket]" if st.moving else ""), fg=OK_CLR)
        else:
            self.conn_lbl.config(text=f"Robot: yok ({self.port})", fg=WARN)
        self.mqtt_lbl.config(text="MQTT: BAGLI" if self.mqtt.bagli else "MQTT: yok",
                             fg=OK_CLR if self.mqtt.bagli else WARN)

        if self.nb.index(self.nb.select()) == 1:
            self._kamera_goster()
        cap_ok = self.cap is not None and self.cap.isOpened()
        self.kam_lbl.config(text="Kamera: BAGLI" if cap_ok else "Kamera: yok",
                            fg=OK_CLR if cap_ok else DANGER)

        basla_aktif = (st.basla == 1) or self._sim_basla
        if basla_aktif:
            kaynak = "A5" if st.basla == 1 else "SIM"
            self.basla_lbl.config(text=f"● AKTIF ({kaynak})", fg=OK_CLR)
        else:
            self.basla_lbl.config(text="● pasif", fg=MUTED)

        if basla_aktif:
            self.haber_lbl.config(text="● HABER GELDI", fg=OK_CLR)
            self.devam_btn.config(state="normal", bg=OK_CLR, fg="white")
        else:
            self.haber_lbl.config(text="○ HABER YOK", fg=MUTED)
            self.devam_btn.config(state="disabled", bg="#3a3a4c", fg=MUTED)
            self._plc_onay = False

        d = self.dongu.durum()
        self.durum_lbl.config(text=d["durum"],
                              fg=DANGER if d["durum"] == "HATA" else
                                 (OK_CLR if d["calisiyor"] else FG))
        self.cevrim_lbl.config(text=f"Cevrim: {d['cevrim']}")
        self.sonrenk_lbl.config(text=f"Son renk: {d['son_renk']}")

        self._gorme_renk_kontrol()

        for _ in range(30):
            try:
                self._otolog(self._panel_log_q.get_nowait())
            except queue.Empty:
                break
        for _ in range(30):
            try:
                self._otolog(self.dongu.log_queue.get_nowait())
            except queue.Empty:
                break
        for _ in range(30):
            try:
                kind, text = self.robot.log_queue.get_nowait()
                tag = {"TX": "> ", "RX": "< ", "ERR": "! ", "INFO": "i "}.get(kind, "  ")
                self.konsol.insert("end", f"{tag}{text}\n")
            except queue.Empty:
                break
        self.konsol.see("end")

        self.root.after(100, self._poll)

    def _kamera_goster(self):
        f = self._son_kare_al()
        if f is None:
            return
        s = self.alg.algila(f)
        self.tespit_lbl.config(
            text=f"Tespit: {s.renk}",
            fg={"RED": DANGER, "GREEN": OK_CLR, "BLUE": ACCENT}.get(s.renk, MUTED))
        goster = self.alg.roi_ciz(f, s)
        if self.mask_var.get():
            import numpy as np
            from renk_algila import _renk_maskesi
            hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
            m = _renk_maskesi(hsv, self.kalib.hsv.get(self.mask_renk.get(),
                                                      [[[0, 0, 0], [0, 0, 0]]]))
            goster = goster.copy()
            goster[m > 0] = (0, 255, 0)
        rgb = cv2.cvtColor(goster, cv2.COLOR_BGR2RGB)
        img = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.canvas.create_image(0, 0, anchor="nw", image=img)
        self.canvas.image = img

    def _toggle_robot(self):
        if self.robot.is_connected():
            self.robot.disconnect()
            self.conn_btn.config(text="ROBOT BAGLAN", bg=ACCENT)
        else:
            if self.robot.connect():
                self.conn_btn.config(text="ROBOT KES", bg=DANGER)
                self._apply_motion()
            else:
                ports = ", ".join(RobotLink.list_ports()) or "(yok)"
                messagebox.showerror("Baglanti hatasi",
                                     f"{self.port} acilamadi.\nPortlar: {ports}")

    def _kapat(self):
        try:
            self.dongu.acil()
        except Exception:
            pass
        self._kam_calis = False
        time.sleep(0.1)
        try:
            if self.cap:
                self.cap.release()
        except Exception:
            pass
        try:
            if self.robot.is_connected():
                self.robot.estop(); self.robot.disconnect()
        except Exception:
            pass
        try:
            self.mqtt.kapat()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    Panel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
