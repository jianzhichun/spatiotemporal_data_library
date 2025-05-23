import os
import sys
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../spatiotemporal_data_library'))

project = 'spatiotemporal_data_library'
copyright = '2024 Zao Zhang'
author = 'Zao Zhang'
release = '0.1.0'

# Language settings
language = 'en'
locale_dirs = ['locale/']
gettext_compact = False

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_copybutton',
    'sphinx_design',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Theme settings
html_theme = 'furo'
html_theme_options = {
    'navigation_with_keys': True,
    'top_of_page_button': None,
    'light_css_variables': {
        'color-brand-primary': '#0077cc',
        'color-brand-content': '#0077cc',
    },
    'dark_css_variables': {
        'color-brand-primary': '#0099ff',
        'color-brand-content': '#0099ff',
    },
}

# Additional theme settings
html_static_path = ['_static']
html_css_files = ['custom.css']
html_js_files = ['custom.js']

# Intersphinx settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
}

autodoc_mock_imports = ["xarray", "pandas", "cdsapi", "netCDF4"] 