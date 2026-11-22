"""
Gera o diagrama conceitual do Grafo Multiescala para o artigo LaTeX.
Inspirado no rascunho do Prado: dois paises como poligonos, vertices internos
conectados por raio adaptativo, rotas aereas cruzando entre eles com pesos.
"""
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 2600, 1700
img = Image.new("RGB", (W, H), (255, 255, 255))
draw = ImageDraw.Draw(img)

# --- Cores ---
C_BG_A       = (232, 242, 252)
C_BOR_A      = (52, 101, 164)
C_BG_B       = (234, 247, 237)
C_BOR_B      = (42, 128, 70)
C_NODE_A     = (30, 76, 150)
C_NODE_B     = (30, 115, 60)
C_EDGE_INT   = (160, 170, 182)
C_EDGE_FLIGHT= (200, 40, 40)
C_TEXT       = (25, 30, 40)
C_MUTED      = (90, 105, 120)
C_BOX_BG     = (253, 253, 255)
C_BOX_BOR    = (180, 185, 200)

# --- Fontes ---
FNT = "C:/Windows/Fonts/segoeui.ttf"
FNT_B = "C:/Windows/Fonts/segoeuib.ttf"
FNT_I = "C:/Windows/Fonts/segoeuii.ttf"
try:
    f_title  = ImageFont.truetype(FNT_B, 44)
    f_sub    = ImageFont.truetype(FNT_I, 29)
    f_node   = ImageFont.truetype(FNT_B, 27)
    f_label  = ImageFont.truetype(FNT_B, 31)
    f_body   = ImageFont.truetype(FNT,   27)
    f_form   = ImageFont.truetype(FNT_B, 27)
    f_leg    = ImageFont.truetype(FNT,   25)
except:
    f_title = f_sub = f_node = f_label = f_body = f_form = f_leg = ImageFont.load_default()

# ============================================================
# 1. POLIGONOS DOS PAISES
# ============================================================
poly_a = [(230,145),(590,115),(1060,138),(1480,125),(1790,168),
          (1870,315),(1820,505),(1610,565),(1090,580),(580,548),
          (230,518),(165,335)]
draw.polygon(poly_a, fill=C_BG_A, outline=C_BOR_A, width=4)

poly_b = [(270,1075),(690,1048),(1210,1058),(1670,1038),(1880,1115),
          (1920,1278),(1810,1462),(1440,1505),(940,1512),(490,1490),
          (210,1428),(175,1248)]
draw.polygon(poly_b, fill=C_BG_B, outline=C_BOR_B, width=4)

# Titulos
draw.text((248, 162), "País A  (Polígono Territorial i)", fill=C_NODE_A, font=f_label)
draw.text((248, 205), "área Areai  |  população pi  |  vértices ni  ∝  √pi", fill=C_MUTED, font=f_sub)

draw.text((248, 1478), "País B  (Polígono Territorial j)", fill=C_NODE_B, font=f_label)
draw.text((248, 1521), "área Areaj  |  população pj  |  vértices nj  ∝  √pj", fill=C_MUTED, font=f_sub)

# ============================================================
# 2. VERTICES
# ============================================================
NA = {"v1":(390,335), "v2":(710,278), "v3":(615,462),
      "v4":(1015,355), "v5":(1335,258), "v6":(1375,478), "v7":(1670,368)}
NB = {"u1":(415,1258), "u2":(672,1158), "u3":(755,1382),
      "u4":(1115,1240), "u5":(1405,1158), "u6":(1460,1382), "u7":(1728,1278)}

# Circulo de raio adaptativo (ilustrativo em torno de v4)
cx, cy = NA["v4"]
R_VIS = 268
draw.ellipse((cx-R_VIS, cy-R_VIS, cx+R_VIS, cy+R_VIS),
             outline=(160, 195, 230), width=2)
draw.text((cx+118, cy-195),
          "raio adaptativo ri ≈ √(d̄ef / (π·ρi))", fill=(100,130,175), font=f_leg)

# Arestas internas Pais A
for u, v in [("v1","v2"),("v1","v3"),("v2","v3"),("v2","v4"),
             ("v3","v4"),("v4","v5"),("v4","v6"),("v5","v6"),("v5","v7"),("v6","v7")]:
    draw.line([NA[u], NA[v]], fill=C_EDGE_INT, width=4)

# Arestas internas Pais B
for u, v in [("u1","u2"),("u1","u3"),("u2","u3"),("u2","u4"),
             ("u3","u4"),("u4","u5"),("u4","u6"),("u5","u6"),("u5","u7"),("u6","u7")]:
    draw.line([NB[u], NB[v]], fill=C_EDGE_INT, width=4)

# Arestas aereas (curvas Bezier)
def bezier_points(p1, p2, curve=60):
    mx = (p1[0]+p2[0])/2 + curve
    my = (p1[1]+p2[1])/2
    pts = []
    for i in range(41):
        t = i/40
        bx = (1-t)**2*p1[0] + 2*(1-t)*t*mx + t**2*p2[0]
        by = (1-t)**2*p1[1] + 2*(1-t)*t*my + t**2*p2[1]
        pts.append((bx, by))
    return pts

flight_pairs = [("v3","u2",-50),("v4","u5",40),("v6","u6",-30)]
for na, nb, cur in flight_pairs:
    pts = bezier_points(NA[na], NB[nb], cur)
    for i in range(len(pts)-1):
        if (i//2)%2 == 0:
            draw.line([pts[i], pts[i+1]], fill=C_EDGE_FLIGHT, width=5)

# Bolinhas dos vertices
R_NODE = 24
for name, pos in NA.items():
    draw.ellipse((pos[0]-R_NODE,pos[1]-R_NODE,pos[0]+R_NODE,pos[1]+R_NODE),
                 fill=(255,255,255), outline=C_NODE_A, width=5)
    draw.text((pos[0]-14, pos[1]-16), name, fill=C_NODE_A, font=f_node)

for name, pos in NB.items():
    draw.ellipse((pos[0]-R_NODE,pos[1]-R_NODE,pos[0]+R_NODE,pos[1]+R_NODE),
                 fill=(255,255,255), outline=C_NODE_B, width=5)
    draw.text((pos[0]-14, pos[1]-16), name, fill=C_NODE_B, font=f_node)

# ============================================================
# 3. CAIXA CENTRAL - FORMULAS  (deslocada para a direita, sem sobrepor a legenda)
# ============================================================
bx0, by0, bx1, by1 = 660, 625, 1900, 980
draw.rectangle([bx0,by0,bx1,by1], fill=C_BOX_BG, outline=C_BOX_BOR, width=3)
draw.rectangle([bx0,by0,bx0+10,by1], fill=C_EDGE_FLIGHT)   # barra decorativa

tx, ty = bx0+30, by0+22
draw.text((tx, ty), "Acoplamento Internacional — Malha Aérea (OpenFlights)", fill=C_EDGE_FLIGHT, font=f_label)
ty += 46
draw.text((tx, ty), "1.  Multiplicidade de arestas:", fill=C_TEXT, font=f_body)
ty += 33
draw.text((tx+22, ty), "kij = min( kmax ,  ⌈ routesij / escala ⌉ )   —   sorteadas com semente determinística", fill=C_MUTED, font=f_form)
ty += 46
draw.text((tx, ty), "2.  Peso logarítmico e probabilidade de transmissão:", fill=C_TEXT, font=f_body)
ty += 33
draw.text((tx+22, ty), "wij = ln(1 + routesij) / ln(1 + max routes)     →     pij = 1 − exp(−β · wij)", fill=C_NODE_A, font=f_form)
ty += 46
draw.text((tx, ty), "3.  Distância Efetiva para Dijkstra  (Brockmann & Helbing, 2013):", fill=C_TEXT, font=f_body)
ty += 33
draw.text((tx+22, ty), "cij = −ln( min( pij ,  0,999 ) )      [custo aditivo positivo — maximiza prod. das probs.]", fill=(175,35,30), font=f_form)

# ============================================================
# 4. LEGENDA  (posicionada na esquerda, sem tocar na caixa de fórmulas)
# ============================================================
lx, ly = 30, 650
draw.rectangle([lx,ly,lx+395,ly+350], fill=(255,255,255), outline=(205,210,220), width=2)
draw.text((lx+18, ly+16), "LEGENDA", fill=C_TEXT, font=f_label)

draw.line([(lx+22,ly+82),(lx+88,ly+82)], fill=C_EDGE_INT, width=4)
draw.text((lx+105, ly+68), "Aresta Interna (d ≤ ri)\nContato por proximidade física", fill=C_TEXT, font=f_leg)

draw.line([(lx+22,ly+168),(lx+88,ly+168)], fill=C_EDGE_FLIGHT, width=4)
draw.text((lx+105, ly+154), "Rota Aérea Internacional\nConexão de longa distância", fill=C_TEXT, font=f_leg)

draw.ellipse((lx+36,ly+248,lx+68,ly+280), fill=(255,255,255), outline=C_NODE_A, width=4)
draw.text((lx+105, ly+244), "Vértice — Indivíduo/Grupo\nEstado SEIRD no tempo t", fill=C_TEXT, font=f_leg)

# ============================================================
# 5. SALVAR
# ============================================================
out = "docs/latex-article/figures/esquema_grafo_multiescala.png"
img.save(out, "PNG", dpi=(300,300))
print(f"OK: {out}")
