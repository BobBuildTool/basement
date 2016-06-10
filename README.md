# Basement

These base recipes are used to build a Linux system from scratch with the Bob
build tool. In particular it builds a sandbox image (sandbox) with
corresponding native toolchain (sandbox-toolchain) that can be used by other
recipe sets as sandbox. Of course you can just build it and chroot into it for
fun.

# Prerequisites

* A x86_64 system with the regular development tools installed (gcc, make,
  perl, ...)
* Bob Build Tool (https://github.com/BobBuildTool/bob)
* Patience

# How to build

Clone the recipes and build them with Bob:

    $ git clone https://github.com/BobBuildTool/basement.git
	$ cd basement
	$ bob build sandbox

The recipes actually builds two sandboxes: a preliminary *bootstrap-sandbox*
and then, utilizing the bootstrap sandbox, the actual sandbox. This two stage
process should make sure that any impact of the host onto the actual result is
kept to the absolute minimum.
