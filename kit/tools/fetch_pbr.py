"""Re-download the CC0 Poly Haven PBR set used by rbx/pbr.py (~26 MB, 1k jpg) into assets/tex/pbr/. Run: python3 -I tools/fetch_pbr.py"""
import json, os, urllib.request, sys
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "tex", "pbr")
IDS = {"cobble":"cobblestone_floor_01","brick":"red_brick_03","plaster":"painted_plaster_wall","planks":"brown_planks_05",
 "steel":"metal_plate","asphalt":"asphalt_02","grass":"leafy_grass","concrete":"concrete_pavement","tile":"floor_tiles_02",
 "fabric":"denim_fabric","roof":"clay_roof_tiles_02","woodfloor":"wood_floor","timber":"weathered_peeling_timber"}
log = []
op = urllib.request.build_opener(); op.addheaders=[("User-Agent","rbx-kit-asset-fetch/1.0")]; urllib.request.install_opener(op)
for key, aid in IDS.items():
    d = json.load(urllib.request.urlopen("https://api.polyhaven.com/files/" + aid))
    os.makedirs(f"{OUT}/{key}", exist_ok=True)
    for mp, fn in (("Diffuse","diff"),("nor_gl","nor"),("arm","arm")):
        if mp not in d: print("missing", aid, mp); continue
        u = d[mp]["1k"]["jpg"]["url"]; p = f"{OUT}/{key}/{fn}.jpg"
        if not os.path.exists(p): urllib.request.urlretrieve(u, p)
    log.append(f"- 2026-11-13 PBR texture {aid} (1k jpg diff/nor_gl/arm) -> tex/pbr/{key}/ from Poly Haven, CC0: https://polyhaven.com/a/{aid}")
print("\n".join(log))
