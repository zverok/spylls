# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('.'))

import sphinx_rtd_theme
import coderead


# -- Project information -----------------------------------------------------

project = 'Spyll'
copyright = '2020, Victor Shepelev'
author = 'Victor Shepelev'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    # 'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc.typehints',
    # 'sphinxcontrib.fulltoc',
    'sphinx_rtd_theme',
    'code_include.extension',
    'coderead'
]

autodoc_typehints = 'description'

autodoc_default_options = {
    'member-order': 'bysource'
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# html_theme = 'pyramid'
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_css_files = [
    'css/coderead.css',
]

modindex_common_prefix = ['spyll.hunspell.', 'spyll.hunspell.data.', 'spyll.hunspell.readers.', 'spyll.hunspell.algo.']
