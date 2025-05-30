# Basement

This basement project is a collection of useful recipes that can be included by
other projects. Most importantly it provides pre-made classes to handle common
build systems and other recurring tasks. Additionally a sandbox and common GCC
toolchains are ready-to-use.

# Documentation

The documentation how to use the basement project can be found on [Read the
Docs](https://bob-build-tool.readthedocs.io/projects/basement/en/latest/index.html).

# Prerequisites

* A x86\_64 system with the regular development tools installed
  * gcc >= 5.x
  * bash
  * POSIX awk (GNU awk version >= 3.1.5)
  * GNU make >= 3.80
  * perl >= 5.6.1
  * GNU tar
  * gzip
  * bzip2
  * rsync
  * xz-utils
* Bob Build Tool (https://github.com/BobBuildTool/bob)

# How to build

Actually there isn't much to build directly in this repository. Head over
to one of the examples to see how this repository is used:

 * [Embedded systems](https://github.com/BobBuildTool/bob-example-embedded)
 * [Linux containers](https://github.com/BobBuildTool/bob-example-containers)

In `tests/linux` there are a couple of recipes that build small test packages
which use the `basement` layer. They act as smoke tests for this project.

# How to use

First you need to add the `basement` layer to your project. To do so, add a
`layers` entry to `config.yaml`:

    bobMinimumVersion: "1.0"
    layers:
        - name: basement
          scm: git
          url: https://github.com/BobBuildTool/basement.git
          commit: <git commit id> # optional but highly recommended

and then fetch the layer:

    $ bob layers update

To use all facilities of the basement project you just need to inherit the `basement::rootrecipe`
class in your root recipe:

    inherit: [ "basement::rootrecipe" ]

This will make your recipe a root recipe and already setup the sandbox with a
proper host toolchain. See the next chapter what tools and toolchains are readily
available.

# Provided tools and C/C++ toolchains

The following tools can be used by naming them in `{checkout,build,package}Tools`:

* bison
* cpio
* flex
* make
* pkg-config
* squashfs-tools
* e2fsprogs
* util-linux

The following cross compiling toolchains are available pre-configured. If you need
other targets you can depend on `devel::cross-toolchain` directly and configure it
as you like.

* `devel::cross-toolchain-aarch64-linux-gnu`: ARMv8-A AArch64 Linux with glibc.
* `devel::cross-toolchain-aarch64-none-elf`: ARMv8-A/R AArch64 bare metal
  toolchain with newlib libc.
* `devel::cross-toolchain-arm-linux-gnueabihf`: ARMv7-A Linux with glibc. Hard
  floating point ABI.
* `devel::cross-toolchain-arm-none-eabi`: ARMv7 bare metal toolchain with
  newlib libc.
* `devel::cross-toolchain-x86_64-linux-gnu`: x86_64 toolchain for Linux with glibc.
* `devel::cross-toolchain-riscv64-linux-gnu`: RISC-V toolchain targeting the GC
  profile.

To use a cross compiling toolchain include it where needed via:

    depends:
        - name: <recipe name here>
          use: [tools, environment]
          forward: True

Regarding the C/C++ toolchains the following tools are defined and used in the
recipes:

* `target-toolchain`: This is the main toolchain. Every C/C++ package uses it.
  It represents the compiler that builds for the target system where the
  package should run in the end. Usually, but not necessarily, this is a cross
  compiler even on the same architecture.

  In autotools speak this is the compiler for the `--host=` system.
* `host-toolchain`: This toolchain represents the native host machine compiler.
  Even though it builds host executables, it does never
  [fingerprint](https://bob-build-tool.readthedocs.io/en/latest/manual/configuration.html#host-dependency-fingerprinting)
  the results. Instead, it is intended to be used in the `buildScript` if the
  package *also* needs the host compiler during build time where none of the
  host build object code is part of the result. Points to the host gcc or the
  gcc of the sandbox. Only selected packages need it when being built in the
  sandbox.

  In autotools speak this is the compiler of the `--build=` system.
* `host-compat-toolchain`: A toolchain that builds portable host executables
  that should be able to run on the oldest supported Ubuntu LTS. Even though it
  builds for the host architecture, it is a cross compiler with a backwards
  compatible glibc version. When using the `basement::rootrecipe` class, this
  is the default `target-toolchain`. It is defined as a dedicated name to be
  able to compile specifically for the host when needed:

      depends:
        - ...
        - name: some::package
          tools:
            target-toolchain: host-compat-toolchain

  This will build `some::package` for the host regardless of the currently
  defined target toolchain.
* `host-native-toolchain`: This toolchain represents the native host machine
  compiler. In contrast to `host-toolchain` it *does* fingerprint the system.
  Used if a package needs to be compiled natively and the object code is part
  of the package result.
