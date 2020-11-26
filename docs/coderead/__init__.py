# The ideas of how to attach it are stolen from
# https://github.com/Chilipp/autodocsumm/blob/master/autodocsumm/__init__.py

import sphinx

from sphinx.ext.autodoc import MethodDocumenter, FunctionDocumenter, get_documenters, bool_option

from typing import Any

CODEREAD_TEMPLATE = """
.. raw:: html

    <div class="coderead">
        <div class="coderead-toggle">
            <a onclick="$(this).parents('.coderead').toggleClass('coderead-on')">code</a>
        </div>
        <div class="coderead-content">

.. code-include:: {{replace}}

.. raw:: html

    </div></div>
"""


class CodeReadMethodDocumenter(MethodDocumenter):
    priority = MethodDocumenter.priority + 0.1

    option_spec = MethodDocumenter.option_spec.copy()

    def generate(self, *args, **kwargs):
        super().generate(*args, **kwargs)

        content = CODEREAD_TEMPLATE.replace('{{replace}}', f":method:`{self.fullname}`")

        for i, ln in enumerate(content.splitlines()):
            self.add_line(ln, "coderead", i)

class CodeReadFunctionDocumenter(FunctionDocumenter):
    priority = FunctionDocumenter.priority + 0.1

    option_spec = FunctionDocumenter.option_spec.copy()

    def generate(self, *args, **kwargs):
        super().generate(*args, **kwargs)

        content = CODEREAD_TEMPLATE.replace('{{replace}}', f":func:`{self.fullname}`")

        for i, ln in enumerate(content.splitlines()):
            self.add_line(ln, "coderead", i)


def setup(app):

    registry = get_documenters(app)
    for cls in [CodeReadMethodDocumenter, CodeReadFunctionDocumenter]:
        if not issubclass(registry.get(cls.objtype), cls):
            app.add_autodocumenter(cls, override=True)

    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
