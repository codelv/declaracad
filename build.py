"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file COPYING.txt, distributed with this software.

Created on Jan 12, 2018

@author
"""
import re
import sh
import os
import sys
import textwrap
from glob import glob
from contextlib import contextmanager

PY_VER = f"{sys.version_info.major}.{sys.version_info.minor}"

CONTROL_TEMPLATE = """
Package: {name}
Section: {section}
Architecture: all
Maintainer: {maintainer}
Standards-Version: 4.0.0
Homepage: {homepage}
Depends: {depends}
Priority: optional
Version: {version}
Description: {short_desc}
 {full_desc}

"""

@contextmanager
def cd(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def make_deb(cfg):
    """ """
    print("Building installer...")
    build_dir = 'build/{name}-{version}'.format(**cfg)
    cfg.update({'build_dir': build_dir})
    install_dir = '{build_dir}/usr/share/{name}'.format(**cfg)
    desktop_dir = '{build_dir}/usr/share/applications/'.format(**cfg)
    cfg.update({'install_dir': install_dir,
                'desktop_dir': desktop_dir})

    os.makedirs(build_dir)

    with cd(build_dir):
        os.makedirs('DEBIAN')

        #: Write control
        with open('DEBIAN/control', 'w') as f:
            f.write(CONTROL_TEMPLATE.format(**cfg))

    #: Write
    os.makedirs(install_dir)
    print(sh.cp('-R', glob(f'build/exe.linux-x86_64-{PY_VER}/*'), install_dir))

    #: Make a simlink to /usr/local/bin
    #print(sh.ln('-sf', '{install_dir}/{name}'.format(**cfg),
    #            '{install_dir}/usr/local/bin/{name}'.format(**cfg)))

    #: Make a desktop icon /usr/share/applications
    os.makedirs(desktop_dir)
    print(sh.cp('{name}/packaging/declaracad.desktop'.format(**cfg), desktop_dir))

    #: Prepare
    try:
        print(sh.chown('-R', 'root:root', build_dir))
    except:
        pass

    #: Build it
    deb = sh.Command('dpkg-deb')
    print(deb('--build', build_dir))


def main(cfg):
    """ Build and run the app
    
    """
    print("Clean...")
    sh.rm('-Rf', glob('build/*'))

    #: Build
    print("Build...")
    try:
        print(sh.python('release.py', 'build', _err_to_out=True))
    except Exception as e:
        for line in e.stdout.split(b"\n"):
            print(line.decode())
        raise

    #: Enter build
    # print("Trim...")
    with cd(f'build/exe.linux-x86_64-{PY_VER}/'):
    #     #: Trim out crap that's not needed
    #     for p in [
    #             #'libicu*',
    #             'lib/PyQt6/Qt',
    #             'lib/PyQt6/QtB*',
    #             'lib/PyQt6/QtDes*',
    #             'lib/PyQt6/QtH*',
    #             'lib/PyQt6/QtL*',
    #             'lib/PyQt6/QtM*',
    #             'lib/PyQt6/QtN*',
    #             'lib/PyQt6/QtPos*',
    #             'lib/PyQt6/QtT*',
    #             #'lib/PyQt6/QtO*',
    #             'lib/PyQt6/QtSe*',
    #             'lib/PyQt6/QtSq*',
    #             'lib/PyQt6/QtQ*',
    #             #'lib/PyQt6/QtWeb*',
    #             'lib/PyQt6/QtX*',
    #             #'platforms',
    #             #'imageformats',
    #             'libQt6Net*',
    #             'libQt6Pos*',
    #             'libQt6Q*',
    #             'libQt6Sq*',
    #             'libQt6O*',
    #             'libQt6T*',
    #             'libQt6Web*',
    #             #'declaracad',
    #             'libQt6X*'
    #             ]:
    #         try:
    #             sh.rm('-Rf', glob(p))
    #         except Exception as e:
    #             print(e)

        #: Test the app
        print("Launching...")
        cmd = sh.Command('./{name}'.format(**cfg))
        try:
            print(cmd(_err_to_out=True))
        except Exception as e:
            for line in e.stdout.split(b"\n"):
                print(line.decode())
            raise


    #: If good then build installer
    # make_deb(cfg)

def find_version():
    with open("declaracad/__init__.py") as f:
        for line in f:
            m = re.search(r'version = [\'"](.+)["\']', line)
            if m:
                return m.group(1)
    raise Exception("Could not find version in declaracad/__init__.py")

if __name__ == '__main__':

    cfg = {
        'name': 'declaracad',
        'version': find_version(),
        'maintainer': 'CodeLV <frmdstryr@gmail.com>',
        'section': 'engineering',
        'depends': '',
        'homepage': 'https://github.com/codelv/declaracad',
        'short_desc': 'A declarative and parametric 3D modeling application',
        'full_desc': "\n ".join(textwrap.dedent(
            """
            Written using python and enaml.
            """.strip()).split("\n")),
    }
    main(cfg)
