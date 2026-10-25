from helpers.extension import Extension


class DurableEnable(Extension):
    def execute(self, data):
        args, kwargs = data["args"], data["kwargs"]
        name = kwargs.get("plugin_name", args[0] if args else "")
        enabled = kwargs.get("enabled", args[1] if len(args) > 1 else False)
        if name == "durable_execution" and enabled and not data.get("exception"):
            from usr.plugins.durable_execution.helpers.bridge import start, recover, deactivate
            try:
                start()
                recover()
            except BaseException:
                from helpers import plugins
                deactivate()
                plugins.toggle_plugin("durable_execution", False)
                raise
