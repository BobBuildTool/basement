# Basement

[![Recipes Build Status](https://ci.bobbuildtool.dev/jenkins/buildStatus/icon?job=basement-integration&subject=Recipes)](https://ci.bobbuildtool.dev/jenkins/view/basement/job/basement-integration/)
[![Packages Build Status](https://ci.bobbuildtool.dev/jenkins/buildStatus/icon?job=basement-buildall&subject=Packages)](https://ci.bobbuildtool.dev/jenkins/view/basement/)

These basement project is a collection of useful recipes and classes that can be
used by other projects. Most importantly it provides standard classes
to handle common build systems and other standard tasks. Additionally a
standard sandbox and common GCC toolchains are ready-to-use.

# Prerequisites

* A x86_64 system with the regular development tools installed (gcc, make,
  perl, ...)
* Bleeding edge Bob Build Tool (https://github.com/BobBuildTool/bob)

# How to build

Actually there isn't anything to build directly in this repository. Head over
to one of the examples to see how this repository is used:

 * [Applications](https://github.com/BobBuildTool/bob-example-applications)
 * [Linux containers](https://github.com/BobBuildTool/bob-example-containers)
 * [Embedded systems](https://github.com/BobBuildTool/bob-example-embedded)

# How to use

First you need to add the `basement` layer to your project. To do so add a
`layers` entry to `config.yaml`:

    bobMinimumVersion: "0.15"
    laysers:
        - basement

and then add this repository as submodule to your project:

    $ git submodule add https://github.com/BobBuildTool/basement.git layers/basement

To use all facilities of the basement project you just need to inherit the `basement::rootrecipe`
class in your root recipe:

    inherit: [ "basement::rootrecipe" ]

This will make your recipe a root recipe and already setup the sandbox with a
proper host toolchain. See the next chapter what tools and toolchains are readily
available.

# Provided tools and toolchains

The following tools can be used by naming them in `{checkout,build,package}Tools`:

* bison
* cpio
* flex
* pkg-config

The following cross compiling toolchains are available pre-configured. If you need
other targets you can depend on `devel::cross-toolchain` directly and configure it
as you like.

* `devel::cross-toolchain-x86_64-linux-gnu`: x86_64 toolchain for Linux with glibc.
* `devel::cross-toolchain-arm-linux-gnueabihf`: ARMv7-A Linux with glibc. Hard
  floating point ABI.
* `devel::cross-toolchain-arm-none-eabi`: ARMv7 bare metal toolchain with
  newlib libc.

To use a cross compiling toolchain include it where needed via:

    depends:
        - name: <recipe name here>
          use: [tools, environment]
          forward: True

