from helpers.extension import Extension


class Durable_AgentContext_kill_process(Extension):
    def execute(self, data):
        from usr.plugins.durable_execution.helpers.bridge import dispatch
        dispatch('agent.py:AgentContext.kill_process', data)
