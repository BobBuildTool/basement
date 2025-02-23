Introduction
============

The `Bob Build Tool <https://github.com/BobBuildTool/bob>`_ is a versatile
build automation tool. While it brings many mechanism, very little policies are
included. To build actual software, a number of foundational recipes and
classes are required. The basement layer provides exactly this.

* Classes for standard build systems (e.g. GNU autotools, CMake, ...)
* Compilers and interpreters for common languages (C/C++, Python, Rust)
* A standard sandbox image

Prerequisites
-------------

To use the basement layer, the following prerequisites should be fulfilled:

* A Linux or Windows MSYS2 ``x86_64`` system
* The following basic development tools should be installed
  * gcc >= 5.x
  * bash
  * POSIX awk (GNU awk version >= 3.1.5)
  * perl >= 5.6.1
  * GNU tar
  * gzip
  * bzip2
  * rsync
  * xz-utils
* The `Bob Build Tool <https://github.com/BobBuildTool/bob>`_

Layer architecture
------------------

The basement layer is intentionally kept to its bare minimum, providing the
above mentioned support. Anything that goes beyond that, is supposed to be kept
in separate layers. Specifically, the following other layers may be of interest:

* `basement-gnu-linux <https://github.com/BobBuildTool/basement-gnu-linux>`_ -
  Provides many recipes to build a GNU/Linux system. Note that the recipes are
  not restricted to be used on Linux. It is just that most of the packages are
  used for that and the name of the layer does not reflect the full breadth any
  more.

Examples
--------

There are some examples available that show how the layers are used:

 * `Embedded systems <https://github.com/BobBuildTool/bob-example-embedded>`_
 * `Linux containers <https://github.com/BobBuildTool/bob-example-containers>`_
