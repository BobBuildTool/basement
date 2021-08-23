from os import makedirs
from os.path import join
from bob.errors import ParseError
from bob.input import PluginState, PluginProperty, PluginSetting

class ShortPathSetting(PluginSetting):
    pass

shortPathSetting = ShortPathSetting(None)

def shortPathFormatter(step, states):
    settings = shortPathSetting.getSettings()
    shortPath = settings.get('path') if settings else None
    if shortPath:
        makedirs(shortPath, exist_ok=True)
        return shortPath
    else:
        return ""

def commonFormatter(step, states):
    if step.isCheckoutStep():
        ret = step.getPackage().getRecipe().getName()
    else:
        base = step.getPackage().getName()
        ext = step.getEnv().get('AUTOCONF_HOST')
        ret = join(base, ext) if ext else base
    return ret.replace('::', "/")

def releaseFormatter(step, states):
    return join(shortPathFormatter(step, states), "work", commonFormatter(step, states), step.getLabel())

def developFormatter(step, states):
    return join(shortPathFormatter(step, states), "dev", step.getLabel(), commonFormatter(step, states))

def jenkinsFormatter(step, states):
    return join(shortPathFormatter(step, states), commonFormatter(step, states), step.getLabel())

manifest = {
    'apiVersion' : "0.3",
    'hooks' : {
        'releaseNameFormatter' : releaseFormatter,
        'developNameFormatter' : developFormatter,
        'jenkinsNameFormatter' : jenkinsFormatter
    },
    'settings' : {
        "ShortPath" : shortPathSetting,
    },
}
