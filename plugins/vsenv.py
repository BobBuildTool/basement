from bob.errors import ParseError
import os, os.path
import subprocess
import glob

cache = {}

def vsvars2019(args, **options):
    if len(args) < 2:
        raise ParseError("$(vsvars2019,VAR,ARCH,...) expects at least two arguments")

    try:
        varname = args[0]
        vsvars_args = args[1:]
        vswargs = (os.path.join(os.environ["ProgramFiles(x86)"],
                                "Microsoft Visual Studio/Installer/vswhere.exe"),
                '-property', 'installationPath',
                '-version', '[16.0,17.0)',
                '-products', '*',
                '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64')

        tag = tuple(vsvars_args)
        if tag not in cache:
            r = subprocess.check_output(vswargs, universal_newlines=True).strip()
            vsvarsall = os.path.join(r, "VC/Auxiliary/Build/vcvarsall.bat")
            r = subprocess.check_output([vsvarsall] + vsvars_args + ['&&', 'set'],
                universal_newlines=True)
            env = {}
            for l in r.splitlines():
                k,sep,v = l.strip().partition("=")
                k = k.upper()
                if k == 'PATH':
                    # convert to POSIX path to be mergeable
                    v = subprocess.check_output(["cygpath", "-u", "-p", v], universal_newlines=True).strip()
                env[k] = v
            cache[tag] = env

        return cache[tag][varname]
    except (OSError, subprocess.SubprocessError) as e:
        raise ParseError("$(vsvars2019) failed: " + str(e))

manifest = {
    'apiVersion' : "0.15",
    'stringFunctions' : {
        "vsvars2019" : vsvars2019
    },
}
