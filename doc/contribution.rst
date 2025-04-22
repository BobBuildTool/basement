Contribution guide
==================

The Bob Build Tool and the Basement project are open-source, community-based
projects. Contributions are very welcome. The following sections should give
some guidance how to create new recipes or improve existing ones.

Before you start
----------------

Please read the following chapters about the recipe style. Adhering to the
guidelines helps to make the process as frictionless as possible.

The YAML files are checked automatically on Github for some common style
errors. This is done with the help of `pre-commit <https://pre-commit.com/>`_.
You can either install pre-commit for the repository by running ``pre-commit
install`` or run it manually before committing via ``pre-commit run`` on all
modified files.

Anatomy of a recipe
-------------------

The general structure of a recipe building some C/C++ code looks like the
following::

    inherit: [autotools]

    depends:
        - libs::pcre-lib-1-dev
        - use: []
          depends:
            - libs::pcre-lib-1-tgt

    metaEnvironment:
        PKG_VERSION: "3.11"
        PKG_LICENSE: "GPL-3.0-or-later"

    checkoutSCM:
        scm: url
        url: ${GNU_MIRROR}/grep/grep-${PKG_VERSION}.tar.xz
        digestSHA1: "955146a0a4887eca33606e391481bbef37055b86"
        stripComponents: 1

    buildScript: |
        autotoolsBuild $1 \
            --without-included-regex

    packageScript: |
        autotoolsPackageTgt

    provideDeps: [ "*-tgt" ]


1. Any classes that are inherited are named at the top of the recipe. Only
   include classes that are actually needed.
2. Usually, recipes depend on other recipes because the package needs other
   libraries to work. They are named in the
   :external:ref:`configuration-recipes-depends` section. Notice that each
   dependency is usually listed twice: the build time library dependency
   (``-dev``) that has the headers and the static or dynamic libraries. The
   same dependencies are again listed as runtime dependency. These packages end
   with the ``-tgt`` suffix by convention.
3. The :external:ref:`configuration-recipes-metaenv` variables describe the
   package. See :ref:`contrib-meta-vars` for more details.
4. The :external:ref:`configuration-recipes-scm` part fetches the source code.
   Always make sure that the checkout is determinisitc. This can be a hash sum
   for tarballs like the example above or a git commit id. If tarballs or other
   archives are available, they are very much preferred. Only use git clones or
   other "real" SCMs if release tarballs are not available.
5. The build script does the actual job of building the package. In case of
   standard build systems, this should only be a couple of lines, passing
   necessary configuration options to the standard build system wrappers.
6. In the ``packageScript`` the desired output is fetched from the build tree
   of the package.
7. As a last step, all runtime dependencies are passed downstream by the
   :external:ref:`configuration-recipes-providedeps` property.

This pattern is the basis for almost all recipes. Some sections might not be
necessary while others need additional things. See the following sections for
more information about the various package types.

C / C++ libraries
~~~~~~~~~~~~~~~~~

.. TODO: Multiple packages with different licenses - USe PKG_LICENSE inside of
   multiPackage

Libraries with applications
~~~~~~~~~~~~~~~~~~~~~~~~~~~



Recipe style guide
------------------

There are a couple of general coding style rules:

* Indent by 4 spaces
* Lines should break after 80 characters. The hard line length limit is 120
  characters.
* ...

.. _contrib-meta-vars:

Standard meta variables
~~~~~~~~~~~~~~~~~~~~~~~

Meta variables, like the name suggests, hold meta information like the version
or license about the recipe. So far, the following standard variables have been
defined:

``PKG_VERSION``
    The version of the package that is built. Must be present when the recipe
    downloads a source code package. The version number should be exactly like
    the upstream package declared it. For packages that do not have an exact
    version number, like untagged git commits, a sensible version string should
    still be used e.g., ``v0.25.0-4-gee29e75c``.

``PKG_LICENSE``
    The license of the package as `SPDX License Identifier
    <https://spdx.org/licenses/>`_. Must be present when the recipe downloads a
    source code package. In the best case, a single identifier applies.
    Sometimes, a more complicated license expression (e.g.  ``GPL-2.0-only OR
    BSD-3-Clause``) is required. See the SPDX specification for details how
    licenses are expressed.

Declaring configuration variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configuration variables of a recipe are used to parametrize the build of the
package. They are used for example to enable or disable certain features.

Such variables should be named like the base name of the recipe. For example,
the ``recipes/devel/gcc.yaml`` recipe declares multiple packages but all
configuration variables have a common ``GCC_`` prefix. Rationale: there are
usually no two recipes with the same name in different categories and we want
to keep variable names short. This naming scheme only applies to "public"
variables, though. Variables declared in ``privateEnvironment`` can be named as
needed without any restrictions.

Avoid any other prefixes like ``CONFIG_`` or ``FEATURE_``. They usually don't
add and information about the variable but make it longer.

To make configuration variables discoverable, a dedicated *config* plugin is
used by the basement project that adds an optional ``Config`` recipe key. It be
used to describe configuration variables in a machine-readable format.
Examples::

    Config:
        FOO_VERSION:
            help: overrides the default package version
        FOO_DEBUG:
            type: bool
            help: Enable debugging. Disabled by default.
            default: False
        FOO_COLOR:
            type: choice
            required: True
            choice:
                red:
                    help: It's red
                green:
                blue:
        FOO_REQUIRED_VAR:
            type: str          # this is the default type anyway
            required: True     # But variable must be present
        FOO_USERS:
            type: int          # A C/C++ integer literal
            range: [1, 10]
            default: 5
        FOO_BASE_ADDRESS:
            type: hex
            prefix: True               # Require "0x" prefix
            range: [0x00, 0xffffffff]  # The range is optional
        FOO_NUM:
            type: decimal
        FOO_MODE:
            type: octal
            prefix: False # Prevent leading "0"
            range: [0, 07777]

Variables declared in this way do not need to be present. You can set the
``required`` key to ``True`` to enforce the presence of the variable.  Even
though variables in Bob are always string, the format can be constrained by the
``Config`` definition. The following types (``type: ...``) are available:

``str``
    An arbitrary string. This is the default and does not need to be named.

``bool``
    A boolean string that is either ``0`` or ``1``.

``choice``
    An enumeration of allowed values. Each value can optionally have a help
    string.

``int``
    A C/C++ integer literal.

``hex``
    A hexadecimal number. By default, a ``0x`` prefix is accepted but not
    required. Set ``prefix`` to ``True`` when requiring a ``0x`` prefix.
    Setting ``prefix`` to ``False`` rejects a ``0x`` prefix.

``decimal``
    A decimal number. Unlike the ``int`` type, leading zeros are accepted and
    do not change the interpretation.

``octal``
    An octal number. By default, leading zeroes are accepted and do not change
    the interpretation. Set ``prefix`` to ``True`` when requiring a leading
    zero.  Setting ``prefix`` to ``False`` rejects a leading zero.

All number types (``int``, ``hex``, ``decimal``, ``octal``) can optionally have
a ``range`` property::

    type: int
    range: [0, 100]

Optionally, a ``default`` property might set a default value if the variable is
not present.

Enforced checks:

 * A ``required`` variable must be present.
 * The ``bool`` type checks that the variable is either ``0`` or ``1``.
 * The ``choice`` type checks that only one of the declared choices is used.
 * Number types are checked that they can be parsed. The ``hex`` and ``octal``
   types may have prefixes. Their presence or absence is checked depending on
   the ``prefix`` setting.
 * All number types can have an optional range that is checked.

Class style guide
-----------------

Regarding the functions in classes, the function name should start with the
class name.  The rest of the name is using camel case. For example, for class
``foo`` might define functions ``fooBuild`` and ``fooBarBaz``.

Classes should typically have no side effect. They should just declare
functions and variables in :external:ref:`checkout/build/packageSetup
<configuration-recipes-setup>`.

Recipe naming
-------------

When creating new recipes, the respective layer must be chosen first. Almost
always, the ``basement-gnu-linux`` layer is the right one. The only reason to
put something new into the ``basement`` layer is when it is required to support
a (new) build system or standard toolchain.

New recipes should be placed next to similar other recipes. Recipes are placed
into different categories. The following list should provide some guideline to
choose the right category. It is not uncommon that multiple categories apply.
In this case, the first matching category of the following list should be used.
If in doubt, create a discussion on Github or ask on the mailing list.

``libs``
  C and C++ libraries to make other programs work. Libraries are packages that
  provide header files and static and/or dynamic libraries that are used by
  other packages. Even if the package additionally provides some application
  based on the library, the ``libs`` category should be used.

  Other languages (e.g. Python) have their own category and libraries of these
  languages should be placed there. On the other hand, there are sometimes
  large collections of libraries that are related to each other. Such
  libraries are further put into sub-categories:

  ``gnome``
    Libraries that are coming from the Gnome project.

  ``xorg``
    Libraries that are related to the X.Org project.

Some interpreted languages have their own category. This includes the
interpreter itself, libraries and applications written in this language.

``perl``
  Everything about Perl.

``python``
  Everything about Python 3. Support for Python 2 has been removed.

The other categories do not really have a preference between each other.

``bsp``
  Anything with links to specific hardware or hardware configuration
  information. These are for example firmware like the Arm Trusted Firmware or
  boot loaders like Grub and U-Boot. On the other hand, this should not include
  packages of other categories just because they have been modified for a
  particular SOC. They should stay in their respective category and either
  get a dedicated sub-category or a vendor suffix.

  If BSP components have been modified by a SOC vendor, they should go into a
  corresponding sub-category. Examples:

  ``imx``
    NXP i.MX series BSP components.

  ``rpi``
    RaspberryPi specific components.

``core``
  Basic files and daemons that are essential to boot the system. This includes
  utilities to administer system resources, manage user accounts, etc.

``db``
  Database Servers and Clients.

``devel``
  Development utilities, compilers, development environments, libraries, etc.
  Basically anything that is required to build other software.

``editors``
  Software to edit files. Programming environments.

``graphics``
  Applications, utilities and files that are graphics related.

  ``fonts``
    Fonts.

  ``gnome``
    Applications of the GNOME desktop environment.

  ``wayland``
    Wayland specific applications and utilities.

  ``xorg``
    X11 specific applications and utilities.

``kernel``
  Operating System Kernels and related modules.

``multimedia``
  Codecs and support utilities for audio, images and video.

``net``
  Daemons and clients to connect the system to the world.

``text``
  Text processing applications and utilities. This includes dictionaries and
  converters.

``utils``
  Shells, utilities for file/disk manipulation, backup and archive tools,
  system monitoring, input systems, etc. Basically any tool that does not fit
  in any of the other categories.

``virtual``
  Virtual packages. Inside the virtual category the sub-categories form the
  same hierarchy like it would for non-virtual packages. That is, any of the
  main categories can be present.
