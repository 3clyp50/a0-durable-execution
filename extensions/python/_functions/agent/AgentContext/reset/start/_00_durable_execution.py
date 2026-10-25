from helpers.extension import Extension


class Durable_AgentContext_reset(Extension):
    def execute(self, data):
        from usr.plugins.durable_execution.helpers.bridge import dispatch
        dispatch('agent.py:AgentContext.reset', data)
