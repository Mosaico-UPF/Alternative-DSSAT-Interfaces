# createSoilFile.py
from __future__ import annotations
from pathlib import Path
from DSSATTools.soil import SoilProfile, SoilLayer

DEFAULT_LAYER_KEYS = (
    "slb slll sdul ssat srgf ssks sbdm sloc slcl slsi slcf slni slhw "
    "slhb scec sadc slpx slpt slpo caco3 slal slfe slmn slbs slpa slpb "
    "slke slmg slna slsu slec slca"
).split()

def make_layer(**kwargs) -> SoilLayer:
    """Builds a Soil Layer, missing values are filled with -99"""
    # Filling the data gaps
    for k in DEFAULT_LAYER_KEYS:
        kwargs.setdefault(k, -99)
    return SoilLayer(**kwargs)

def build_soil_file(
    profile_id: str,
    site: str,
    country: str,
    lat: float, lon: float,
    layers: list[dict[str, float]],
    dest: str | Path,
    *,
    salb=.13, slu1=6, sldr=.6, slro=61,
    slnf=1, slpf=1, smhb="IB001", smpx="IB001", smke="IB001",
    soil_data_source="-99", soil_series_name="-99",
    scs_family="FINE, HYPHERTERMIC, VERTIC USTOCHREPTS", scom="BN"
) -> None:

    if len(profile_id) != 10:
        raise ValueError("profile_id must have exactly 10 characters.")

    table = [make_layer(**lay) for lay in layers]

    profile = SoilProfile(
        table=table,
        name=profile_id,
        site=site[:10], country=country[:10],
        lat=lat, long=lon,
        salb=salb, slu1=slu1, sldr=sldr, slro=slro,
        slnf=slnf, slpf=slpf, smhb=smhb, smpx=smpx, smke=smke,
        soil_data_source=soil_data_source,
        soil_clasification="SCL",               
        soil_series_name=soil_series_name,
        scs_family=scs_family,
        scom=scom,
    )

    dest = Path(dest)
    dest.write_text(profile._write_sol(), encoding="utf-8")
    print(f"✔ Profile «{profile_id}» salvo em {dest.resolve()}")

# ----------------------------------------------------------------------
if __name__ == "__main__":
    build_soil_file(
        profile_id="UMVA030003",
        site="umarya",
        country="India",
        lat=23.5, lon=80.75,
        layers=[
            {"slb": 11, "slll": .175, "sdul": .271, "ssat": .415, "srgf": 1,
             "ssks": .43, "sbdm": 1.47, "sloc": .97, "slcl": 24.5, "slsi": 13.2,
             "slhw": 6.7, "scec": 18.5, "slke": .3, "slca": 11.3},
            {"slb": 31, "slll": .226, "sdul": .332, "ssat": .421, "srgf": .657,
             "ssks": .12, "sbdm": 1.46, "sloc": .66, "slcl": 36.4, "slsi": 18.4,
             "slhw": 6.4, "scec": 19.3, "slke": .4, "slca": 12.4},
            {"slb": 50, "slll": .256, "sdul": .348, "ssat": .408, "srgf": .445,
             "ssks": .12, "sbdm": 1.50, "sloc": .50, "slcl": 43.3, "slsi": 11.1,
             "slhw": 6.4, "scec": 24.5, "slke": .5, "slca": 14.3},
            {"slb": 75, "slll": .278, "sdul": .374, "ssat": .423, "srgf": .287,
             "ssks": .06, "sbdm": 1.46, "sloc": .40, "slcl": 48.2, "slsi": 12.9,
             "slhw": 6.4, "scec": 31.3, "slke": .3, "slca": 17.3},
        ],
        dest="UMVA030003.SOL",
    )
