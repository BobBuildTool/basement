from bob.errors import ParseError
import fnmatch
import functools
import platform

# TODO: support more architectures; support musl/dietlibc

def normalizedHostMachine():
    m = platform.uname().machine
    if m == "AMD64":
        return "x86_64"
    elif m.startswith("i"):
        return "i386"
    else:
        return m

# get host architecture
def hostArch(args, **options):
    m = normalizedHostMachine()
    if m.startswith("aarch64"):
        return "arm64"
    elif m.startswith("arm"):
        return "arm"
    else:
        return m

# get host autoconf triple
def hostAutoconf(args, **options):
    machine = normalizedHostMachine()
    system = platform.uname().system
    if system == 'Linux':
        return machine + "-linux-gnu"
    elif system.startswith("MSYS_NT"):
        return machine + "-pc-msys"
    elif system.startswith("MINGW64_NT"):
        return "x86_64-w64-mingw32"
    elif system.startswith("MINGW32_NT"):
        return "i686-w64-mingw32"
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

RUST_TARGETS = (
    ("aarch64-unknown-linux-gnu",       "aarch64-",     "-linux-gnu"),
    ("armv7-unknown-linux-gnueabihf",   "arm",          "-linux-gnueabihf"),
    ("i686-unknown-linux-gnu",          "i",            "-linux-gnu"),
    ("x86_64-unknown-linux-gnu",        "x86_64-",      "-linux-gnu"),
)

@functools.lru_cache
def rustcTargetMatch(triple):
    for target, prefix, postfix in RUST_TARGETS:
        if triple.startswith(prefix) and triple.endswith(postfix):
            return target
    return "UNKNOWN"

# transform triple into known rustc targets
def rustcTarget(args, **options):
    if len(args) != 1:
        raise ParseError("$(rustc-target,triple) expects one argument")
    return rustcTargetMatch(args[0])

# Cross toolchain CPU feature handling
# X86 only cares about -march=...  CPUs than lack SSE2 are not supported here!
# Based on GCC 14 documentation.
AMD64_FEATURES = {
    "x86-64"             : set(),
    "x86-64-v2"          : {"sse3", "ssse3", "sse4.1", "sse4.2"},
    "x86-64-v3"          : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "x86-64-v4"          : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "core2"              : {"sse3", "ssse3"},
    "nehalem"            : {"sse3", "ssse3", "sse4.1", "sse4.2"},
    "westmere"           : {"sse3", "ssse3", "sse4.1", "sse4.2"},
    "sandybridge"        : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx"},
    "ivybridge"          : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx"},
    "haswell"            : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "broadwell"          : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "skylake"            : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "bonnell"            : {"sse3", "ssse3"},
    "silvermont"         : {"sse3", "ssse3", "sse4.1", "sse4.2"},
    "goldmont"           : {"sse3", "ssse3", "sse4.1", "sse4.2"},
    "goldmont-plus"      : {"sse3", "ssse3", "sse4.1", "sse4.2"},
    "tremont"            : {"sse3", "ssse3", "sse4.1", "sse4.2"},
    "sierraforest"       : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "grandridge"         : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "knl"                : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "knm"                : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "skylake-avx512"     : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "icelake-client"     : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "icelake-server"     : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "cascadelake"        : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "cooperlake"         : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "tigerlake"          : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "sapphirerapids"     : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "alderlake"          : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "rocketlake"         : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "graniterapids"      : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "graniterapids-d"    : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
    "bdver1"             : {"sse3", "ssse3"},
    "bdver2"             : {"sse3", "ssse3", "sse4.1", "sse4.2"},
    "bdver3"             : {"sse3", "ssse3", "sse4.1", "sse4.2"},
    "bdver4"             : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "znver1"             : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "znver2"             : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "znver3"             : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2"},
    "znver4"             : {"sse3", "ssse3", "sse4.1", "sse4.2", "avx", "avx2", "avx512"},
}

# Based on GCC 15
# Taken from gcc/config/aarch64/aarch64-option-extensions.def
ARM64_FEATURES = {
    "aes"           : ("AES",           {"SIMD"}, set(), set()),
    "bf16"          : ("BF16",          {"FP"}, {"SIMD"}, set()),
    "cpa"           : ("CPA",           set(), set(), set()),
    "crc"           : ("CRC",           set(), set(), set()),
    "crypto"        : ("CRYPTO",        {"AES", "SHA2"}, set(), {"AES", "SHA2", "SM4"}),
    "cssc"          : ("CSSC",          set(), set(), set()),
    "d128"          : ("D128",          {"LSE128"}, set(), set()),
    "dotprod"       : ("DOTPROD",       {"SIMD"}, set(), set()),
    "f32mm"         : ("F32MM",         {"SVE"}, set(), set()),
    "f64mm"         : ("F64MM",         {"SVE"}, set(), set()),
    "faminmax"      : ("FAMINMAX",      {"SIMD"}, set(), set()),
    "fcma"          : ("FCMA",          {"SIMD"}, set(), set()),
    "flagm"         : ("FLAGM",         set(), set(), set()),
    "flagm2"        : ("FLAGM2",        {"FLAGM"}, set(), set()),
    "fp"            : ("FP",            set(), set(), set()),
    "fp16"          : ("F16",           {"FP"}, set(), {"F16FML"}),
    "fp16fml"       : ("F16FML",        set(), {"F16"}, set()),
    "fp8"           : ("FP8",           {"SIMD"}, set(), set()),
    "fp8dot2"       : ("FP8DOT2",       {"FP8"}, set(), set()),
    "fp8dot4"       : ("FP8DOT4",       {"FP8"}, set(), set()),
    "fp8fma"        : ("FP8FMA",        {"FP8"}, set(), set()),
    "frintts"       : ("FRINTTS",       {"FP"}, set(), set()),
    "gcs"           : ("GCS",           set(), set(), set()),
    "i8mm"          : ("I8MM",          {"SIMD"}, set(), set()),
    "jscvt"         : ("JSCVT",         {"FP"}, set(), set()),
    "ls64"          : ("LS64",          set(), set(), set()),
    "lse"           : ("LSE",           set(), set(), set()),
    "lse128"        : ("LSE128",        {"LSE"}, set(), set()),
    "lut"           : ("LUT",           {"SIMD"}, set(), set()),
    "memtag"        : ("MEMTAG",        set(), set(), set()),
    "mops"          : ("MOPS",          set(), set(), set()),
    "pauth"         : ("PAUTH",         set(), set(), set()),
    "predres"       : ("PREDRES",       set(), set(), set()),
    "profile"       : ("PROFILE",       set(), set(), set()),
    "rcpc"          : ("RCPC",          set(), set(), set()),
    "rcpc2"         : ("RCPC2",         {"RCPC"}, set(), set()),
    "rcpc3"         : ("RCPC3",         {"RCPC2"}, set(), set()),
    "rdma"          : ("RDMA",          set(), {"SIMD"}, set()),
    "rng"           : ("RNG",           set(), set(), set()),
    "sb"            : ("SB",            set(), set(), set()),
    "sha2"          : ("SHA2",          {"SIMD"}, set(), set()),
    "sha3"          : ("SHA3",          {"SHA2"}, set(), set()),
    "simd"          : ("SIMD",          {"FP"}, set(), set()),
    "sm4"           : ("SM4",           {"SIMD"}, set(), set()),
    "sme"           : ("SME",           {"BF16", "SVE2"}, set(), set()),
    "sme-b16b16"    : ("SME_B16B16",    {"SME2", "SVE_B16B16"}, set(), set()),
    "sme-f16f16"    : ("SME_F16F16",    {"SME2"}, set(), set()),
    "sme-f64f64"    : ("SME_F64F64",    {"SME"}, set(), set()),
    "sme-i16i64"    : ("SME_I16I64",    {"SME"}, set(), set()),
    "sme2"          : ("SME2",          {"SME"}, set(), set()),
    "sme2p1"        : ("SME2p1",        {"SME2"}, set(), set()),
    "ssbs"          : ("SSBS",          set(), set(), set()),
    "ssve-fp8dot2"  : ("SSVE_FP8DOT2",  {"SME2", "FP8"}, set(), set()),
    "ssve-fp8dot4"  : ("SSVE_FP8DOT4",  {"SME2", "FP8"}, set(), set()),
    "ssve-fp8fma"   : ("SSVE_FP8FMA",   {"SME2", "FP8"}, set(), set()),
    "sve"           : ("SVE",           {"SIMD", "F16", "FCMA"}, set(), set()),
    "sve-b16b16"    : ("SVE_B16B16",    set(), set(), set()),
    "sve2"          : ("SVE2",          {"SVE"}, set(), set()),
    "sve2-aes"      : ("SVE2_AES",      {"SVE2", "AES"}, set(), set()),
    "sve2-bitperm"  : ("SVE2_BITPERM",  {"SVE2"}, set(), set()),
    "sve2-sha3"     : ("SVE2_SHA3",     {"SVE2", "SHA3"}, set(), set()),
    "sve2-sm4"      : ("SVE2_SM4",      {"SVE2", "SM4"}, set(), set()),
    "sve2p1"        : ("SVE2p1",        {"SVE2"}, set(), set()),
    "the"           : ("THE",           set(), set(), set()),
    "tme"           : ("TME",           set(), set(), set()),
    "wfxt"          : ("WFXT",          set(), set(), set()),
    "xs"            : ("XS",            set(), set(), set()),
}

# Taken from gcc/config/aarch64/aarch64-arches.def
ARM64_ARCHES = {
    "armv8-a"   :  ("V8A",       8,  {"SIMD"}),
    "armv8.1-a" :  ("V8_1A",     8,  {"V8A", "LSE", "CRC", "RDMA"}),
    "armv8.2-a" :  ("V8_2A",     8,  {"V8_1A"}),
    "armv8.3-a" :  ("V8_3A",     8,  {"V8_2A", "PAUTH", "RCPC", "FCMA", "JSCVT"}),
    "armv8.4-a" :  ("V8_4A",     8,  {"V8_3A", "F16FML", "DOTPROD", "FLAGM", "RCPC2"}),
    "armv8.5-a" :  ("V8_5A",     8,  {"V8_4A", "SB", "SSBS", "PREDRES", "FRINTTS", "FLAGM2"}),
    "armv8.6-a" :  ("V8_6A",     8,  {"V8_5A", "I8MM", "BF16"}),
    "armv8.7-a" :  ("V8_7A",     8,  {"V8_6A", "WFXT", "XS"}),
    "armv8.8-a" :  ("V8_8A",     8,  {"V8_7A", "MOPS"}),
    "armv8.9-a" :  ("V8_9A",     8,  {"V8_8A", "CSSC"}),
    "armv8-r"   :  ("V8R"  ,     8,  {"V8_4A"}),
    "armv9-a"   :  ("V9A"  ,     9,  {"V8_5A", "SVE2"}),
    "armv9.1-a" :  ("V9_1A",     9,  {"V8_6A", "V9A"}),
    "armv9.2-a" :  ("V9_2A",     9,  {"V8_7A", "V9_1A"}),
    "armv9.3-a" :  ("V9_3A",     9,  {"V8_8A", "V9_2A"}),
    "armv9.4-a" :  ("V9_4A",     9,  {"V8_9A", "V9_3A"}),
    "armv9.5-a" :  ("V9_5A",     9,  {"V9_4A", "CPA", "FAMINMAX", "LUT"}),
}

# Taken from gcc/config/aarch64/aarch64-cores.def
ARM64_CPUS = {
    "cortex-a34" :              ("V8A",   {"CRC"}),
    "cortex-a35" :              ("V8A",   {"CRC"}),
    "cortex-a53" :              ("V8A",   {"CRC"}),
    "cortex-a57" :              ("V8A",   {"CRC"}),
    "cortex-a72" :              ("V8A",   {"CRC"}),
    "cortex-a73" :              ("V8A",   {"CRC"}),
    "thunderx" :                ("V8A",   {"CRC", "CRYPTO"}),
    "thunderxt88" :             ("V8A",   {"CRC", "CRYPTO"}),
    "thunderxt88p1" :           ("V8A",   {"CRC", "CRYPTO"}),
    "octeontx" :                ("V8A",   {"CRC", "CRYPTO"}),
    "octeontx81" :              ("V8A",   {"CRC", "CRYPTO"}),
    "octeontx83" :              ("V8A",   {"CRC", "CRYPTO"}),
    "thunderxt81" :             ("V8A",   {"CRC", "CRYPTO"}),
    "thunderxt83" :             ("V8A",   {"CRC", "CRYPTO"}),
    "ampere1" :                 ("V8_6A", {"F16", "RNG", "AES", "SHA3"}),
    "ampere1a" :                ("V8_6A", {"F16", "RNG", "AES", "SHA3", "SM4", "MEMTAG"}),
    "ampere1b" :                ("V8_7A", {"F16", "RNG", "AES", "SHA3", "SM4", "MEMTAG", "CSSC"}),
    "emag" :                    ("V8A",   {"CRC", "CRYPTO"}),
    "xgene1" :                  ("V8A",   set()),
    "falkor" :                  ("V8A",   {"CRC", "CRYPTO", "RDMA"}),
    "qdf24xx" :                 ("V8A",   {"CRC", "CRYPTO", "RDMA"}),
    "exynos-m1" :               ("V8A",   {"CRC", "CRYPTO"}),
    "phecda" :                  ("V8A",   {"CRC", "CRYPTO"}),
    "thunderx2t99p1" :          ("V8_1A", {"CRYPTO"}),
    "vulcan" :                  ("V8_1A", {"CRYPTO"}),
    "thunderx2t99" :            ("V8_1A", {"CRYPTO"}),
    "cortex-a55" :              ("V8_2A", {"F16", "RCPC", "DOTPROD"}),
    "cortex-a75" :              ("V8_2A", {"F16", "RCPC", "DOTPROD"}),
    "cortex-a76" :              ("V8_2A", {"F16", "RCPC", "DOTPROD"}),
    "cortex-a76ae" :            ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS"}),
    "cortex-a77" :              ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS"}),
    "cortex-a78" :              ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS", "PROFILE"}),
    "cortex-a78ae" :            ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS", "PROFILE"}),
    "cortex-a78c" :             ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS", "PROFILE", "FLAGM", "PAUTH"}),
    "cortex-a65" :              ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS"}),
    "cortex-a65ae" :            ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS"}),
    "cortex-x1" :               ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS", "PROFILE"}),
    "cortex-x1c" :              ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS", "PROFILE", "PAUTH"}),
    "neoverse-n1" :             ("V8_2A", {"F16", "RCPC", "DOTPROD", "PROFILE"}),
    "ares" :                    ("V8_2A", {"F16", "RCPC", "DOTPROD", "PROFILE"}),
    "neoverse-e1" :             ("V8_2A", {"F16", "RCPC", "DOTPROD", "SSBS"}),
    "octeontx2" :               ("V8_2A", {"CRYPTO", "PROFILE"}),
    "octeontx2t98" :            ("V8_2A", {"CRYPTO", "PROFILE"}),
    "octeontx2t96" :            ("V8_2A", {"CRYPTO", "PROFILE"}),
    "octeontx2t93" :            ("V8_2A", {"CRYPTO", "PROFILE"}),
    "octeontx2f95" :            ("V8_2A", {"CRYPTO", "PROFILE"}),
    "octeontx2f95n" :           ("V8_2A", {"CRYPTO", "PROFILE"}),
    "octeontx2f95mm" :          ("V8_2A", {"CRYPTO", "PROFILE"}),
    "a64fx" :                   ("V8_2A", {"F16", "SVE"}),
    "fujitsu-monaka" :          ("V9_3A", {"F16", "FP8", "LS64", "RNG", "CRYPTO", "SVE2_AES", "SVE2_BITPERM", "SVE2_SHA3", "SVE2_SM4"}),
    "tsv110" :                  ("V8_2A", {"CRYPTO", "F16"}),
    "thunderx3t110" :           ("V8_3A", {"CRYPTO", "SM4", "SHA3", "F16FML"}),
    "neoverse-v1" :             ("V8_4A", {"SVE", "I8MM", "BF16", "PROFILE", "SSBS", "RNG"}),
    "zeus" :                    ("V8_4A", {"SVE", "I8MM", "BF16", "PROFILE", "SSBS", "RNG"}),
    "neoverse-512tvb" :         ("V8_4A", {"SVE", "I8MM", "BF16", "PROFILE", "SSBS", "RNG"}),
    "saphira" :                 ("V8_4A", {"CRYPTO"}),
    "oryon-1" :                 ("V8_6A", {"CRYPTO", "SM4", "SHA3", "F16"}),
    "cortex-a57.cortex-a53" :   ("V8A",   {"CRC"}),
    "cortex-a72.cortex-a53" :   ("V8A",   {"CRC"}),
    "cortex-a73.cortex-a35" :   ("V8A",   {"CRC"}),
    "cortex-a73.cortex-a53" :   ("V8A",   {"CRC"}),
    "cortex-a75.cortex-a55" :   ("V8_2A", {"F16", "RCPC", "DOTPROD"}),
    "cortex-a76.cortex-a55" :   ("V8_2A", {"F16", "RCPC", "DOTPROD"}),
    "cortex-r82" :              ("V8R",   set()),
    "cortex-r82ae" :            ("V8R",   set()),
    "cortex-a510" :             ("V9A",   {"SVE2_BITPERM", "MEMTAG", "I8MM", "BF16"}),
    "cortex-a520" :             ("V9_2A", {"SVE2_BITPERM", "MEMTAG"}),
    "cortex-a520ae" :           ("V9_2A", {"SVE2_BITPERM", "MEMTAG"}),
    "cortex-a710" :             ("V9A",   {"SVE2_BITPERM", "MEMTAG", "I8MM", "BF16"}),
    "cortex-a715" :             ("V9A",   {"SVE2_BITPERM", "MEMTAG", "I8MM", "BF16"}),
    "cortex-a720" :             ("V9_2A", {"SVE2_BITPERM", "MEMTAG", "PROFILE"}),
    "cortex-a720ae" :           ("V9_2A", {"SVE2_BITPERM", "MEMTAG", "PROFILE"}),
    "cortex-a725" :             ("V9_2A", {"SVE2_BITPERM", "MEMTAG", "PROFILE"}),
    "cortex-x2" :               ("V9A",   {"SVE2_BITPERM", "MEMTAG", "I8MM", "BF16"}),
    "cortex-x3" :               ("V9A",   {"SVE2_BITPERM", "MEMTAG", "I8MM", "BF16"}),
    "cortex-x4" :               ("V9_2A", {"SVE2_BITPERM", "MEMTAG", "PROFILE"}),
    "cortex-x925" :             ("V9_2A", {"SVE2_BITPERM", "MEMTAG", "PROFILE"}),
    "neoverse-n2" :             ("V9A",   {"I8MM", "BF16", "SVE2_BITPERM", "RNG", "MEMTAG", "PROFILE"}),
    "cobalt-100" :              ("V9A",   {"I8MM", "BF16", "SVE2_BITPERM", "RNG", "MEMTAG", "PROFILE"}),
    "neoverse-n3" :             ("V9_2A", {"SVE2_BITPERM", "RNG", "MEMTAG", "PROFILE"}),
    "neoverse-v2" :             ("V9A",   {"I8MM", "BF16", "SVE2_BITPERM", "RNG", "MEMTAG", "PROFILE"}),
    "grace" :                   ("V9A",   {"I8MM", "BF16", "SVE2_BITPERM", "SVE2_AES", "SVE2_SHA3", "SVE2_SM4", "PROFILE"}),
    "neoverse-v3" :             ("V9_2A", {"SVE2_BITPERM", "RNG", "LS64", "MEMTAG", "PROFILE"}),
    "neoverse-v3ae" :           ("V9_2A", {"SVE2_BITPERM", "RNG", "LS64", "MEMTAG", "PROFILE"}),
    "demeter" :                 ("V9A",   {"I8MM", "BF16", "SVE2_BITPERM", "RNG", "MEMTAG", "PROFILE"}),
    "generic" :                 ("V8A",   set()),
    "generic-armv8-a" :         ("V8A",   set()),
    "generic-armv9-a" :         ("V9A",   set()),
}

# Computed lazily
ARM64_DEPS = {}
ARM64_RDEPS = {}

def arm64GetAllDeps(flag, graph):
    if not ARM64_DEPS:
        for (k, deps, on, off) in ARM64_FEATURES.values():
            ARM64_DEPS[k] = deps
            ARM64_RDEPS[k] = set()
        for (k, vsn, deps) in ARM64_ARCHES.values():
            ARM64_DEPS[k] = deps
            ARM64_RDEPS[k] = set()
        for k, deps in ARM64_DEPS.items():
            for d in deps:
                ARM64_RDEPS[d].add(k)

    ret = set([flag])
    for d in graph[flag]:
        ret |= arm64GetAllDeps(d, graph)
    return ret

def arm64ResolveOptions(flags, options):
    for opt in (options.split('+') if options else []):
        if opt.startswith('no'):
            remove = arm64GetAllDeps(ARM64_FEATURES[opt[2:]][0], ARM64_RDEPS)
            for r in ARM64_FEATURES[opt[2:]][3]:
                remove |= arm64GetAllDeps(r, ARM64_RDEPS)
            flags -= remove
        else:
            add = arm64GetAllDeps(ARM64_FEATURES[opt][0], ARM64_DEPS)
            for a in ARM64_FEATURES[opt][2]:
                add |= arm64GetAllDeps(a, ARM64_DEPS)
            flags |= add

    return flags

@functools.lru_cache
def arm64FlagsFromArch(arch):
    arch, _, options = arch.partition('+')
    arch_flag, arch_vsn, arch_flags = ARM64_ARCHES[arch]
    flags = arm64GetAllDeps(arch_flag, ARM64_DEPS)
    return arm64ResolveOptions(flags, options)

@functools.lru_cache
def arm64FlagsFromCpu(cpu):
    cpu, _, options = cpu.partition('+')
    cpu_flag, cpu_deps = ARM64_CPUS[cpu]
    flags = arm64GetAllDeps(cpu_flag, ARM64_DEPS)
    for d in cpu_deps:
        flags |= arm64GetAllDeps(d, ARM64_DEPS)
    return arm64ResolveOptions(flags, options)

# Taken from gcc/config/arm/arm-cpus.in and converted automatically by
# plugins/update/convert-gcc-arm.py...

ARM_FGROUPS = {'ALL_CRYPTO': {'crypto'},
               'ALL_FP': {'ALL_FPU_INTERNAL', 'ALL_FPU_EXTERNAL', 'ALL_SIMD'},
               'ALL_FPU_EXTERNAL': {'bf16', 'fp16'},
               'ALL_FPU_INTERNAL': {'ALL_SIMD_INTERNAL', 'fp16conv', 'fp_dbl', 'fpv5',
                                    'vfpv2', 'vfpv3', 'vfpv4'},
               'ALL_QUIRKS': {'quirk_aes_1742098', 'quirk_armv6kz', 'quirk_cm3_ldrd',
                              'quirk_no_asmcpu', 'quirk_no_volatile_ce', 'quirk_vlldm',
                              'xscale'},
               'ALL_SIMD': {'ALL_SIMD_INTERNAL', 'ALL_SIMD_EXTERNAL'},
               'ALL_SIMD_EXTERNAL': {'i8mm', 'fp16fml', 'dotprod'},
               'ALL_SIMD_INTERNAL': {'neon', 'ALL_CRYPTO', 'fp_d32'},
               'ARMv4': {'notm', 'armv4'},
               'ARMv4t': {'ARMv4', 'thumb'},
               'ARMv5t': {'ARMv4t', 'armv5t'},
               'ARMv5te': {'ARMv5t', 'armv5te'},
               'ARMv5tej': {'ARMv5te'},
               'ARMv6': {'armv6', 'be8', 'ARMv5te'},
               'ARMv6j': {'ARMv6'},
               'ARMv6k': {'armv6k', 'ARMv6'},
               'ARMv6kz': {'ARMv6k', 'quirk_armv6kz'},
               'ARMv6m': {'armv4', 'armv6', 'thumb', 'armv5t', 'be8', 'armv5te'},
               'ARMv6t2': {'thumb2', 'ARMv6'},
               'ARMv6z': {'ARMv6'},
               'ARMv6zk': {'ARMv6k'},
               'ARMv7': {'thumb2', 'armv7', 'ARMv6m'},
               'ARMv7a': {'armv6k', 'notm', 'ARMv7'},
               'ARMv7em': {'ARMv7m', 'armv7em'},
               'ARMv7m': {'tdiv', 'ARMv7'},
               'ARMv7r': {'ARMv7a', 'tdiv'},
               'ARMv7ve': {'lpae', 'adiv', 'ARMv7a', 'tdiv', 'mp', 'sec'},
               'ARMv8_1a': {'crc32', 'armv8_1', 'ARMv8a'},
               'ARMv8_1m_main': {'ARMv8m_main', 'armv8_1m_main'},
               'ARMv8_2a': {'ARMv8_1a', 'armv8_2'},
               'ARMv8_3a': {'ARMv8_2a', 'armv8_3'},
               'ARMv8_4a': {'armv8_4', 'ARMv8_3a'},
               'ARMv8_5a': {'ARMv8_4a', 'predres', 'sb', 'armv8_5'},
               'ARMv8_6a': {'ARMv8_5a', 'armv8_6'},
               'ARMv8a': {'armv8', 'ARMv7ve'},
               'ARMv8m_base': {'cmse', 'armv8', 'tdiv', 'ARMv6m'},
               'ARMv8m_main': {'ARMv7m', 'cmse', 'armv8'},
               'ARMv8r': {'ARMv8a'},
               'ARMv9a': {'armv9', 'ARMv8_5a'},
               'CRYPTO': {'NEON', 'crypto'},
               'DOTPROD': {'NEON', 'dotprod'},
               'FP_ARMv8': {'FP_D32', 'FPv5'},
               'FP_D32': {'fp_d32', 'FP_DBL'},
               'FP_DBL': {'fp_dbl'},
               'FPv5': {'fpv5', 'VFPv4'},
               'IGNORE_FOR_MULTILIB': {'cdecp0', 'cdecp1', 'cdecp2', 'cdecp3', 'cdecp4',
                                       'cdecp5', 'cdecp6', 'cdecp7'},
               'MVE': {'armv7em', 'mve'},
               'MVE_FP': {'MVE', 'mve_float', 'FPv5', 'fp16'},
               'NEON': {'neon', 'FP_D32'},
               'VFPv2': {'vfpv2'},
               'VFPv3': {'VFPv2', 'vfpv3'},
               'VFPv4': {'VFPv3', 'fp16conv', 'vfpv4'}}

ARM_ARCHES = {'armv4': ['ARMv4', {}],
              'armv4t': ['ARMv4t', {}],
              'armv5t': ['ARMv5t', {}],
              'armv5te': ['ARMv5te',
                          {'fp': (True, {'VFPv2', 'FP_DBL'}),
                           'nofp': (False, {'ALL_FP'}),
                           'vfpv2': (True, {'VFPv2', 'FP_DBL'})}],
              'armv5tej': ['ARMv5tej',
                           {'fp': (True, {'VFPv2', 'FP_DBL'}),
                            'nofp': (False, {'ALL_FP'}),
                            'vfpv2': (True, {'VFPv2', 'FP_DBL'})}],
              'armv6': ['ARMv6',
                        {'fp': (True, {'VFPv2', 'FP_DBL'}),
                         'nofp': (False, {'ALL_FP'}),
                         'vfpv2': (True, {'VFPv2', 'FP_DBL'})}],
              'armv6-m': ['ARMv6m', {}],
              'armv6j': ['ARMv6j',
                         {'fp': (True, {'VFPv2', 'FP_DBL'}),
                          'nofp': (False, {'ALL_FP'}),
                          'vfpv2': (True, {'VFPv2', 'FP_DBL'})}],
              'armv6k': ['ARMv6k',
                         {'fp': (True, {'VFPv2', 'FP_DBL'}),
                          'nofp': (False, {'ALL_FP'}),
                          'vfpv2': (True, {'VFPv2', 'FP_DBL'})}],
              'armv6kz': ['ARMv6kz',
                          {'fp': (True, {'VFPv2', 'FP_DBL'}),
                           'nofp': (False, {'ALL_FP'}),
                           'vfpv2': (True, {'VFPv2', 'FP_DBL'})}],
              'armv6s-m': ['ARMv6m', {}],
              'armv6t2': ['ARMv6t2',
                          {'fp': (True, {'VFPv2', 'FP_DBL'}),
                           'nofp': (False, {'ALL_FP'}),
                           'vfpv2': (True, {'VFPv2', 'FP_DBL'})}],
              'armv6z': ['ARMv6z',
                         {'fp': (True, {'VFPv2', 'FP_DBL'}),
                          'nofp': (False, {'ALL_FP'}),
                          'vfpv2': (True, {'VFPv2', 'FP_DBL'})}],
              'armv6zk': ['ARMv6kz',
                          {'fp': (True, {'VFPv2', 'FP_DBL'}),
                           'nofp': (False, {'ALL_FP'}),
                           'vfpv2': (True, {'VFPv2', 'FP_DBL'})}],
              'armv7': ['ARMv7',
                        {'fp': (True, {'VFPv3', 'FP_DBL'}),
                         'nofp': (False, {'ALL_FP'}),
                         'vfpv3-d16': (True, {'VFPv3', 'FP_DBL'})}],
              'armv7-a': ['ARMv7a',
                          {'fp': (True, {'VFPv3', 'FP_DBL'}),
                           'mp': (True, {'mp'}),
                           'neon': (True, {'NEON', 'VFPv3'}),
                           'neon-fp16': (True, {'NEON', 'VFPv3', 'fp16conv'}),
                           'neon-vfpv3': (True, {'NEON', 'VFPv3'}),
                           'neon-vfpv4': (True, {'NEON', 'VFPv4'}),
                           'nofp': (False, {'ALL_FP'}),
                           'nosimd': (False, {'ALL_SIMD'}),
                           'sec': (True, {'sec'}),
                           'simd': (True, {'NEON', 'VFPv3'}),
                           'vfpv3': (True, {'VFPv3', 'FP_D32'}),
                           'vfpv3-d16': (True, {'VFPv3', 'FP_DBL'}),
                           'vfpv3-d16-fp16': (True, {'fp16conv', 'VFPv3', 'FP_DBL'}),
                           'vfpv3-fp16': (True, {'fp16conv', 'VFPv3', 'FP_DBL', 'FP_D32'}),
                           'vfpv4': (True, {'VFPv4', 'FP_D32'}),
                           'vfpv4-d16': (True, {'FP_DBL', 'VFPv4'})}],
              'armv7-m': ['ARMv7m', {}],
              'armv7-r': ['ARMv7r',
                          {'fp': (True, {'VFPv3', 'FP_DBL'}),
                           'fp.sp': (True, {'VFPv3'}),
                           'idiv': (True, {'adiv'}),
                           'nofp': (False, {'ALL_FP'}),
                           'noidiv': (False, {'adiv'}),
                           'vfpv3-d16': (True, {'VFPv3', 'FP_DBL'}),
                           'vfpv3-d16-fp16': (True, {'fp16conv', 'VFPv3', 'FP_DBL'}),
                           'vfpv3xd': (True, {'VFPv3'}),
                           'vfpv3xd-fp16': (True, {'VFPv3', 'fp16conv'})}],
              'armv7e-m': ['ARMv7em',
                           {'fp': (True, {'VFPv4'}),
                            'fp.dp': (True, {'FP_DBL', 'FPv5'}),
                            'fpv5': (True, {'FPv5'}),
                            'fpv5-d16': (True, {'FP_DBL', 'FPv5'}),
                            'nofp': (False, {'ALL_FP'}),
                            'vfpv4-sp-d16': (True, {'VFPv4'})}],
              'armv7ve': ['ARMv7ve',
                          {'fp': (True, {'FP_DBL', 'VFPv4'}),
                           'neon': (True, {'NEON', 'VFPv3'}),
                           'neon-fp16': (True, {'NEON', 'VFPv3', 'fp16conv'}),
                           'neon-vfpv3': (True, {'NEON', 'VFPv3'}),
                           'neon-vfpv4': (True, {'NEON', 'VFPv4'}),
                           'nofp': (False, {'ALL_FP'}),
                           'nosimd': (False, {'ALL_SIMD'}),
                           'simd': (True, {'NEON', 'VFPv4'}),
                           'vfpv3': (True, {'VFPv3', 'FP_D32'}),
                           'vfpv3-d16': (True, {'VFPv3', 'FP_DBL'}),
                           'vfpv3-d16-fp16': (True, {'fp16conv', 'VFPv3', 'FP_DBL'}),
                           'vfpv3-fp16': (True, {'fp16conv', 'VFPv3', 'FP_DBL', 'FP_D32'}),
                           'vfpv4': (True, {'VFPv4', 'FP_D32'}),
                           'vfpv4-d16': (True, {'FP_DBL', 'VFPv4'})}],
              'armv8-a': ['ARMv8a',
                          {'crc': (True, {'crc32'}),
                           'crypto': (True, {'CRYPTO', 'FP_ARMv8'}),
                           'nocrypto': (False, {'ALL_CRYPTO'}),
                           'nofp': (False, {'ALL_FP'}),
                           'predres': (True, {'predres'}),
                           'sb': (True, {'sb'}),
                           'simd': (True, {'NEON', 'FP_ARMv8'})}],
              'armv8-m.base': ['ARMv8m_base', {}],
              'armv8-m.main': ['ARMv8m_main',
                               {'cdecp0': (True, {'cdecp0'}),
                                'cdecp1': (True, {'cdecp1'}),
                                'cdecp2': (True, {'cdecp2'}),
                                'cdecp3': (True, {'cdecp3'}),
                                'cdecp4': (True, {'cdecp4'}),
                                'cdecp5': (True, {'cdecp5'}),
                                'cdecp6': (True, {'cdecp6'}),
                                'cdecp7': (True, {'cdecp7'}),
                                'dsp': (True, {'armv7em'}),
                                'fp': (True, {'FPv5'}),
                                'fp.dp': (True, {'FP_DBL', 'FPv5'}),
                                'nodsp': (False, {'armv7em'}),
                                'nofp': (False, {'ALL_FP'})}],
              'armv8-r': ['ARMv8r',
                          {'crc': (True, {'crc32'}),
                           'crypto': (True, {'CRYPTO', 'FP_ARMv8'}),
                           'fp.sp': (True, {'FPv5'}),
                           'nocrypto': (False, {'ALL_CRYPTO'}),
                           'nofp': (False, {'ALL_FP'}),
                           'simd': (True, {'NEON', 'FP_ARMv8'})}],
              'armv8.1-a': ['ARMv8_1a',
                            {'crypto': (True, {'CRYPTO', 'FP_ARMv8'}),
                             'nocrypto': (False, {'ALL_CRYPTO'}),
                             'nofp': (False, {'ALL_FP'}),
                             'predres': (True, {'predres'}),
                             'sb': (True, {'sb'}),
                             'simd': (True, {'NEON', 'FP_ARMv8'})}],
              'armv8.1-m.main': ['ARMv8_1m_main',
                                 {'cdecp0': (True, {'cdecp0'}),
                                  'cdecp1': (True, {'cdecp1'}),
                                  'cdecp2': (True, {'cdecp2'}),
                                  'cdecp3': (True, {'cdecp3'}),
                                  'cdecp4': (True, {'cdecp4'}),
                                  'cdecp5': (True, {'cdecp5'}),
                                  'cdecp6': (True, {'cdecp6'}),
                                  'cdecp7': (True, {'cdecp7'}),
                                  'dsp': (True, {'armv7em'}),
                                  'fp': (True, {'FPv5', 'fp16'}),
                                  'fp.dp': (True, {'FP_DBL', 'FPv5', 'fp16'}),
                                  'mve': (True, {'MVE'}),
                                  'mve.fp': (True, {'MVE_FP'}),
                                  'nofp': (False, {'ALL_FP'}),
                                  'pacbti': (True, {'pacbti'})}],
              'armv8.2-a': ['ARMv8_2a',
                            {'bf16': (True, {'NEON', 'bf16', 'FP_ARMv8'}),
                             'crypto': (True, {'CRYPTO', 'FP_ARMv8'}),
                             'dotprod': (True, {'DOTPROD', 'FP_ARMv8'}),
                             'fp16': (True, {'FP_ARMv8', 'NEON', 'fp16'}),
                             'fp16fml': (True, {'FP_ARMv8', 'fp16fml', 'NEON', 'fp16'}),
                             'i8mm': (True, {'i8mm', 'NEON', 'FP_ARMv8'}),
                             'nocrypto': (False, {'ALL_CRYPTO'}),
                             'nofp': (False, {'ALL_FP'}),
                             'predres': (True, {'predres'}),
                             'sb': (True, {'sb'}),
                             'simd': (True, {'NEON', 'FP_ARMv8'})}],
              'armv8.3-a': ['ARMv8_3a',
                            {'bf16': (True, {'NEON', 'bf16', 'FP_ARMv8'}),
                             'crypto': (True, {'CRYPTO', 'FP_ARMv8'}),
                             'dotprod': (True, {'DOTPROD', 'FP_ARMv8'}),
                             'fp16': (True, {'FP_ARMv8', 'NEON', 'fp16'}),
                             'fp16fml': (True, {'FP_ARMv8', 'fp16fml', 'NEON', 'fp16'}),
                             'i8mm': (True, {'i8mm', 'NEON', 'FP_ARMv8'}),
                             'nocrypto': (False, {'ALL_CRYPTO'}),
                             'nofp': (False, {'ALL_FP'}),
                             'predres': (True, {'predres'}),
                             'sb': (True, {'sb'}),
                             'simd': (True, {'NEON', 'FP_ARMv8'})}],
              'armv8.4-a': ['ARMv8_4a',
                            {'bf16': (True, {'DOTPROD', 'bf16', 'FP_ARMv8'}),
                             'crypto': (True, {'CRYPTO', 'DOTPROD', 'FP_ARMv8'}),
                             'fp16': (True, {'FP_ARMv8', 'fp16fml', 'DOTPROD', 'fp16'}),
                             'i8mm': (True, {'i8mm', 'DOTPROD', 'FP_ARMv8'}),
                             'nocrypto': (False, {'ALL_CRYPTO'}),
                             'nofp': (False, {'ALL_FP'}),
                             'predres': (True, {'predres'}),
                             'sb': (True, {'sb'}),
                             'simd': (True, {'DOTPROD', 'FP_ARMv8'})}],
              'armv8.5-a': ['ARMv8_5a',
                            {'bf16': (True, {'DOTPROD', 'bf16', 'FP_ARMv8'}),
                             'crypto': (True, {'CRYPTO', 'DOTPROD', 'FP_ARMv8'}),
                             'fp16': (True, {'FP_ARMv8', 'fp16fml', 'DOTPROD', 'fp16'}),
                             'i8mm': (True, {'i8mm', 'DOTPROD', 'FP_ARMv8'}),
                             'nocrypto': (False, {'ALL_CRYPTO'}),
                             'nofp': (False, {'ALL_FP'}),
                             'simd': (True, {'DOTPROD', 'FP_ARMv8'})}],
              'armv8.6-a': ['ARMv8_6a',
                            {'bf16': (True, {'DOTPROD', 'bf16', 'FP_ARMv8'}),
                             'crypto': (True, {'CRYPTO', 'DOTPROD', 'FP_ARMv8'}),
                             'fp16': (True, {'FP_ARMv8', 'fp16fml', 'DOTPROD', 'fp16'}),
                             'i8mm': (True, {'i8mm', 'DOTPROD', 'FP_ARMv8'}),
                             'nocrypto': (False, {'ALL_CRYPTO'}),
                             'nofp': (False, {'ALL_FP'}),
                             'simd': (True, {'DOTPROD', 'FP_ARMv8'})}],
              'armv9-a': ['ARMv9a',
                          {'bf16': (True, {'DOTPROD', 'bf16', 'FP_ARMv8'}),
                           'crypto': (True, {'CRYPTO', 'DOTPROD', 'FP_ARMv8'}),
                           'fp16': (True, {'FP_ARMv8', 'fp16fml', 'DOTPROD', 'fp16'}),
                           'i8mm': (True, {'i8mm', 'DOTPROD', 'FP_ARMv8'}),
                           'nocrypto': (False, {'ALL_CRYPTO'}),
                           'nofp': (False, {'ALL_FP'}),
                           'simd': (True, {'DOTPROD', 'FP_ARMv8'})}],
              'iwmmxt': ['ARMv5te', {}],
              'iwmmxt2': ['ARMv5te', {}]}

ARM_CPUS = {'ares': ['armv8.2-a+fp16+dotprod', set(),
                     {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'arm1020e': ['armv5te+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'arm1020t': ['armv5t', set(), {}],
            'arm1022e': ['armv5te+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'arm1026ej-s': ['armv5tej+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'arm10e': ['armv5te+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'arm10tdmi': ['armv5t', set(), {}],
            'arm1136j-s': ['armv6j', set(), {}],
            'arm1136jf-s': ['armv6j+fp', set(), {}],
            'arm1156t2-s': ['armv6t2', set(), {}],
            'arm1156t2f-s': ['armv6t2+fp', set(), {}],
            'arm1176jz-s': ['armv6kz', set(), {}],
            'arm1176jzf-s': ['armv6kz+fp', set(), {}],
            'arm710t': ['armv4t', set(), {}],
            'arm720t': ['armv4t', set(), {}],
            'arm740t': ['armv4t', set(), {}],
            'arm7tdmi': ['armv4t', set(), {}],
            'arm7tdmi-s': ['armv4t', set(), {}],
            'arm8': ['armv4', set(), {}],
            'arm810': ['armv4', set(), {}],
            'arm9': ['armv4t', set(), {}],
            'arm920': ['armv4t', set(), {}],
            'arm920t': ['armv4t', set(), {}],
            'arm922t': ['armv4t', set(), {}],
            'arm926ej-s': ['armv5tej+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'arm940t': ['armv4t', set(), {}],
            'arm946e-s': ['armv5te+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'arm966e-s': ['armv5te+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'arm968e-s': ['armv5te+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'arm9e': ['armv5te+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'arm9tdmi': ['armv4t', set(), {}],
            'cortex-a12': ['armv7ve+simd', set(), {'nofp': (False, {'ALL_FP'})}],
            'cortex-a15': ['armv7ve+simd', set(), {'nofp': (False, {'ALL_FP'})}],
            'cortex-a15.cortex-a7': ['armv7ve+simd', set(), {'nofp': (False, {'ALL_FP'})}],
            'cortex-a17': ['armv7ve+simd', set(), {'nofp': (False, {'ALL_FP'})}],
            'cortex-a17.cortex-a7': ['armv7ve+simd', set(), {'nofp': (False, {'ALL_FP'})}],
            'cortex-a32': ['armv8-a+crc+simd', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'}),
                            'nofp': (False, {'ALL_FP'})}],
            'cortex-a35': ['armv8-a+crc+simd', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'}),
                            'nofp': (False, {'ALL_FP'})}],
            'cortex-a5': ['armv7-a+mp+sec+neon-fp16', set(),
                          {'nofp': (False, {'ALL_FP'}), 'nosimd': (False, {'ALL_SIMD'})}],
            'cortex-a53': ['armv8-a+crc+simd', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'}),
                            'nofp': (False, {'ALL_FP'})}],
            'cortex-a55': ['armv8.2-a+fp16+dotprod', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'}),
                            'nofp': (False, {'ALL_FP'})}],
            'cortex-a57': ['armv8-a+crc+simd', {'quirk_aes_1742098'},
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a57.cortex-a53': ['armv8-a+crc+simd', {'quirk_aes_1742098'},
                                      {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a7': ['armv7ve+simd', set(),
                          {'nofp': (False, {'ALL_FP'}), 'nosimd': (False, {'ALL_SIMD'})}],
            'cortex-a710': ['armv9-a+fp16+bf16+i8mm', set(),
                            {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a72': ['armv8-a+crc+simd', {'quirk_aes_1742098'},
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a72.cortex-a53': ['armv8-a+crc+simd', {'quirk_aes_1742098'},
                                      {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a73': ['armv8-a+crc+simd', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a73.cortex-a35': ['armv8-a+crc+simd', set(),
                                      {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a73.cortex-a53': ['armv8-a+crc+simd', set(),
                                      {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a75': ['armv8.2-a+fp16+dotprod', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a75.cortex-a55': ['armv8.2-a+fp16+dotprod', set(),
                                      {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a76': ['armv8.2-a+fp16+dotprod', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a76.cortex-a55': ['armv8.2-a+fp16+dotprod', set(),
                                      {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a76ae': ['armv8.2-a+fp16+dotprod', set(),
                             {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a77': ['armv8.2-a+fp16+dotprod', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a78': ['armv8.2-a+fp16+dotprod', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a78ae': ['armv8.2-a+fp16+dotprod', set(),
                             {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a78c': ['armv8.2-a+fp16+dotprod', set(),
                            {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-a8': ['armv7-a+sec+simd', set(), {'nofp': (False, {'ALL_FP'})}],
            'cortex-a9': ['armv7-a+mp+sec+neon-fp16', set(),
                          {'nofp': (False, {'ALL_FP'}), 'nosimd': (False, {'ALL_SIMD'})}],
            'cortex-m0': ['armv6s-m', set(), {}],
            'cortex-m0.small-multiply': ['armv6s-m', set(), {}],
            'cortex-m0plus': ['armv6s-m', set(), {}],
            'cortex-m0plus.small-multiply': ['armv6s-m', set(), {}],
            'cortex-m1': ['armv6s-m', set(), {}],
            'cortex-m1.small-multiply': ['armv6s-m', set(), {}],
            'cortex-m23': ['armv8-m.base', set(), {}],
            'cortex-m3': ['armv7-m', {'quirk_cm3_ldrd'}, {}],
            'cortex-m33': ['armv8-m.main+dsp+fp', {'quirk_vlldm'},
                           {'nodsp': (False, {'armv7em'}), 'nofp': (False, {'ALL_FP'})}],
            'cortex-m35p': ['armv8-m.main+dsp+fp', {'quirk_vlldm'},
                            {'nodsp': (False, {'armv7em'}), 'nofp': (False, {'ALL_FP'})}],
            'cortex-m4': ['armv7e-m+fp', set(), {'nofp': (False, {'ALL_FP'})}],
            'cortex-m52': ['armv8.1-m.main+pacbti+mve.fp+fp.dp',
                           {'quirk_no_asmcpu', 'quirk_vlldm'},
                           {'cdecp0': (True, {'cdecp0'}),
                            'cdecp1': (True, {'cdecp1'}),
                            'cdecp2': (True, {'cdecp2'}),
                            'cdecp3': (True, {'cdecp3'}),
                            'cdecp4': (True, {'cdecp4'}),
                            'cdecp5': (True, {'cdecp5'}),
                            'cdecp6': (True, {'cdecp6'}),
                            'cdecp7': (True, {'cdecp7'}),
                            'nodsp': (False, {'MVE', 'mve_float'}),
                            'nofp': (False, {'ALL_FP', 'mve_float'}),
                            'nomve': (False, {'mve', 'mve_float'}),
                            'nomve.fp': (False, {'mve_float'}),
                            'nopacbti': (False, {'pacbti'})}],
            'cortex-m55': ['armv8.1-m.main+mve.fp+fp.dp',
                           {'quirk_no_asmcpu', 'quirk_vlldm'},
                           {'cdecp0': (True, {'cdecp0'}),
                            'cdecp1': (True, {'cdecp1'}),
                            'cdecp2': (True, {'cdecp2'}),
                            'cdecp3': (True, {'cdecp3'}),
                            'cdecp4': (True, {'cdecp4'}),
                            'cdecp5': (True, {'cdecp5'}),
                            'cdecp6': (True, {'cdecp6'}),
                            'cdecp7': (True, {'cdecp7'}),
                            'nodsp': (False, {'MVE', 'mve_float'}),
                            'nofp': (False, {'ALL_FP', 'mve_float'}),
                            'nomve': (False, {'mve', 'mve_float'}),
                            'nomve.fp': (False, {'mve_float'})}],
            'cortex-m7': ['armv7e-m+fp.dp', {'quirk_no_volatile_ce'},
                          {'nofp': (False, {'ALL_FP'}), 'nofp.dp': (False, {'FP_DBL'})}],
            'cortex-m85': ['armv8.1-m.main+pacbti+mve.fp+fp.dp',
                           {'quirk_no_asmcpu', 'quirk_vlldm'},
                           {'nodsp': (False, {'MVE', 'mve_float'}),
                            'nofp': (False, {'ALL_FP', 'mve_float'}),
                            'nomve': (False, {'mve', 'mve_float'}),
                            'nomve.fp': (False, {'mve_float'}),
                            'nopacbti': (False, {'pacbti'})}],
            'cortex-r4': ['armv7-r', set(), {}],
            'cortex-r4f': ['armv7-r+fp', set(), {}],
            'cortex-r5': ['armv7-r+idiv+fp', set(),
                          {'nofp': (False, {'ALL_FP'}), 'nofp.dp': (False, {'FP_DBL'})}],
            'cortex-r52': ['armv8-r+crc+simd', set(),
                           {'nofp.dp': (False, {'ALL_SIMD', 'FP_DBL'})}],
            'cortex-r52plus': ['armv8-r+crc+simd', set(),
                               {'nofp.dp': (False, {'ALL_SIMD', 'FP_DBL'})}],
            'cortex-r7': ['armv7-r+idiv+vfpv3-d16-fp16', set(),
                          {'nofp': (False, {'ALL_FP'}), 'nofp.dp': (False, {'FP_DBL'})}],
            'cortex-r8': ['armv7-r+idiv+vfpv3-d16-fp16', set(),
                          {'nofp': (False, {'ALL_FP'}), 'nofp.dp': (False, {'FP_DBL'})}],
            'cortex-x1': ['armv8.2-a+fp16+dotprod', set(),
                          {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'cortex-x1c': ['armv8.2-a+fp16+dotprod', set(),
                           {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'ep9312': ['armv4t', set(), {}],
            'exynos-m1': ['armv8-a+crc+simd', set(),
                          {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'fa526': ['armv4', set(), {}],
            'fa606te': ['armv5te', set(), {}],
            'fa626': ['armv4', set(), {}],
            'fa626te': ['armv5te', set(), {}],
            'fa726te': ['armv5te', set(), {}],
            'fmp626': ['armv5te', set(), {}],
            'generic-armv7-a': ['armv7-a+fp', {'quirk_no_asmcpu'},
                                {'mp': (True, {'mp'}),
                                 'neon': (True, {'NEON', 'VFPv3'}),
                                 'neon-fp16': (True, {'NEON', 'VFPv3', 'fp16conv'}),
                                 'neon-vfpv3': (True, {'NEON', 'VFPv3'}),
                                 'neon-vfpv4': (True, {'NEON', 'VFPv4'}),
                                 'nofp': (False, {'ALL_FP'}),
                                 'nosimd': (False, {'ALL_SIMD'}),
                                 'sec': (True, {'sec'}),
                                 'simd': (True, {'NEON', 'VFPv3'}),
                                 'vfpv3': (True, {'VFPv3', 'FP_D32'}),
                                 'vfpv3-d16': (True, {'VFPv3', 'FP_DBL'}),
                                 'vfpv3-d16-fp16': (True, {'fp16conv', 'VFPv3', 'FP_DBL'}),
                                 'vfpv3-fp16': (True, {'VFPv3', 'fp16conv', 'FP_D32'}),
                                 'vfpv4': (True, {'VFPv4', 'FP_D32'}),
                                 'vfpv4-d16': (True, {'FP_DBL', 'VFPv4'})}],
            'iwmmxt': ['iwmmxt', set(), {}],
            'iwmmxt2': ['iwmmxt2', set(), {}],
            'marvell-pj4': ['armv7-a+mp+sec+fp', set(), {}],
            'mpcore': ['armv6k+fp', set(), {}],
            'mpcorenovfp': ['armv6k', set(), {}],
            'neoverse-n1': ['armv8.2-a+fp16+dotprod', set(),
                            {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'neoverse-n2': ['armv8.5-a+fp16+bf16+i8mm', set(),
                            {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'neoverse-v1': ['armv8.4-a+fp16+bf16+i8mm', set(),
                            {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'star-mc1': ['armv8-m.main+dsp+fp', {'quirk_no_asmcpu', 'quirk_vlldm'},
                         {'cdecp0': (True, {'cdecp0'}),
                          'cdecp1': (True, {'cdecp1'}),
                          'cdecp2': (True, {'cdecp2'}),
                          'cdecp3': (True, {'cdecp3'}),
                          'cdecp4': (True, {'cdecp4'}),
                          'cdecp5': (True, {'cdecp5'}),
                          'cdecp6': (True, {'cdecp6'}),
                          'cdecp7': (True, {'cdecp7'}),
                          'nodsp': (False, {'armv7em'}),
                          'nofp': (False, {'ALL_FP'})}],
            'strongarm': ['armv4', set(), {}],
            'strongarm110': ['armv4', set(), {}],
            'strongarm1100': ['armv4', set(), {}],
            'strongarm1110': ['armv4', set(), {}],
            'xgene1': ['armv8-a+simd', set(), {'crypto': (True, {'CRYPTO', 'FP_ARMv8'})}],
            'xscale': ['armv5te', {'xscale'}, {}]}

def armResolveFgroups(features):
    ret = None
    while True:
        ret = set()
        for i in features:
            ret |= ARM_FGROUPS.get(i, set([i]))
        if ret == features:
            break
        else:
            features = ret
    return ret

def armResolveOptions(flags, options, known_options):
    flags = set(flags)
    for opt in (options.split('+') if options else []):
        mode, dependencies = known_options[opt]
        if mode:
            flags |= armResolveFgroups(dependencies)
        else:
            flags -= armResolveFgroups(dependencies)
    return flags

@functools.lru_cache
def armFlagsFromArch(arch):
    arch, _, options = arch.partition('+')
    arch_isa, arch_options = ARM_ARCHES[arch]
    flags = armResolveFgroups(set([arch_isa]))
    return armResolveOptions(flags, options, arch_options)

@functools.lru_cache
def armFlagsFromCpu(cpu):
    cpu, _, options = cpu.partition('+')
    cpu_arch, cpu_features, cpu_options = ARM_CPUS[cpu]
    flags = armFlagsFromArch(cpu_arch)
    flags |= armResolveFgroups(cpu_features)
    return armResolveOptions(flags, options, cpu_options)


def crossToolchainCpuFeature(args, env, **options):
    if len(args) != 1:
        raise ParseError("$(toolchain-feature,id) expects one argument")

    try:
        coarseArch = env.get("ARCH")

        selectedArch = env.get("CROSS_TOOLCHAIN_ARCH")
        defaultArch = env.get("GCC_TARGET_ARCH")
        if defaultArch is None and selectedArch is None:
            if coarseArch == "x86_64":
                defaultArch = "x86-64"
            elif coarseArch == "arm":
                defaultArch = "armv4t"
            else:
                raise ParseError("$(toolchain-feature): neither $CROSS_TOOLCHAIN_ARCH nor $GCC_TARGET_ARCH set")

        # Arm(64) is complicated. The toolchain default is encoded in
        # GCC_TARGET_ARCH. This may be overridden by CROSS_TOOLCHAIN_ARCH and
        # CROSS_TOOLCHAIN_CPU where CROSS_TOOLCHAIN_ARCH takes precedence.

        if coarseArch in ("x86_64", "i386"):
            flags = AMD64_FEATURES[selectedArch or defaultArch]
        elif coarseArch == "arm64":
            cpu = env.get("CROSS_TOOLCHAIN_CPU")
            if selectedArch is not None:
                flags = arm64FlagsFromArch(selectedArch)
            elif cpu is not None:
                flags = arm64FlagsFromCpu(cpu)
            else:
                flags = arm64FlagsFromArch(defaultArch)
        elif coarseArch == "arm":
            cpu = env.get("CROSS_TOOLCHAIN_CPU")
            if selectedArch is not None:
                flags = armFlagsFromArch(selectedArch)
            elif cpu is not None:
                flags = armFlagsFromCpu(cpu)
            else:
                flags = armFlagsFromArch(defaultArch)
        else:
            raise ParseError("$(toolchain-feature): unsupported $ARCH")
    except KeyError as e:
        raise ParseError("Wrong arch/cpu/flag in cross-toolchain-cpu-feature: "+ str(e))

    return "1" if args[0] in flags else "0"

def libcFlavour(args, **options):
    if len(args) != 1:
        raise ParseError("$(libc-flavour,triple) expects one argument")
    # Very simple for the moment because we just support glibc and uclibc on Linux...
    _, _, os_part = args[0].rpartition("-")
    if "uclibc" in os_part:
        return "uclibc"
    else:
        return "glibc"

manifest = {
    'apiVersion' : "0.25",
    'stringFunctions' : {
        "gen-autoconf" : genAutoconf,
        "host-arch" : hostArch,
        "host-autoconf" : hostAutoconf,
        "rustc-target" : rustcTarget,
        "toolchain-feature" : crossToolchainCpuFeature,
        "libc-flavour" : libcFlavour,
    }
}
