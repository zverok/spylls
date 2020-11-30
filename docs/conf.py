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

project = 'Spylls'
copyright = '2020, Victor Shepelev'
author = 'Victor Shepelev'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    # 'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc.typehints',
    # 'sphinxcontrib.fulltoc', -- included in rtd_theme
    'sphinx_rtd_theme',
    'code_include.extension',
    'coderead',
    'sphinx.ext.linkcode',
    # 'sphinxcontrib.spelling'
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

add_module_names = False

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

modindex_common_prefix = ['spylls.hunspell.', 'spylls.hunspell.data.', 'spylls.hunspell.readers.', 'spylls.hunspell.algo.']

# The code below, I suspect, is godless unholy abomination.
# Yet it works.
# The idea is by linkcode's param (which is just a name of the object) to produce proper GitHub link to code
# We do it by eval'ing the code object and then inspect'ing it to get source file and line
# Sue me!

import spylls
import inspect

# Git commit fetching is stolen from
# https://stackoverflow.com/questions/61579937/how-to-access-the-git-commit-id-in-sphinxs-conf-py
import subprocess
commit_id = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode('ascii')

def linkcode_resolve(domain, info):
    try:
        obj = eval(f"{info['module']}.{info['fullname']}")
        path = inspect.getsourcefile(obj).replace(os.path.abspath('..'), '')
        lineno = inspect.getsourcelines(obj)[1]
    except:
        # Attributes and other similar stuff can't be resolved with inspect
        return None

    return f'http://github.com/zverok/spylls/blob/{commit_id}{path}#L{lineno}'
