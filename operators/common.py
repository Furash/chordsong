import bpy


def prefs(context: bpy.types.Context):
    return context.preferences.addons[__package__.split(".")[0]].preferences


