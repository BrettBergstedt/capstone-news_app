# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Django bootstrap --------------------------------------------------------
# Autodoc imports the real application modules. Django models raise an
# AppRegistryNotReady error unless settings are configured and the app registry
# is loaded first, so this block has to run before any `automodule` directive.
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newsproject.settings")

import django  # noqa: E402

django.setup()

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'The Daily Brief'
copyright = '2026, Brett Bergstedt'
author = 'Brett Bergstedt'

version = '1.0'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'en'

# -- Extension configuration -------------------------------------------------
# Keep documentation in the order the code declares things, rather than
# alphabetical, so a reader follows the models top to bottom.
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
add_module_names = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
