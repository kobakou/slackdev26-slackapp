from slack_bolt import App

from .define_command import define_command_callback
from .sample_command import sample_command_callback


def register(app: App):
    app.command("/sample-command")(sample_command_callback)
    app.command("/define")(define_command_callback)
