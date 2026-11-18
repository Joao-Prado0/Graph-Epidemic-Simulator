"""Visualizador de mapa global com QPainter em lote (M5 — RF22, RF26).

Renderiza os polígonos dos países pré-calculados em QPainterPath com cores
definidas pelo status epidemiológico dominante do dia (ou intensidade de casos
no fluxo real), histerese de exibição de nós (40 px / 36 px), zoom (+/-),
arraste (pan), botão de ajuste automático e tooltip ao passar o mouse.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from epidemia.app.panel_metrics import inspect_vertex_metrics
from epidemia.core.timeline.protocol import (
    FLAG_ISOLATED,
    FLAG_VACCINATED,
    STATE_MASK,
    STATE_R,
)
from epidemia.ui.styles import (
    COLOR_HEX_ISOLATED,
    COLOR_ISOLATED,
    COLOR_RECOVERED_VAC,
    STATE_COLORS,
    VERTEX_HIDE_THRESHOLD_PX,
    VERTEX_MARKER_RADIUS,
    VERTEX_SHOW_THRESHOLD_PX,
    color_for_real_cases_per_100k,
    format_number_br,
)

if TYPE_CHECKING:
    from epidemia.core.timeline.protocol import CountryCounts
    from epidemia.world.geometry import CountryGeometry
    from epidemia.world.world import World


def _compute_country_deg_width(geom: CountryGeometry, bbox: QRectF) -> float:
    """Calcula a largura efetiva em graus de longitude tratando o antimeridiano (D15)."""
    if not geom.polygons:
        return max(0.5, bbox.width())

    part_widths: list[float] = []
    for exterior, _holes in geom.polygons:
        if not exterior:
            continue
        xs = [float(pt[0]) for pt in exterior]
        w = max(xs) - min(xs)
        if w > 180.0:
            xs_shifted = [x + 360.0 if x < 0.0 else x for x in xs]
            w = max(xs_shifted) - min(xs_shifted)
        part_widths.append(w)

    if not part_widths:
        return max(0.5, bbox.width())

    if bbox.width() > 180.0:
        # País dividido no antimeridiano (D15): soma as partes divididas
        return max(0.5, min(180.0, sum(part_widths)))

    # Para países com territórios ultramarinos distantes (ex: FRA), usa a parte principal
    return max(0.5, max(part_widths))


class MapCanvas(QWidget):
    """Área gráfica que desenha o mapa com QPainter em lote."""

    vertex_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._world: World | None = None
        self._vertex_bytes: bytes | None = None
        self._country_counts: Sequence[CountryCounts] | None = None
        self._country_counts_map: dict[str, CountryCounts] = {}
        self._is_real_flow: bool = False

        # Geometrias pré-calculadas: iso3 -> QPainterPath
        self._country_paths: dict[str, QPainterPath] = {}
        self._country_bboxes: dict[str, QRectF] = {}
        self._country_deg_widths: dict[str, float] = {}
        self._country_visible_nodes: dict[str, bool] = {}

        # Transformação de visualização (pan e zoom)
        self._zoom: float = 3.0  # Pixels por grau de longitude
        self._pan_x: float = 0.0
        self._pan_y: float = 0.0
        self._center_lon: float = 0.0
        self._center_lat: float = 0.0

        # Controle de arraste e clique com o mouse
        self._is_dragging: bool = False
        self._press_mouse_pos = QPointF(0, 0)
        self._last_mouse_pos = QPointF(0, 0)

    def set_world(self, world: World | None) -> None:
        """Configura o mundo sintético ou real e pré-calcula os caminhos dos polígonos."""
        self._world = world
        self._country_paths.clear()
        self._country_bboxes.clear()
        self._country_deg_widths.clear()
        self._country_visible_nodes.clear()

        if world is None:
            self.update()
            return

        all_min_lon = 180.0
        all_max_lon = -180.0
        all_min_lat = 90.0
        all_max_lat = -90.0

        for iso3, geom in world.country_geometries.items():
            path = QPainterPath()
            for poly in geom.polygons:
                exterior, holes = poly
                if exterior:
                    p0 = exterior[0]
                    path.moveTo(float(p0[0]), float(p0[1]))
                    for pt in exterior[1:]:
                        path.lineTo(float(pt[0]), float(pt[1]))
                    path.closeSubpath()
                for hole in holes:
                    if hole:
                        p0 = hole[0]
                        path.moveTo(float(p0[0]), float(p0[1]))
                        for pt in hole[1:]:
                            path.lineTo(float(pt[0]), float(pt[1]))
                        path.closeSubpath()

            bbox = path.boundingRect()
            self._country_paths[iso3] = path
            self._country_bboxes[iso3] = bbox
            self._country_deg_widths[iso3] = _compute_country_deg_width(geom, bbox)
            self._country_visible_nodes[iso3] = False

            if bbox.width() > 0 and bbox.height() > 0:
                all_min_lon = min(all_min_lon, bbox.left())
                all_max_lon = max(all_max_lon, bbox.right())
                all_min_lat = min(all_min_lat, bbox.top())
                all_max_lat = max(all_max_lat, bbox.bottom())

        if all_min_lon < all_max_lon and all_min_lat < all_max_lat:
            self._center_lon = (all_min_lon + all_max_lon) / 2.0
            self._center_lat = (all_min_lat + all_max_lat) / 2.0
        else:
            self._center_lon = 0.0
            self._center_lat = 0.0

        self.fit_map()

    def set_day_data(
        self,
        vertex_bytes: bytes | None,
        country_counts: Sequence[CountryCounts] | None = None,
        is_real_flow: bool = False,
    ) -> None:
        """Atualiza os dados de estado para renderização do dia."""
        self._vertex_bytes = vertex_bytes
        self._country_counts = country_counts
        if country_counts is not None:
            self._country_counts_map = {c.iso3: c for c in country_counts}
        else:
            self._country_counts_map = {}
        self._is_real_flow = is_real_flow
        self.update()

    def fit_map(self) -> None:
        """Ajusta o enquadramento do mapa para caber perfeitamente no widget."""
        self._pan_x = 0.0
        self._pan_y = 0.0
        if not self._country_bboxes:
            self._zoom = 3.0
            self.update()
            return

        total_rect = QRectF()
        for bbox in self._country_bboxes.values():
            total_rect = total_rect.united(bbox)

        w = self.width() if self.width() > 50 else 800
        h = self.height() if self.height() > 50 else 500

        scale_x = (w * 0.85) / max(1.0, total_rect.width())
        scale_y = (h * 0.85) / max(1.0, total_rect.height())
        self._zoom = max(0.5, min(scale_x, scale_y, 40.0))
        self.update()

    def zoom_in(self) -> None:
        """Aumenta o zoom em 25%."""
        self._zoom = min(200.0, self._zoom * 1.25)
        self.update()

    def zoom_out(self) -> None:
        """Diminui o zoom em 20%."""
        self._zoom = max(0.2, self._zoom / 1.25)
        self.update()

    def _get_transform(self) -> QTransform:
        transform = QTransform()
        transform.translate(self.width() / 2.0 + self._pan_x, self.height() / 2.0 + self._pan_y)
        transform.scale(self._zoom, -self._zoom)  # Inverte eixo Y para coordenadas de latitude
        transform.translate(-self._center_lon, -self._center_lat)
        return transform

    def _calculate_dominant_status_color(self, iso3: str) -> QColor:
        """Determina a cor do país pelo status dominante de CountryCounts (M3)."""
        if self._world is None:
            return QColor("#2b2d31")

        c_info = self._country_counts_map.get(iso3)
        if c_info is not None:
            max_comp = max(
                c_info.susceptible,
                c_info.exposed,
                c_info.infected,
                c_info.total_recovered,
                c_info.deceased,
            )
            if c_info.isolated > 0 and c_info.isolated >= max_comp:
                return COLOR_ISOLATED
            dom = c_info.dominant_state
            if dom == STATE_R and c_info.recovered_vaccinated > c_info.recovered_natural:
                return COLOR_RECOVERED_VAC
            return STATE_COLORS.get(dom, QColor("#2b2d31"))

        if self._vertex_bytes is None:
            return QColor("#2b2d31")

        verts = self._world.country_vertices.get(iso3, [])
        if not verts:
            return QColor("#2b2d31")

        state_counts: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        iso_count = 0
        for u in verts:
            if u < len(self._vertex_bytes):
                b = self._vertex_bytes[u]
                if b & FLAG_ISOLATED:
                    iso_count += 1
                st = b & STATE_MASK
                state_counts[st] = state_counts.get(st, 0) + 1

        if iso_count > 0 and iso_count >= max(state_counts.values()):
            return COLOR_ISOLATED

        priority = (2, 1, 4, 3, 0)
        dominant_st = max(priority, key=lambda s: (state_counts.get(s, 0), -priority.index(s)))
        return STATE_COLORS.get(dominant_st, QColor("#2b2d31"))

    def _calculate_real_flow_color(self, iso3: str) -> QColor:
        """Determina a cor do país pela intensidade de casos no fluxo real (A12)."""
        if self._country_counts is None or self._world is None:
            return QColor("#2b2d31")

        c_info = self._country_counts_map.get(iso3)
        if c_info is None or c_info.cases <= 0:
            return QColor("#202225")

        pop = self._world.country_populations.get(iso3, 100_000)
        cases_per_100k = (c_info.cases / max(1, pop)) * 100_000.0
        return color_for_real_cases_per_100k(cases_per_100k)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # Fundo do oceano / mapa
            painter.fillRect(self.rect(), QColor("#141619"))

            if self._world is None:
                painter.setPen(QColor("#777777"))
                painter.drawText(
                    self.rect(), Qt.AlignmentFlag.AlignCenter, "Nenhum cenário carregado."
                )
                return

            transform = self._get_transform()
            painter.setTransform(transform)

            # 1. Renderização dos polígonos dos países
            outline_pen = QPen(QColor("#4a5568"), 1.0 / self._zoom)
            outline_pen.setCosmetic(True)
            country_fill_colors: dict[str, QColor] = {}

            for iso3, path in self._country_paths.items():
                if self._is_real_flow:
                    fill_color = self._calculate_real_flow_color(iso3)
                else:
                    fill_color = self._calculate_dominant_status_color(iso3)
                country_fill_colors[iso3] = fill_color

                painter.setPen(outline_pen)
                painter.setBrush(QBrush(fill_color))
                painter.drawPath(path)

                # Atualização da histerese de nós (40 px entrada / 36 px saída)
                deg_w = self._country_deg_widths.get(iso3, 1.0)
                screen_width_px = deg_w * self._zoom
                currently_visible = self._country_visible_nodes.get(iso3, False)

                if not currently_visible and screen_width_px >= VERTEX_SHOW_THRESHOLD_PX:
                    self._country_visible_nodes[iso3] = True
                elif currently_visible and screen_width_px < VERTEX_HIDE_THRESHOLD_PX:
                    self._country_visible_nodes[iso3] = False

            # 2. Renderização dos vértices em lote com drawPoints (Arquitetura 4.1, RNF02)
            point_diam_px = max(3.0, VERTEX_MARKER_RADIUS * 1.4)
            positions = self._world.vertex_positions

            if self._is_real_flow:
                # Arquitetura 4.1: no fluxo real, os vértices recebem a cor do polígono do país
                for iso3, is_vis in self._country_visible_nodes.items():
                    if not is_vis:
                        continue
                    verts = self._world.country_vertices.get(iso3, [])
                    if not verts:
                        continue
                    poly_pts = QPolygonF(
                        [
                            QPointF(positions[u][0], positions[u][1])
                            for u in verts
                            if u < len(positions)
                        ]
                    )
                    base_col = country_fill_colors.get(iso3, QColor("#4a5568"))
                    pen = QPen(base_col.lighter(135), point_diam_px)
                    pen.setCosmetic(True)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    painter.setPen(pen)
                    painter.drawPoints(poly_pts)
            elif self._vertex_bytes is not None:
                v_bytes = self._vertex_bytes
                n_bytes = len(v_bytes)
                batches: dict[int, QPolygonF] = {}
                color_table: dict[int, QColor] = {
                    0: STATE_COLORS[0],
                    1: STATE_COLORS[1],
                    2: STATE_COLORS[2],
                    3: STATE_COLORS[3],
                    4: STATE_COLORS[4],
                    5: COLOR_RECOVERED_VAC,
                    6: QColor(COLOR_HEX_ISOLATED),
                }

                for iso3, is_vis in self._country_visible_nodes.items():
                    if not is_vis:
                        continue
                    verts = self._world.country_vertices.get(iso3, [])
                    for u in verts:
                        if u >= len(positions):
                            continue
                        pt = positions[u]
                        b = v_bytes[u] if u < n_bytes else 0
                        if b & FLAG_ISOLATED:
                            key = 6
                        elif (b & STATE_MASK) == STATE_R and (b & FLAG_VACCINATED):
                            key = 5
                        else:
                            key = b & STATE_MASK

                        poly_group = batches.get(key)
                        if poly_group is None:
                            poly_group = QPolygonF()
                            batches[key] = poly_group
                        poly_group.append(QPointF(pt[0], pt[1]))

                for key, poly_group in batches.items():
                    pen = QPen(color_table.get(key, QColor("#ffffff")), point_diam_px)
                    pen.setCosmetic(True)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    painter.setPen(pen)
                    painter.drawPoints(poly_group)
        finally:
            painter.end()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom com a roda do mouse centrado no ponteiro."""
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else (1.0 / 1.15)
        new_zoom = max(0.2, min(300.0, self._zoom * factor))
        self._zoom = new_zoom
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._press_mouse_pos = event.position()
            self._last_mouse_pos = event.position()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            delta = event.position() - self._last_mouse_pos
            self._last_mouse_pos = event.position()
            self._pan_x += delta.x()
            self._pan_y += delta.y()
            self.update()
        else:
            self._handle_tooltip(event.position())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragging = self._is_dragging
            self._is_dragging = False
            drag_dist = (event.position() - self._press_mouse_pos).manhattanLength()
            if was_dragging and drag_dist <= 5.0:
                self._handle_click_inspection(event.position())

    def _find_nearest_vertex(self, geo_pos: QPointF, max_px_radius: float = 10.0) -> int | None:
        """Localiza o vértice mais próximo da coordenada clicada (RF26)."""
        if self._world is None:
            return None
        max_deg_dist = max_px_radius / max(0.2, self._zoom)
        max_deg_sq = max_deg_dist * max_deg_dist
        best_u: int | None = None
        best_d2 = max_deg_sq

        gx = geo_pos.x()
        gy = geo_pos.y()
        positions = self._world.vertex_positions

        for iso3, path in self._country_paths.items():
            if not path.contains(geo_pos) and not self._country_visible_nodes.get(iso3, False):
                continue
            for u in self._world.country_vertices.get(iso3, ()):
                if u >= len(positions):
                    continue
                dx = positions[u][0] - gx
                dy = positions[u][1] - gy
                d2 = dx * dx + dy * dy
                if d2 <= best_d2:
                    best_d2 = d2
                    best_u = u

        if best_u is not None:
            return best_u

        # Se clicou dentro de um país sem acertar em cima do marcador, retorna o 1º nó do país
        for iso3, path in self._country_paths.items():
            if path.contains(geo_pos):
                verts = self._world.country_vertices.get(iso3, ())
                if verts:
                    return verts[0]
        return None

    def _handle_click_inspection(self, pos: QPointF) -> None:
        """Inspeciona o vértice clicado e emite sinal vertex_clicked (RF26)."""
        if self._world is None:
            return
        transform = self._get_transform()
        inv_transform, invertible = transform.inverted()
        if not invertible:
            return

        geo_pos = inv_transform.map(pos)
        u = self._find_nearest_vertex(geo_pos)
        if u is None:
            return

        self.vertex_clicked.emit(u)
        info = inspect_vertex_metrics(self._world, u, self._vertex_bytes)
        flags: list[str] = []
        if info.is_isolated:
            flags.append("Isolado")
        if info.is_vaccinated:
            flags.append("Vacinado")
        flags_str = f" ({', '.join(flags)})" if flags else ""
        text = (
            f"<b>Vértice #{info.vertex_id} — {info.country_name} ({info.iso3})</b><br/>"
            f"Estado: {info.state_name}{flags_str}<br/>"
            f"Grau (k): {info.degree} · Agrupamento local (C): "
            f"{format_number_br(info.local_clustering, 3)}"
        )
        QToolTip.showText(self.mapToGlobal(pos.toPoint()), text, self)

    def _handle_tooltip(self, pos: QPointF) -> None:
        """Exibe tooltip ao passar o mouse sobre o polígono de um país."""
        if not self._country_paths or self._world is None:
            return

        transform = self._get_transform()
        inv_transform, invertible = transform.inverted()
        if not invertible:
            return

        geo_pos = inv_transform.map(pos)

        for iso3, path in self._country_paths.items():
            if path.contains(geo_pos):
                c_name = self._world.country_names.get(iso3, iso3)
                c_pop = self._world.country_populations.get(iso3, 0)
                n_verts = len(self._world.country_vertices.get(iso3, []))
                iso_tag = (
                    "<br/><i>Sem rota aérea internacional (D16)</i>"
                    if iso3 in self._world.isolated_countries
                    else ""
                )
                text = (
                    f"<b>{c_name} ({iso3})</b><br/>"
                    f"População: {format_number_br(c_pop)}<br/>"
                    f"Vértices: {n_verts}{iso_tag}"
                )
                QToolTip.showText(self.mapToGlobal(pos.toPoint()), text, self)
                return

        QToolTip.hideText()


class MapView(QWidget):
    """Container com canvas do mapa e barra de controles de zoom."""

    vertex_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Barra de ferramentas superior de navegação
        self._toolbar_widget = QWidget(self)
        toolbar = QHBoxLayout(self._toolbar_widget)
        toolbar.setContentsMargins(8, 6, 8, 4)

        btn_fit = QPushButton("⛶ Ajustar mapa")
        btn_fit.setToolTip("Enquadra todo o cenário na visualização")
        btn_fit.clicked.connect(self._on_fit_clicked)
        toolbar.addWidget(btn_fit)

        toolbar.addStretch(1)

        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedWidth(32)
        btn_zoom_out.setToolTip("Diminuir zoom")
        btn_zoom_out.clicked.connect(self._on_zoom_out_clicked)
        toolbar.addWidget(btn_zoom_out)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedWidth(32)
        btn_zoom_in.setToolTip("Aumentar zoom")
        btn_zoom_in.clicked.connect(self._on_zoom_in_clicked)
        toolbar.addWidget(btn_zoom_in)

        main_layout.addWidget(self._toolbar_widget)

        self._canvas = MapCanvas(self)
        self._canvas.vertex_clicked.connect(self.vertex_clicked.emit)
        main_layout.addWidget(self._canvas, stretch=1)

    def set_toolbar_visible(self, visible: bool) -> None:
        """Exibe ou oculta a barra interna de zoom para evitar duplicidade com a janela."""
        self._toolbar_widget.setVisible(visible)

    def set_world(self, world: World | None) -> None:
        self._canvas.set_world(world)

    def set_day_data(
        self,
        vertex_bytes: bytes | None,
        country_counts: Sequence[CountryCounts] | None = None,
        is_real_flow: bool = False,
    ) -> None:
        self._canvas.set_day_data(vertex_bytes, country_counts, is_real_flow)

    @property
    def is_real_flow(self) -> bool:
        """Indica se o mapa está renderizando o fluxo de pandemias reais."""
        return self._canvas._is_real_flow

    def _on_fit_clicked(self) -> None:
        self._canvas.fit_map()

    def _on_zoom_in_clicked(self) -> None:
        self._canvas.zoom_in()

    def _on_zoom_out_clicked(self) -> None:
        self._canvas.zoom_out()
