from bob.errors import ParseError
import fnmatch
import os
import platform

# TODO: support more architectures; support musl/dietlibc

# get host architecture
def hostArch(args, **options):
    m = os.uname().machine
    if m == "x86_64":
        return m
    elif m.startswith("i"):
        return "i386"
    elif m.startswith("aarch64"):
        return "arm64"
    elif m.startswith("arm"):
        return "arm"
    else:
        raise ParseError("Unsupported host machine: " + m)

# get host autoconf triple
def hostAutoconf(args, **options):
    u = platform.uname()
    if u.system == 'Linux':
        return u.machine + "-linux-gnu"
    elif u.system.startswith("MSYS_NT"):
        return u.machine + "-pc-msys"
    else:
        raise ParseError("Unsupported system: " + u.system)

# set or replace vendor field in autoconf triplet
def genAutoconf(args, **options):
    if len(args) != 1:
        raise ParseError("$(gen-autoconf,vendor) expects one argument")
    u = os.uname()
    return u.machine + '-' + args[0] + '-linux-gnu'

manifest = {
    'apiVersion' : "0.15",
    'stringFunctions' : {
        "gen-autoconf" : genAutoconf,
        "host-arch" : hostArch,
        "host-autoconf" : hostAutoconf,
    }
}
