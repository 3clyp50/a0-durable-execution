from helpers.extension import Extension


class DurableDisable(Extension):
    def execute(self, data):
        args, kwargs = data["args"], data["kwargs"]
        name = kwargs.get("plugin_name", args[0] if args else "")
        enabled = kwargs.get("enabled", args[1] if len(args) > 1 else True)
        if name == "durable_execution" and not enabled:
            from usr.plugins.durable_execution.helpers.bridge import deactivate
            deactivate()
