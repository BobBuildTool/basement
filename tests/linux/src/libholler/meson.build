project('libholler', 'c',
  version : '0.1',
  default_options : ['warning_level=3'])

lib = library('holler', 'holler.c',
	version : '0.1.0',
	soversion : '0',
	install : true,
)

install_headers('holler.h')

pkgcfg = import('pkgconfig')
pkgcfg.generate(lib,
	name : 'libholler',
	filebase : 'libholler'
)
