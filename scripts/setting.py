import gradio as gr
from modules import shared
from modules import script_callbacks


def on_ui_settings():
    section = ('controlnet-fastload', "Controlnet Fastload")
    shared.opts.add_option(
        "isEnabledManualSend",
        shared.OptionInfo(
            False,
            "Allow manually uploading pnginfo from the uploaded plugin image to txt2img or img2img.",
            gr.Checkbox,
            section=section).needs_restart()
    )
    shared.opts.add_option(
        "saveControlnet",
        shared.OptionInfo(
            "Extra .cni file",
            "Where to save Controlnet data?",
            gr.Dropdown,
            lambda: {"choices": ["Embed photo", "Extra .cni file", "Both"]},
            section=section)
    )
    shared.opts.add_option(
        "overwritePriority",
        shared.OptionInfo(
            "ControlNet Plugin First",
            "If the ControlNet Plugin is enabled, which do you use first?",
            gr.Dropdown,
            lambda: {"choices": ["ControlNet Plugin First", "ControlNet Fastload Plugin First"]},
            section=section)
    )
    """
    Plugin first -> ControlNet Plugin First
    Script first -> ControlNet Fastload Plugin First
    """


script_callbacks.on_ui_settings(on_ui_settings)
