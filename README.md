# Basement

These base recipes are used to build a Linux system from scratch with the Bob
build tool. In particular it builds a sandbox image (sandbox) with
corresponding native toolchain (sandbox-toolchain) that can be used by other
recipe sets as sandbox. Of course you can just build it and chroot into it for
fun.

# Prerequisites

* A x86_64 system with the regular development tools installed (gcc, make,
  perl, ...)
* Bleeding edge Bob Build Tool (https://github.com/BobBuildTool/bob)
* Patience

# How to build

Clone the recipes and build them with Bob:

    $ git clone https://github.com/BobBuildTool/basement.git
    $ cd basement

## Sandbox image

    $ bob build devel::sandbox

The recipes actually builds two sandboxes: a preliminary *bootstrap-sandbox*
and then, utilizing the bootstrap sandbox, the actual sandbox. This two stage
process should make sure that any impact of the host onto the actual result is
kept to the absolute minimum.

The built sandbox image can be used for other Bob projects. You can also chroot
into it and take a look around:

    $ unshare -Urm $SHELL
    # sandbox=$(bob query-path -f '{dist}' --release devel::sandbox)
    # for i in dev proc sys ; do
    > mkdir -p $sandbox/$i
    > mount --rbind /$i $sandbox/$i
    > done
    # /usr/sbin/chroot $sandbox /bin/bash

## Lighttpd container

    $ bob build containers::lighttpd

This recipe builds a minimal container image that has solely lighttpd and the required
dependencies installed. It acutally makes use of the sandbox above while building
the container. To use it you have to import it in docker:

    $ tar -C $(bob query-path -f '{dist}' --release containers::lighttpd) -c . \
        | docker import - lighttpd

Now you can serve any host directory with the lighttpd in the image:

    $ docker run -it --rm -p 8080:80 -v <your-html-dir>:/srv/www lighttpd \
        /usr/sbin/lighttpd -D -f /etc/lighttpd/lighttpd.conf \
        -m /usr/lib/x86_64-linux-gnu/lighttpd

This will expose the lighttpd at port 8080 on your host.
