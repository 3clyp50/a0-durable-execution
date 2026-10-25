from helpers.extension import Extension


class Durable_AgentContext_communicate(Extension):
    def execute(self, data):
        from usr.plugins.durable_execution.helpers.bridge import dispatch
        dispatch('agent.py:AgentContext.communicate', data)
