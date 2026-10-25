from helpers.extension import Extension


class DurablePreserveImports(Extension):
    def execute(self, data):
        from usr.plugins.durable_execution.helpers.bridge import preserve_modules
        preserve_modules()
