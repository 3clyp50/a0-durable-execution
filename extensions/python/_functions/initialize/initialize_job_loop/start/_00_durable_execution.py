from helpers.extension import Extension


class DurableRecovery(Extension):
    def execute(self, data):
        from usr.plugins.durable_execution.helpers.bridge import recover
        recover()
