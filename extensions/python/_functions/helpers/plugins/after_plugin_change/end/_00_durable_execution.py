from helpers.extension import Extension


class DurableRestoreImports(Extension):
    def execute(self, data):
        from usr.plugins.durable_execution.helpers.bridge import restore_modules
        restore_modules()
