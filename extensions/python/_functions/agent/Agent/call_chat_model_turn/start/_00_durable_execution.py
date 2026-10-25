from helpers.extension import Extension


class Durable_Agent_call_chat_model_turn(Extension):
    async def execute(self, data):
        from usr.plugins.durable_execution.helpers.bridge import dispatch_async
        await dispatch_async('agent.py:Agent.call_chat_model_turn', data)
