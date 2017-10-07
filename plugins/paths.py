from os.path import join
from bob.errors import ParseError
from bob.input import PluginState, PluginProperty

def commonFormatter(step, states):
    if step.isCheckoutStep():
        ret = step.getPackage().getRecipe().getName()
    else:
        base = step.getPackage().getName()
        ext = step.getEnv().get('AUTOCONF_HOST')
        ret = join(base, ext) if ext else base
    return ret.replace('::', "/")

def releaseFormatter(step, states):
    return join("work", commonFormatter(step, states), step.getLabel())

def developFormatter(step, states):
    return join("dev", step.getLabel(), commonFormatter(step, states))

def jenkinsFormatter(step, states):
    return join(commonFormatter(step, states), step.getLabel())

manifest = {
    'apiVersion' : "0.3",
    'hooks' : {
        'releaseNameFormatter' : releaseFormatter,
        'developNameFormatter' : developFormatter,
        'jenkinsNameFormatter' : jenkinsFormatter
    },
}
