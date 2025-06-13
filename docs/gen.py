
import re
import sys
import enaml
import inspect
from textwrap import dedent
from os.path import exists, join, abspath


def convert(name):
    # Straight from So
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def make_decls():
    """ """
    from declaracad.occ import api
    widgets = [getattr(api, n) for n in dir(api) if not n.startswith("_")]
    for Widget in widgets:
        example = "No example available."
        try:
            if not inspect.isclass(Widget):
                continue
            mod = Widget.__module__.split(".")[-1]
            for filename in ['{mod}.enaml',
                             '{mod}s.enaml',
                             '{name}.enaml',
                             '{uname}.enaml',
                             '{uname}s.enaml',
                             '{name}s.enaml']:
                path = join('../examples', filename.format(
                    mod=mod, name=Widget.__name__.lower(),
                    uname=convert(Widget.__name__)))
                if exists(path):
                    example = dedent("""

                    .. literalinclude:: ../{path}
                        :language: python
                    """.strip()).format(path=path)
                else:
                    print("{} not found".format(abspath(path)))
        except:
            pass


        try:
            from declaracad.occ.impl.occ_factories import OCC_FACTORIES

            impl = dedent("""
            Implementation
            ----------------------------
            .. autoclass:: {mod.__module__}.{mod.__name__}
               :show-inheritance:
               :members:

            """).format(mod=OCC_FACTORIES[Widget.__name__]())
        except:
            impl = "No implementation found"


        with open('source/decls/{}.rst'.format(Widget.__name__.lower()), 'w') as f:
            f.write(dedent("""
            {w.__name__}
            ========================================

            {ex}

            Declaration
            ----------------------------

            .. autoclass:: {w.__module__}.{w.__name__}
               :show-inheritance:
               :members:

            {impl}
            """).format(w=Widget, impl=impl, ex=example))

    with open('source/decls/index.rst', 'w') as f:
        f.write(dedent("""
        Model Declarations
        ========================================

        .. toctree::
           :maxdepth: 2
           {toc}
        """).format(toc='\n   '.join([
            '{N} <{n}>'.format(N=w.__name__, n=w.__name__.lower())
            for w in widgets
        ])))


def make_apis():
    from declaracad.occ import api

    apis = [
        getattr(api, n) for n in dir(api)
        if not n.startswith("_")
    ]
    for api in apis:
        with open('source/apis/{}_{}.rst'.format(
                platform, api.__name__.lower()), 'w') as f:
            f.write(dedent("""
            {cls.__name__}
            ========================================

            .. autoclass:: {cls.__module__}.{cls.__name__}

            """.format(cls=api)))

    with open('source/apis/index.rst', 'w') as f:
        f.write(dedent("""
        APIs
        ========================================

        .. toctree::
           :maxdepth: 2
           {toc}
        """).format(toc='\n   '.join([
            '{N} <{p}_{n}>'.format(
                N=api.__name__,
                p=api.__module__.split('.')[1],
                n=api.__name__.lower())
            for api in apis
        ])))



def main():
    make_decls()
    #make_apis()


if __name__ == '__main__':
    sys.path.append('../examples')
    with enaml.imports():
        main()
