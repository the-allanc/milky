import ast

from griffe.agents.extensions import VisitorExtension, When


class Extension(VisitorExtension):
    when = When.after_all

    def visit_functiondef(self, node):
        if 'cached_property' in [
            d.attr for d in node.decorator_list if isinstance(d, ast.Attribute)
        ]:
            self.visitor.current.members[node.name].labels.update(
                {"property", "cached"}
            )
