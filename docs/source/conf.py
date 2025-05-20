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
html_css_files = ['custom.css']
html_static_path = ['_static']

