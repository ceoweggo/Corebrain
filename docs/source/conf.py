import os
import sys

sys.path.insert(0, os.path.abspath('../..'))

project = 'Corebrain Documentation'
copyright = '2025, Corebrain'
author = 'Corebrain'
release = '0.1'

extensions = [
    'sphinx.ext.autodoc',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'furo'

html_static_path = ['_static']
