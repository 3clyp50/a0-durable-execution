from helpers.extension import Extension


class DurableStartup(Extension):
    def execute(self, data):
        from usr.plugins.durable_execution.helpers.bridge import start
        start()
