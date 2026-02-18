# Configuration file for the Sphinx documentation builder.

import os
import sys

# Добавляем корневую папку проекта в путь, чтобы Sphinx видел модули
sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
project = "Telegram Job Bot"
copyright = "2026, Developer"
author = "Developer"
release = "1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",  # Автоматическое документирование из docstrings
    "sphinx.ext.viewcode",  # Ссылки на исходный код
    "sphinx.ext.napoleon",  # Поддержка Google/NumPy стиля docstrings
    "sphinx.ext.todo",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
language = "ru"

# -- Options for HTML output -------------------------------------------------
try:
    import sphinx_rtd_theme  # noqa: F401

    html_theme = "sphinx_rtd_theme"
except ImportError:
    html_theme = "alabaster"

html_static_path = ["_static"]

# Включаем отображение __init__ метода
autoclass_content = "both"
