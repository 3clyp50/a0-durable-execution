from helpers.extension import Extension


class Durable_Agent_process_tools(Extension):
    async def execute(self, data):
        from usr.plugins.durable_execution.helpers.bridge import dispatch_async
        await dispatch_async('agent.py:Agent.process_tools', data)
