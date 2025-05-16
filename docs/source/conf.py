# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys


sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------
project = 'Documentation'
copyright = '2025, Emilia'
author = 'Emilia'
release = '0.1'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',   
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = 'alabaster'

html_theme_options = {
    'show_related': True,
    'sidebar_width': '220px',
}

# Optional: add extra sidebar content
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'relations.html',  # next/prev links
        'searchbox.html',
    ]
}

html_static_path = ['_static']
