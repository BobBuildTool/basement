# Defines the "License" recipe key that can be used to describe the package license.
# If the package uses a vanilla license with a known spdx.id the license can be specified as:
#
# License: "GPL-3.0"
#
# and for custom licenses with a license file:
#
# License:
#    Id: "devel.m4"
#    Paths: "COPYING"
#
# The plugin also offers string functions to get these information back into the environment
# to be used by the licenses class.

# To enable the validation check of the license expression the license-expression module must be
# installed. (e.g. 'pip install license-expression').

from bob.errors import ParseError
from bob.input import PluginState, PluginProperty
from bob.tty import Warn
import schema

def expression_check(license):
    try:
        get_spdx_licensing().parse(license, validate=True, strict=True)
    except ExpressionError as e:
        # a raised exception message is not shown (?)
        print(e)
        return False
    else:
        return True

def dummyCheck (license):
    return True

try:
    from license_expression import get_spdx_licensing, ExpressionError
except ImportError as e:
    Warn ("Unable to import license_expression module. License expressions will not be checked!").warn()
    license_check = dummyCheck
else:
    license_check = expression_check

LICENSE_SHEMA = schema.Schema(schema.Or(str, schema.Schema({'Id' : str, 'Paths' : str})))

class LicenseProperty(PluginProperty):
    @staticmethod
    def validate(data):
        try:
            lic = LICENSE_SHEMA.validate(data)
        except schema.SchemaError as e:
            print(e)
            return False
        if isinstance(lic, str):
            return license_check(lic)
        return True

def pkgLicense(args, env, recipe, **kwargs):
    lic = recipe.getPluginProperties().get('License').getValue()
    if lic is not None:
        if isinstance(lic, str):
            return lic
        else:
            return "LicenseRef-"+lic.get('Id')
    return "UNSET"
    #raise ParseError(f"{recipe.getName()} has no LICENSE")

def pkgLicensePaths(args, env, recipe, **kwargs):
    lic = recipe.getPluginProperties().get('License').getValue()
    if lic and isinstance(lic, dict):
        return lic.get('Paths', "")
    return ""

manifest = {
    'apiVersion' : "1.1",
    'properties' : {
        'License' : LicenseProperty,
    },
    'stringFunctions' : {
        'pkg_license' : pkgLicense,
        'pkg_license_paths' : pkgLicensePaths
    }
}
