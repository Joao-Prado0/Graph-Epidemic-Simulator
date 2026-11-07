"""Prova de conceito do ambiente (provisoria).

Valida PySide6, QPainter em lote, QThread com buffer de estados e pyqtgraph.
Os estados sao aleatorios: nao ha modelo epidemiologico aqui.
"""

import random
import sys
import time

import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

N_VERTICES = 8000
SEMENTE = 42
# Estados: 0=S, 1=E, 2=I, 3=R, 4=D
CORES = [
    QColor("#4caf50"),
    QColor("#ffb300"),
    QColor("#e53935"),
    QColor("#42a5f5"),
    QColor("#212121"),
]
PESOS = [0.70, 0.05, 0.15, 0.08, 0.02]


class Simulador(QThread):
    dia_gravado = Signal(int)

    def __init__(self, historico: list, n: int, semente: int):
        super().__init__()
        self._historico = historico
        self._n = n
        self._rng = random.Random(semente)

    def run(self):
        while not self.isInterruptionRequested():
            estados = bytearray(self._rng.choices(range(5), weights=PESOS, k=self._n))
            self._historico.append(estados)
            self.dia_gravado.emit(len(self._historico) - 1)
            self.msleep(100)


class Mapa(QWidget):
    def __init__(self, historico: list):
        super().__init__()
        rng = random.Random(SEMENTE)
        self._pontos = [(rng.random(), rng.random()) for _ in range(N_VERTICES)]
        self._historico = historico
        self._dia = 0
        self.quadros = 0
        self.setMinimumSize(640, 360)

    def mostrar_dia(self, dia: int):
        self._dia = dia

    def paintEvent(self, _evento):
        pintor = QPainter(self)
        pintor.fillRect(self.rect(), QColor("#eceff1"))
        if self._historico:
            estados = self._historico[self._dia]
            largura, altura = self.width(), self.height()
            grupos = [QPolygonF() for _ in CORES]
            for (x, y), estado in zip(self._pontos, estados, strict=True):
                grupos[estado].append(QPointF(x * largura, y * altura))
            for cor, grupo in zip(CORES, grupos, strict=True):
                caneta = QPen(cor)
                caneta.setWidth(4)
                caneta.setCapStyle(Qt.RoundCap)
                pintor.setPen(caneta)
                pintor.drawPoints(grupo)
            self.quadros += 1
        pintor.end()


class Janela(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulador de Epidemias - verificacao do ambiente")
        self.historico: list[bytearray] = []
        self.infectados: list[int] = []

        self.mapa = Mapa(self.historico)
        self.grafico = pg.PlotWidget(title="Infectados (I) por dia")
        self.curva = self.grafico.plot([], [], pen=pg.mkPen("#e53935", width=2))
        self.rotulo = QLabel("FPS: -")

        caixa = QVBoxLayout()
        caixa.addWidget(self.mapa, 3)
        caixa.addWidget(self.grafico, 1)
        caixa.addWidget(self.rotulo)
        centro = QWidget()
        centro.setLayout(caixa)
        self.setCentralWidget(centro)

        self.simulador = Simulador(self.historico, N_VERTICES, SEMENTE)
        self.simulador.dia_gravado.connect(self._novo_dia)
        self.simulador.start()

        self._t0 = time.perf_counter()
        self.timer_quadro = QTimer(self)
        self.timer_quadro.timeout.connect(self.mapa.update)
        self.timer_quadro.start(16)
        self.timer_fps = QTimer(self)
        self.timer_fps.timeout.connect(self._atualizar_fps)
        self.timer_fps.start(1000)

    def _novo_dia(self, dia: int):
        self.mapa.mostrar_dia(dia)
        self.infectados.append(self.historico[dia].count(2))
        self.curva.setData(self.infectados)

    def _atualizar_fps(self):
        agora = time.perf_counter()
        fps = self.mapa.quadros / (agora - self._t0)
        self.mapa.quadros = 0
        self._t0 = agora
        texto = f"{N_VERTICES} vertices | FPS: {fps:.1f} | dias gravados: {len(self.historico)}"
        self.rotulo.setText(texto)
        self.setWindowTitle(f"Simulador de Epidemias - {fps:.1f} FPS")
        print(texto)

    def closeEvent(self, evento):
        self.simulador.requestInterruption()
        self.simulador.wait(2000)
        super().closeEvent(evento)


def main() -> int:
    app = QApplication(sys.argv)
    janela = Janela()
    janela.resize(900, 700)
    janela.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
