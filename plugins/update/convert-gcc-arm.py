#!/usr/bin/env python3

# Used to convert gcc/config/arm/arm-cpus.in to the tables in multiarch.py

import pprint

ARM_FGROUPS = {}
ARM_ARCHES = {}
ARM_CPUS = {}

def handleArch(tokens):
    if tokens[0] == "isa":
        ARM_ARCHES[arch][0] = tokens[1]
    elif tokens[0] == "option":
        name = tokens[1]
        mode = tokens[2] == "add"
        features = set(tokens[3:])
        ARM_ARCHES[arch][1][name] = (mode, features)
    elif tokens[0] == "optalias":
        name = tokens[1]
        alias = tokens[2]
        ARM_ARCHES[arch][1][name] = ARM_ARCHES[arch][1][alias]

def handleCpu(tokens):
    if tokens[0] == "architecture":
        ARM_CPUS[cpu][0] = tokens[1]
    elif tokens[0] == "alias":
        for alias in tokens[1:]:
            if alias.startswith("!"): alias = alias[1:]
            ARM_CPUS[alias] = ARM_CPUS[cpu]
    elif tokens[0] == "isa":
        ARM_CPUS[cpu][1] = set(tokens[1:])
    elif tokens[0] == "option":
        name = tokens[1]
        mode = tokens[2] == "add"
        features = set(tokens[3:])
        ARM_CPUS[cpu][2][name] = (mode, features)
    elif tokens[0] == "optalias":
        name = tokens[1]
        alias = tokens[2]
        ARM_CPUS[cpu][2][name] = ARM_CPUS[cpu][2][alias]

handler = None
with open("arm-cpus.in") as f:
    for line in f:
        line, _, _ = line.strip().partition('#')
        tokens = line.split()
        if line.startswith('define fgroup'):
            ARM_FGROUPS[tokens[2]] = set(tokens[3:])
        elif line.startswith('begin arch'):
            arch = tokens[2]
            ARM_ARCHES[arch] = [None, {}]
            handler = handleArch
        elif line.startswith("begin cpu"):
            cpu = tokens[2]
            ARM_CPUS[cpu] = [None, set(), {}]
            handler = handleCpu
        elif line.startswith("end"):
            handler = None
        elif tokens and handler:
            handler(tokens)

pp = pprint.PrettyPrinter(depth=4, compact=True)

print(" =============== FEATURES ==================")
pp.pprint(ARM_FGROUPS)
print(" =============== ARCHES ==================")
pp.pprint(ARM_ARCHES)
print(" =============== CPUS ==================")
pp.pprint(ARM_CPUS)
