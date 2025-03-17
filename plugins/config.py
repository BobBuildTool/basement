# Defines the "Config" recipe key that can be used to describe configuration
# variables. Examples:
#
#Config:
#    FOO_VERSION:
#        help: overrides the default package version
#    FOO_DEBUG:
#        type: bool
#        help: Enable debugging. Disabled by default.
#    FOO_COLOR:
#        type: choice
#        required: True
#        choice:
#            red:
#                help: It's red
#            green:
#            blue:
#    FOO_REQUIRED_VAR:
#        type: str # this is the default type anyway
#        required: True # But variable must be present
#    FOO_USERS:
#        type: int # A C integer literal
#        range: [1, 10]
#    FOO_BASE_ADDRESS:
#        type: hex
#        required: True
#        prefix: True # Require "0x" prefix
#        range: [0x00, 0xffffffff] # The range is optional
#    FOO_NUM:
#        type: decimal
#    FOO_MODE:
#        type: octal
#        prefix: False # Prevent leading "0"
#        range: [0, 07777]

from bob.errors import ParseError
from bob.input import PluginState, PluginProperty
import re
import schema

class TwoInts:
    def validate(self, data):
        data = schema.Schema([int]).validate(data)
        if len(data) != 2:
            raise schema.SchemaError("range property must have two integers")
        return data

COMMON_SCHEMA = schema.Schema({
    schema.Optional('type') : schema.Or("choice", "bool", "str", "int",
                                        "octal", "decimal", "hex"),
    schema.Optional('required') : bool,
}, ignore_extra_keys=True)

CHOICE_SCHEMA = schema.Schema({
    'type' : 'choice',
    schema.Optional('required') : bool,
    schema.Optional('help') : str,
    'choice' : schema.Schema({
        str : schema.Or(None, { schema.Optional('help') : str })
    })
})

BOOL_SCHEMA = schema.Schema({
    'type' : 'bool',
    schema.Optional('required') : bool,
    schema.Optional('help') : str,
})

STR_SCHEMA = schema.Schema({
    schema.Optional('type') : 'str',
    schema.Optional('required') : bool,
    schema.Optional('help') : str,
})

INT_SCHEMA = schema.Schema({
    'type' : 'int',
    schema.Optional('required') : bool,
    schema.Optional('help') : str,
    schema.Optional('range') : TwoInts(),
})

OCTAL_SCHEMA = schema.Schema({
    'type' : 'octal',
    schema.Optional('required') : bool,
    schema.Optional('prefix') : bool,
    schema.Optional('help') : str,
    schema.Optional('range') : TwoInts(),
})

DECIMAL_SCHEMA = schema.Schema({
    'type' : 'decimal',
    schema.Optional('required') : bool,
    schema.Optional('help') : str,
    schema.Optional('range') : TwoInts(),
})

HEX_SCHEMA = schema.Schema({
    'type' : 'hex',
    schema.Optional('required') : bool,
    schema.Optional('prefix') : bool,
    schema.Optional('help') : str,
    schema.Optional('range') : TwoInts(),
})

ALL_SCHEMA = {
    'choice' : CHOICE_SCHEMA,
    'bool' : BOOL_SCHEMA,
    'str' : STR_SCHEMA,
    'int' : INT_SCHEMA,
    'octal' : OCTAL_SCHEMA,
    'decimal' : DECIMAL_SCHEMA,
    'hex' : HEX_SCHEMA,
}

class VarValidator:
    def validate(self, data):
        COMMON_SCHEMA.validate(data)
        ALL_SCHEMA[data.get('type', "str")].validate(data)
        return data

SCHEMA = schema.Schema({ str : VarValidator() })

class ConfigProperty(PluginProperty):
    @staticmethod
    def validate(data):
        try:
            SCHEMA.validate(data)
            return True
        except schema.SchemaError as e:
            print("Config schema error:", e)
            return False

    def inherit(self, cls):
        if self.present:
            if cls.present:
                # Take only new values from class
                self.value.update({ name : descr for name, descr in cls.value.items()
                                    if name not in self.value })
        else:
            self.present = cls.present
            self.value = cls.value


def handleChoice(var, val):
    if val not in var["choice"]:
        return f"Invalid 'choice': key '{val}' not defined"

def handleBool(var, val):
    if val not in ("0", "1"):
        return f"'{val}' is not a boolean"

def handleStr(var, val):
    pass

NUM_HANDLERS = {
    0  : (re.compile(r"0[xX][0-9a-fA-F]+|0[0-7]+|[1-9][0-9]*"), None, "C-like"),
    8  : (re.compile(r"[0-7]+"), "0",  "octal"),
    10 : (re.compile(r"[0-9]+"), None, "decimal"),
    16 : (re.compile(r"(0[xX])?[0-9a-fA-F]+"), "0x", "hexadecimal"),
}

def parseCNum(val):
    if val.startswith("0"):
        if val == "0":
            return 0
        elif val[1] == 'x' or val[1] == 'X':
            return int(val, 16)
        else:
            return int(val, 8)
    else:
        return int(val, 10)

def handleNum(var, val, base, prefix):
    regex, prefixStr, name = NUM_HANDLERS[base]
    if prefixStr:
        if prefix == True:
            if not val.startswith(prefixStr):
                return f"missing prefix '{prefixStr}' in '{val}'"
        elif prefix == False:
            if val.startswith(prefixStr):
                return f"forbidden prefix '{prefixStr}' in '{val}'"

    if not regex.fullmatch(val):
        return f"'{val}' is not a {name} number"

    try:
        val = parseCNum(val) if base == 0 else int(val, base)
    except ValueError:
        return f"'{val}' is not a {name} value"

    rng = var.get("range")
    if rng is not None:
        if val < rng[0]:
            return f"'{val}' is below allowed range [{rng[0]} - {rng[1]}]"
        if val > rng[1]:
            return f"'{val}' is above allowed range [{rng[0]} - {rng[1]}]"

def handleCLike(var, val):
    return handleNum(var, val, 0, None)

def handleOctal(var, val):
    return handleNum(var, val, 8, var.get("prefix"))

def handleDecimal(var, val):
    return handleNum(var, val, 10, None)

def handleHex(var, val):
    return handleNum(var, val, 16, var.get("prefix"))

HANDLER = {
    'str' : handleStr,
    'choice' : handleChoice,
    'bool' : handleBool,
    'int' : handleCLike,
    'octal' : handleOctal,
    'decimal' : handleDecimal,
    'hex' : handleHex,
}

class ConfigState(PluginState):
    def onFinish(self, env, properties):
        cfg = properties.get("Config")
        if not (cfg and cfg.isPresent()): return
        for name, var in cfg.getValue().items():
            typ = var.get("type", "str")
            val = env.get(name)
            if val is None:
                if var.get("required", False):
                    raise ParseError(f"Config: required variable {name} not present!")
                continue

            err = HANDLER[typ](var, val)
            if err:
                raise ParseError(f"Config: {name}: {err}")

manifest = {
    'apiVersion' : "0.25",
    'properties' : {
        'Config' : ConfigProperty,
    },
    'state' : {
        "Config" : ConfigState,
    },
}
