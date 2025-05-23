import os
import sys

sys.path.insert(0, os.path.abspath('../..'))

project = 'Corebrain Documentation'
copyright = '2025, Corebrain'
author = 'Corebrain'
release = '0.1'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',        
    'sphinx.ext.viewcode',   
    'sphinx_copybutton',        
    'sphinx_design', 
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'furo'
html_css_files = [
    "custom.css",
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap",
]
html_static_path = ['_static']

html_title = "Corebrain Documentation 0.1"

