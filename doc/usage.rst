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
