from bob.errors import ParseError
import os, os.path
import platform
import subprocess

def msbuild(args, **options):
    system = platform.uname().system
    if system.startswith("MSYS_NT") or system.startswith("MINGW"):
        isMSYS = True
    elif system == "Windows":
        isMSYS = False
    else:
        raise ParseError("Unsupported system for $(msbuild,...): " + system)

    try:
        vswargs = (os.path.join(os.environ["ProgramFiles(x86)"],
                                "Microsoft Visual Studio/Installer/vswhere.exe"),
                '-find', 'MSBuild\**\Bin\MSBuild.exe',
                '-latest',
                '-products', '*',
                '-requires', 'Microsoft.Component.MSBuild')

        path = subprocess.check_output(vswargs, universal_newlines=True).strip()
        if isMSYS:
            path = subprocess.check_output(["cygpath", "-u", "-p", path], universal_newlines=True).strip()
        path = subprocess.check_output(["dirname", path], universal_newlines=True).strip()

        return path
    except (OSError, subprocess.SubprocessError) as e:
        raise ParseError("$(msbuild) failed: " + str(e))

manifest = {
    'apiVersion' : "0.15",
    'stringFunctions' : {
        "msbuild": msbuild
    },
}
