# -*- coding: utf-8 -*-
"""
Leitura de perfis *.SOL* com DSSATTools 3.x
------------------------------------------
read_profile(path, code) → dict pronto p/ preencher a UI
show_profiles(path)      → lista de {code, content}
"""

from pathlib import Path
import re
import numpy as np
from DSSATTools.soil import SoilProfile

# ----------------------------------------------------------------------
MISSING = {None, "nan", "NaN"}
ID_RE = re.compile(r"^[A-Za-z0-9]{10}$")        # códigos-ID válidos (10 chars)


def sane(v):
    """Converte «coisa» em string limpa, sem -99/NaN."""
    if v in MISSING or (isinstance(v, float) and v != v):
        return ""
    if isinstance(v, (int, float)) and float(v).is_integer():
        return str(int(v))
    return str(v).strip()


def get_content_by_profile_id(sol_path: Path | str, code: str) -> str:
    """Extrai o bloco-texto referente ao perfil *code* (inclui cabeçalhos)."""
    sol_path = Path(sol_path)
    content = sol_path.read_text(encoding="utf-8")
    for blk in re.split(r"\*+", content):
        if blk.strip().startswith(code):
            return blk
    raise ValueError(f"Perfil {code} não encontrado")

def show_profiles(sol_path: Path | str) -> list[dict]:
    """Lista somente os perfis válidos existentes no .SOL."""
    sol_path = Path(sol_path)
    content  = sol_path.read_text(encoding="utf-8")

    out: list[dict] = []
    for blk in re.split(r"\*+", content):
        first = blk.strip().splitlines()
        if not first:
            continue

        # 1.ª linha do bloco (sem o * inicial)
        hdr  = first[0].lstrip("*").rstrip()
        cols = hdr.split()

        code = cols[0].strip()
        if not ID_RE.match(code):
            continue

        # nome da série (a partir da 5.ª coluna)
        if cols[4].upper() == "DEFAULT":
            series_name = " ".join(cols[6:]).lstrip("-").strip()
        else:
            series_name = " ".join(cols[4:]).lstrip("-").strip()

        label = f"{series_name} ({code})" if series_name else code
        out.append({"code": code,
                    "label": label,
                    "content": blk})
    return out

NUM_RE = re.compile(r"-?\d+(?:\.\d+)?$")      # inteiro ou decimal opcional ±

# ----------------------------------------------------------------------
def read_profile(path: str | Path, code: str) -> dict:
    """Lê um perfil *.SOL* (DSSAT) e devolve TUDO que a interface precisa."""

    path = Path(path)
    prof = SoilProfile.from_file(code, path)
    raw  = prof.__dict__['_Record__data']

    # ── helper case-insensitive ---------------------------------------
    def g(field, default=""):
        return raw.get(field) or raw.get(field.upper()) or raw.get(field.lower()) or default

    # ── latitude / longitude -----------------------------------------
    blk = get_content_by_profile_id(path, code).splitlines()
    lat = lon = ""
    for i, ln in enumerate(blk):
        if ln.strip().upper().startswith("@SITE") and i + 1 < len(blk):
            for tok in blk[i + 1].split():
                if NUM_RE.match(tok):
                    if not lat:   lat = tok
                    elif not lon: lon = tok; break
            break

    # ── cabeçalho simples --------------------------------------------
    drainage = sane(g("sldr"))
    runoff   = sane(g("slro"))
    scom = g("scom")
    if str(scom).strip() in {"", "-99", "nan", "NaN"}:
        first = (g("soil_series_name") or "").strip().upper()[:1]
        color_code = {
            "B": "BL",
            "N": "R",
            "G": "G",
            "Y": "Y",
            "R": "R",
        }.get(first, "BN")
    else:
        color_code = str(scom).strip()

    # ── utilitário: garante sempre list[str] -------------------------
    def as_list(x):
        if x in ("", None):                     return []
        if isinstance(x, (list, tuple, np.ndarray)): return list(x)
        return [x]

    # listas “normais” ------------------------------------------------
    slb  = as_list(g("slb"))
    slmh = as_list(g("slmh"))
    slcl = as_list(g("slcl"))
    slsi = as_list(g("slsi"))
    slcf = as_list(g("slcf"))
    sloc = as_list(g("sloc"))
    slhw = as_list(g("slhw"))
    scec = as_list(g("scec"))
    slni = as_list(g("slni"))

    # *novas* listas para a grade de cálculo --------------------------
    slll = as_list(g("slll"))
    sdul = as_list(g("sdul"))
    ssat = as_list(g("ssat"))
    sbdm = as_list(g("sbdm"))
    sskh = as_list(g("ssks"))
    srgf = as_list(g("srgf"))

    # ── fallback: parse direto da tabela se algo estiver faltando ----
    if not slb or not slll or not ssat:
        header = {}
        rows   = []
        for ln in blk:
            if ln.upper().startswith("@  SLB"):
                header = {tok.upper(): i for i, tok in enumerate(ln.replace("@", "").split())}
                continue
            if header and (ln.startswith("@") or ln.startswith("*") or not ln.strip()):
                break
            if header:
                rows.append(ln.split())

        def col(tok):
            idx = header.get(tok)
            return [row[idx] if idx is not None and idx < len(row) else "" for row in rows]

        if not slb:  slb = col("SLB")
        if not slmh: slmh = col("SLMH")
        if not slcl: slcl = col("SLCL")
        if not slsi: slsi = col("SLSI")
        if not slcf: slcf = col("SLCF")
        if not sloc: sloc = col("SLOC")
        if not slhw: slhw = col("SLHW")
        if not scec: scec = col("SCEC")
        if not slni: slni = col("SLNI")

        if not slll: slll = col("SLLL")
        if not sdul: sdul = col("SDUL")
        if not ssat: ssat = col("SSAT")
        if not sbdm: sbdm = col("SBDM")
        if not sskh: sskh = col("SSKS") or col("SSKH")
        if not srgf: srgf = col("SRGF")

    # ── monta lista de camadas ---------------------------------------
    layers = []
    n = len(slb)
    for i in range(n):
        layers.append({
            "depth":  sane(slb[i]),
            "texture": sane(slmh[i]) if i < len(slmh) else "",
            "clay":    sane(slcl[i]) if i < len(slcl) else "-99",
            "silt":    sane(slsi[i]) if i < len(slsi) else "-99",
            "stones":  sane(slcf[i]) if i < len(slcf) else "-99",
            "oc":      sane(sloc[i]) if i < len(sloc) else "-99",
            "ph":      sane(slhw[i]) if i < len(slhw) else "-99",
            "cec":     sane(scec[i]) if i < len(scec) else "-99",
            "tn":      sane(slni[i]) if i < len(slni) else "-99",
            "lll":     sane(slll[i]) if i < len(slll) else "",
            "dul":     sane(sdul[i]) if i < len(sdul) else "",
            "sat":     sane(ssat[i]) if i < len(ssat) else "",
            "bd":      sane(sbdm[i]) if i < len(sbdm) else "",
            "ksat":    sane(sskh[i]) if i < len(sskh) else "",
            "srgf":    sane(srgf[i]) if i < len(srgf) else "",
        })

    # ── dicionário final ---------------------------------------------
    return {
        "country":             sane(g("country")),
        "site_name":           sane(g("site")),
        "institute_code":      sane(g("name")[:2]).upper(),
        "latitude":            lat,
        "longitude":           lon,
        "soil_data_source":    sane(g("soil_data_source")),
        "soil_series_name":    sane(g("soil_series_name")),
        "soil_classification": sane(g("scs_family")),
        "color_code":          color_code,
        "albedo":              sane(g("salb")),
        "drainage_rate":       drainage,
        "runoff_curve":        runoff,
        "fertility_factor":    sane(g("slpf")),
        "layers":              layers,
    }
