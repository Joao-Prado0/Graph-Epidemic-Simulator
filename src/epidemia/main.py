"""Ponto de entrada principal do Simulador de Epidemias em Redes (M5).

Inicializa a aplicação Qt, instancia a janela principal e executa o event loop.
Pode ser executado diretamente com:
    python -m epidemia.main
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from epidemia.ui.main_window import MainWindow


def main() -> int:
    """Função principal de inicialização da interface gráfica."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("Simulador de Epidemias em Redes")
    app.setOrganizationName("Graph-Epidemic-Simulator")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
