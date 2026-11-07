import importlib


def test_dependencias_importam():
    for nome in ("PySide6", "pyqtgraph"):
        importlib.import_module(nome)


def test_pacote_do_projeto_importa():
    import epidemia  # noqa: F401