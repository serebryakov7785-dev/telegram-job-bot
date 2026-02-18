import os
import sys
from unittest.mock import MagicMock, patch

# Ensure the project root is in the path, similar to how conf.py does it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_conf_imports_and_variables():
    """
    Tests that the conf.py file can be imported and has basic variables set.
    This is a simple test to ensure the file is syntactically correct.
    """
    import conf

    assert conf.project == "Telegram Job Bot"
    assert conf.author == "Developer"
    assert "sphinx.ext.autodoc" in conf.extensions
    assert conf.language == "ru"


def test_conf_theme_logic():
    """
    Tests the theme selection logic in conf.py.
    """
    from importlib import reload

    # Case 1: sphinx_rtd_theme is available
    with patch.dict("sys.modules", {"sphinx_rtd_theme": MagicMock()}):
        import conf

        reload(conf)
        assert conf.html_theme == "sphinx_rtd_theme"

    # Case 2: sphinx_rtd_theme is NOT available
    with patch.dict("sys.modules", {"sphinx_rtd_theme": None}):
        import conf

        reload(conf)
        assert conf.html_theme == "alabaster"
