project('libgreet', 'c',
  version : '0.1',
  default_options : ['warning_level=3'])

libholler = dependency('libholler')

lib = library('greet', 'greet.c',
	version : '0.1.0',
	soversion : '0',
	install : true,
	dependencies : libholler
)

install_headers('greet.h')

pkgcfg = import('pkgconfig')
pkgcfg.generate(lib,
	name : 'libgreet',
	filebase : 'libgreet'
)
