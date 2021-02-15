from bob.errors import ParseError
import fnmatch
import platform

# TODO: support more architectures; support musl/dietlibc

# get host architecture
def hostArch(args, **options):
    m = platform.uname().machine
    if m == "x86_64":
        return m
    elif m == "AMD64":
        return "x86_64"
    elif m.startswith("i"):
        return "i386"
    elif m.startswith("aarch64"):
        return "aarch64"
    elif m.startswith("arm"):
        return "arm"
    else:
        raise ParseError("Unsupported host machine: " + m)

# get host autoconf triple
def hostAutoconf(args, **options):
    machine = hostArch(None)
    system = platform.uname().system
    if system == 'Linux':
        return machine + "-linux-gnu"
    elif system.startswith("MSYS_NT"):
        return machine + "-pc-msys"
    elif system == "Windows":
        return machine + "-pc-win32"
    else:
        raise ParseError("Unsupported system: " + system)

# set or replace vendor field in autoconf triplet
def genAutoconf(args, **options):
    if len(args) != 1:
        raise ParseError("$(gen-autoconf,vendor) expects one argument")
    machine, _, system = hostAutoconf(None).partition("-")
    return machine + '-' + args[0] + '-' + system

manifest = {
    'apiVersion' : "0.15",
    'stringFunctions' : {
        "gen-autoconf" : genAutoconf,
        "host-arch" : hostArch,
        "host-autoconf" : hostAutoconf,
    }
}
