Usage notes
===========

Basic setup
-----------

First, you need to add the basement layer to your project. To do so, add a
:external:ref:`configuration-config-layers` entry to your
:external:ref:`config.yaml <configuration-config>`::

    bobMinimumVersion: "1.0"
    layers:
        - name: basement
          scm: git
          url: https://github.com/BobBuildTool/basement.git

This will always use the latest version. You probably want to add a specific ``commit``
so that always the same recipes are used. Next, the layer must be fetched. For that,
do a::

    bob layers update

To use all facilities of the basement project, you just need to inherit the
``basement::rootrecipe`` class in your root recipe::

    inherit: [ "basement::rootrecipe" ]

This will make your recipe a root recipe and already setup the sandbox with a
proper host toolchain. See the next chapter what tools and toolchains are readily
available.

C/C++ toolchains
----------------

Before delving into the details, some definitions are necessary. The basement layer
uses the same terms that were establisdhed by the autoconf project. In principle, three
different systems are distinguished:

The *build* system
    This is the system where the build is executed, i.e. where Bob and the
    compiler is running. The ``AUTOCONF_BUILD`` variable describes the build
    system and is always defined.

The *host* system
    The host system is where the compiled binaries are meant to be executed.
    For embedded build systems, this is sometimes called the "target" system.
    The ``AUTOCONF_HOST`` variable represents this system. If set and different
    than ``AUTOCONF_BUILD``, the package is cross compiled.

The *target* system
    This system is only applicable to compilers and their related tools. It is
    stored in the ``AUTOCONF_TARGET`` variable. It describes the system for
    which the compiler produces the object code. For a cross-compiler, the
    *target* system is different from the *host* system where the compiler is
    executed.  Of *build* and *target* system are identical, it is called a
    native compiler.

The different systems are described as a so-called *target triplet*. Even
though it is used ubiquitously, it is only loosely defined. In fact, it may not
even have exactly three fields as the name suggests. It generally has the
format of ``arch-vendor-system`` where ``system`` may either be the ``os``
(operating system) or ``kernel-os``. See the `autoconf documentation
<https://autotools.info/autoconf/canonical.html>`_.

In almost all cases, projects will use cross compilation. This is even the case
where the build system and the host system have the same architecture and
operating system. The rationale is to be as independent from the build system
as possible.  Using native compiler always has the drawback that the result
relies at least on the libc of the build system and is thus not portable across
machines.

Selecting a C/C++-toolchain
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To select the desired toolchain, add a dependency in the following format early
in your project dependency list::

    depends:
        - name: <toolchain name here>
          use: [tools, environment]
          forward: True

The following toolchains are predefined for commonly used target systems:

* ``devel::cross-toolchain-aarch64-linux-gnu``: ARMv8-A AArch64 Linux with glibc.
* ``devel::cross-toolchain-aarch64-none-elf``: ARMv8-A/R AArch64 bare metal
  toolchain with newlib libc.
* ``devel::cross-toolchain-arm-linux-gnueabihf``: ARMv7-A Linux with glibc. Hard
  floating point ABI.
* ``devel::cross-toolchain-arm-none-eabi``: ARMv7 bare metal toolchain with
  newlib libc.
* ``devel::cross-toolchain-x86_64-linux-gnu``: x86_64 toolchain for Linux with glibc.
* ``devel::cross-toolchain-riscv64-linux-gnu``: RISC-V toolchain targeting the GC
  profile.

Read on to learn how to switch to different toolchains for selected
dependencies or how to define your own if the standard ones are not sufficient.

All toolchains compile for a reasonable default architecture model that is
supposed to be widely supported. To tweak the standard compile flags, the
following variables may be optionally set when pulling in the toolchain.

``BASEMENT_OPTIMIZE``
    Compiler optimization level (``-O``). Defaults to ``s`` to optimize for
    small binaries.

``BASEMENT_DEBUG``
    May be ``0`` or ``1`` and controls the generation of debugging information.
    Defaults to ``1``.

``CROSS_TOOLCHAIN_CPU``
    If set, adds an ``-mcpu=`` option to the compiler flags with the value. It
    overrides the default CPU selection of the toolchain.

``CROSS_TOOLCHAIN_ARCH``
    If set, adds an ``-march=`` option to the compiler flags with the value. It
    overrides the default architecture selection of the toolchain.

Standard tools
~~~~~~~~~~~~~~

There are two tools that are meant to be used by recipes that compile C/C++
code.

``target-toolchain``
    This is the main toolchain. Every C/C++ package uses it. It represents the
    compiler that builds for the target system where the package should run in
    the end. Usually, but not necessarily, this is a cross compiler even on the
    same architecture.

    A recipe should make no assumption about which compiler this is and for
    which architecture or operating system it compiles. This is the key
    ingredient for making Bob projects flexible because the
    ``target-toolchain`` may be replaced anywhere in the dependency tree and
    all dependencies beneath it will automatically be compiled for the
    configured target.

``host-toolchain``
    This toolchain represents the native host machine compiler.  Even though it
    builds host executables, it does never :external:ref:`fingerprint
    <configuration-principle-fingerprinting>` the results. Instead, it is
    intended to be used in the ``buildScript`` if the package *also* needs the
    host compiler during build time where none of the host build object code is
    part of the result. Points to the host gcc or the gcc of the sandbox. Only
    selected packages need it when being built in the sandbox.

Given the above definitions, practically all recipes that build C/C++ code will do
a::

    buildTool: [target-toolchain]

to use the currently selected C/C++ compiler. Only if the build requires the
native compiler too (e.g. to build some intermediate build tool),
``host-toolchain`` may be added to ``buildTool``.

There are two other tools that are always defined. They are intended to be used
at special places where they replace the ``target-toolchain`` for selected
dependencies.

``host-compat-toolchain``
    A toolchain that builds portable host executables that should be able to
    run on the oldest supported Ubuntu LTS. Even though it builds for the host
    architecture and operating system, it is a cross compiler with a backwards
    compatible glibc version. When using the ``basement::rootrecipe`` class,
    this is the default ``target-toolchain``. It is defined as a dedicated name
    to be able to compile specifically for the host when needed::

      depends:
        - ...
        - name: some::package
          tools:
            target-toolchain: host-compat-toolchain

    This will build ``some::package`` for the host regardless of the currently
    defined target toolchain. It comes in handy if some special tool is needed
    to compile a package.

``host-native-toolchain``
    This toolchain represents the native host machine compiler. In contrast to
    ``host-toolchain`` it *does* fingerprint the system.  This implies that
    binary artifacts of such packages are not exchangeable between systems!  It
    is used if a package needs to be compiled natively and the object code is
    part of the package result. Like in the ``host-compat-toolchain`` example
    above, it is usually supplied as ``target-toolchain`` for selected
    dependencies.

    An example for the necessity of the ``host-native-toolchain`` is for
    example Python.  To cross-compile python, the same version is required on
    the build system. Therefore, Python needs to be first compiled natively.
    Then Python can be cross compiled by whatever ``target-toolchain`` is
    configured. See the following excerpt from the ``basement::rootrecipe``
    class where this is already done for you::

        depends:
          - name: python::python3-minimal
            use: [tools]
            forward: True
            tools:
                # To build python3 a working python interpreter is required. Build
                # a bootstrap python3 interpreter with the native host toolchain.
                # The real interpreter is then built with the
                # host-compat-toolchain.
                target-toolchain: host-native-toolchain

          - python::python3

Switching cross-compilers
~~~~~~~~~~~~~~~~~~~~~~~~~

Once a cross-compiling toolchain has been selected, all following dependencies
are built by this compiler. As this applies to all packages, selecting a
different cross compiler requires some special care. Suppose a root recipe has
the following (intentionally incorrect!) dependency list::

    inherit: ["basement::rootrecipe"]
    depends:
        - name: devel::cross-toolchain-aarch64-linux-gnu
          use: [tools, environment]
          forward: True

        - utils::bash

        - name: devel::cross-toolchain-arm-none-eabi
          use: [tools, environment]
          forward: True

        - some::firmware

.. warning::
   The example above does *not* work but is used as an illustration what needs
   to be considered.

The above example will unfortunately not work as expected. The reason is that after
the ``devel::cross-toolchain-aarch64-linux-gnu`` dependency, *everything* will be
compiled for Linux AArch64. This includes the ``devel::cross-toolchain-arm-none-eabi``
dependency too! But this compiler needs to be executed on the build system. Therefore,
the ``target-toolchain`` used for the compiler needs to be replaced with the
``host-compat-toolchain``::

    depends:
        ...
        - name: devel::cross-toolchain-arm-none-eabi
          use: [tools, environment]
          forward: True
          tools:
              target-toolchain: host-compat-toolchain

        - some::firmware

As you can see, the ``devel::cross-toolchain-arm-none-eabi`` is built
explicitly with the ``host-compat-toolchain``, regardless of which other
toolchain is configured at this point.

Installing a compiler in the target system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes, the toolchain should be installed on the target system. This works
like for any other package. The only difference is that the ``use`` list does
not have the ``tools`` key because the compiler should be installed rather than
used at build time::

    inherit: ["basement::rootrecipe"]
    depends:
        # The toolchain for the target system
        - name: devel::cross-toolchain-aarch64-linux-gnu
          use: [tools, environment]
          forward: True

        # The native compiler and binutils for the target system
        - devel::binutils
        - devel::gcc-native

The above example installs a native compiler into the target system. That is, this compiler
will produce binaries for the same system. Similarly, a cross-compiler could be installed
as well::

    inherit: ["basement::rootrecipe"]
    depends:
        # The toolchain for the target system
        - name: devel::cross-toolchain-aarch64-linux-gnu
          use: [tools, environment]
          forward: True

        - devel::cross-toolchain-arm-none-eabi

The toolchain will be compiled for the AArch64 Linux system and will produce
object code for AArch32 bare-metal systems. Note the absence of the ``use:
[tools, environment]`` and ``forward: True`` lines from the
``devel::cross-toolchain-arm-none-eabi`` dependency.

Advanced toolchain selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the pre-configured toolchains are not sufficient, it is possible to compile
almost any custom GNU gcc/binutils based Linux toolchain. Starting point is
the generic ``devel::cross-toolchain`` recipe. This unconfigured cross-compilation
toolchain needs to be configured. At least the following variables need to be
defined for it:

``ARCH``
    The target architecture. This is based on the architectures as defined by
    the Linux kernel. Valid choices are, among others, ``arm``, ``arm64``,
    ``i386``, ``x86_64`` or ``riscv``. See the Linux kernel documentation for
    all possible values.

``AUTOCONF_TARGET``
    The autoconf target triplet that describes the system. This is the primary
    variable that affects the toolchain and needs to be aligned with the other
    switches. See below for some rough guidelines.

``GCC_LIBC``
    The C-library that should be used by the toolchain. Valid choices are
    ``glibc``, ``newlib`` and ``uclibc-ng``.

The following, additional variables are available to tweak the toolchain:

``GCC_TARGET_ARCH``
    This is passed as ``--with-arch=`` to the gcc configure script and provides
    the default value for the ``-march=`` gcc option. As such, it sets the
    default target architecture that the compiler is using. It is recommended
    to pass this switch to choose the right architectural features. See the
    `GCC machine dependent options
    <https://gcc.gnu.org/onlinedocs/gcc-14.2.0/gcc/Submodel-Options.html>`_ for
    the supported values of the ``-march=`` option.

``GCC_TARGET_ABI``
    Passed as ``--with-abi=`` to the gcc configure script and provides the
    default value for the ``-mabi=`` option. This is used for example for
    RISC-V to choose between the different possible ABIs.

``GCC_TARGET_FLOAT_ABI``
    May be either ``hard`` or ``soft``.

``GCC_TARGET_FPU``
    Passed as ``--with-fpu=`` to the gcc configure script and provides the
    default value for the ``-mfpu=`` option. Again, the acceptable values
    depend on the chosen target.

``GCC_MULTILIB``
    If set, provides the comma separated set of multilibs to build. The
    permissible values depend on the target architecture. Currently, the
    basement layer only supports ``m32,m64`` on ``x86_64``.

``GCC_ENABLE_LANGUAGES``
    Comma separated list of languages that gcc should support. Defaults to
    ``c,c++``.

``GCC_EXTRA_OPTIONS``
    If set, it is passed verbatim to the gcc configure script.

TODO: Explain target triplet choices.

Standard variables for C/C++ packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using the ``target-toolchain``, the following variables are available. The
variables have the same name as the executable that is normally available on
the build system.

* ``AR``: The archiver to create/modify static libraries.
* ``AS``: The assembler.
* ``CC``: The C-compiler.
* ``CPP``: The C preprocessor.
* ``CXX``: The C++-compiler.
* ``LD``: The linker.
* ``NM``: Tool to inspect object symbol tables.
* ``OBJCOPY``: Tool to copy and translate object files.
* ``OBJDUMP``: Print object file contents.
* ``RANLIB``: Tool to (re-)generate symbol index of a static library.
* ``READELF``: Display information about ELF files.
* ``STRIP``: Tool for stripping unneeded sections and symbols from object files.

Other meta information variables that are not directly linked to a particular
executable are:

* ``AUTOCONF_HOST``: Set for cross-compiler to the *host* system target triplet.
* ``CROSS_COMPILE``: Cross compile prefix for standard tool of a
  cross-compiling toolchain, e.g., ``riscv64-linux-gnu-`` for a RISC-V Linux
  cross toolchain. Some build systems use this method to find the right tools
  instead of the individual variables above (``AR``, ...).
* ``TOOLCHAIN_FLAVOUR``: Basically the compiler vendor. Can be ``gcc`` which is
  the basement layer main compiler, ``clang`` for LLVM clang and ``msvc`` for
  Windows builds with the Microsoft Visual C++ compiler.

.. attention::
   The above variables are defined by ``target-toolchain`` only. If it is
   missing from ``buildTools``, they will be undefined!

The following variables are not defined by ``target-toolchain`` but are part of
the normal environment variables. The reason is that recipes should be able to
amend or replace them at any place.

* ``CPPFLAGS``: Preprocessor options, e.g., ``-DMACRO=definition``.
* ``CFLAGS``: Compiler options that are used when compiling C-code.
* ``CXXFLAGS``: Compiler options that are used when compiling C++-code.
* ``LDFLAGS``: Options used when linking. Note that they are passed to the
  compiler driver (e.g., ``gcc`` or ``clang``) and therefore need to be wrapped
  appropriately (e.g., ``-Wl,<option>`` in case of ``gcc`` or ``clang``).

Feature variables
~~~~~~~~~~~~~~~~~

For some architectures, the cross compilation toolchains provide variables that
indicate the available features of the selected target architecture. This
information is derived from the toolchain defaults and any
``CROSS_TOOLCHAIN_ARCH`` and ``CROSS_TOOLCHAIN_CPU`` settings made.

* Arm: ``CPU_HAS_VFPV2``, ``CPU_HAS_VFPV3``, ``CPU_HAS_VFPV4``, ``CPU_HAS_NEON``
* Arm64: ``CPU_HAS_SVE``, ``CPU_HAS_SVE2``, ``CPU_HAS_SME``
* x86_64: ``CPU_HAS_SSE3``, ``CPU_HAS_SSSE3``, ``CPU_HAS_SSE41``,
  ``CPU_HAS_SSE42``, ``CPU_HAS_AVX``, ``CPU_HAS_AVX2``, ``CPU_HAS_AVX512``. All
  CPU features before and including SSE2 are implicitly assumed to be present.

Standard build systems
----------------------

The following build tools are supported by the basement layer. See the
respective section below for the particular usage notes.

CMake
~~~~~

Python 3
--------

Perl
----

.. TODO

Ocaml / opam / dune
-------------------

Ocaml is available for building ocaml host tools only. ATM there is no cross
compiling support.

See `tests/linux/recipes/ocaml/hello.yaml` for a hello world example using dune.

Rust
----

Available development tools
---------------------------

The following tools can be used by naming them in
:external:ref:`configuration-recipes-tools`:

* bison
* cpio
* flex
* make
* pkg-config
* squashfs-tools
* e2fsprogs
* util-linux
