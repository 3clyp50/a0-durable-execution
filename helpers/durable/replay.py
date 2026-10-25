"""Explicit source-pinned replay audits; drift requires a new review."""

AUDITED_HOOKS = {
    ('BrowserModelCleanup', '55ad6654cf45adc77f741cfa7e47e0562fa5a3bcc6768f7527af95e00d0a2f6d'),
    ('WaitingForInputMsg', '6c783e2e86031a26d33ed50204fbeb28004e1813618f9eb5851e98f2a69712d5'),
    ('MaskReasoningStreamEnd', '55eae68432367201f292a4bdd13527519d763f45b2247a20cb09901619d3c872'),
    ('MaskResponseStreamEnd', '5f7fa3c82c5d468fd680127251a50d3cc189153c55e1c10d038635619eab035d'),
    ('LogFromStream', '658d4be2120b4914872941d9e8c17141f9a7f852100d8a4114f34695a2adc9ed'),
    ('ReplaceLastToolOutput', 'c309d8f1eb104a01dece04e4f63026881abb49bf220387ae46f4598ce2e847ea'),
    ('UnmaskToolSecrets', '9b8e435be74e6a6d41718fa1de7fe0ff43f5a929da7f0d98e46521f6a8965941'),
    ('BlockParallelRecursion', '5eff30bc40ccee527217a79ec08403b138440b64c62f48294725eb2875a46959'),
    ('MaskToolSecrets', 'c37ca95db6bc9c62af50a69a430f111a48d507b49b66a53a80a9eab513a12115'),
    ('EnforceToolPolicy', '814c5974e8f0d647d75974cbc7479ad8b0edf67783f45ba5c6c80726f107164f'),
}

AUDITED_TOOLS = {
    ('DurablePlan', '239254074f6a7eb1c887ad95b8c14abd2de41e4e1d0fa7889adb0cd6422cccc8'),
    ('ResponseTool', '805ca9cedf2465f5fb42b2255fa04c385c7ef7acf2df0aea32455041ce451422'),
}

# Exact built-in workflow sources are pinned after adapter verification.
AUDITED_WORKFLOWS = {
    ('Delegation', '3faf3881335236a6fb87a943d5727fb347b7a28b4a73a58531095bc431ff0ebb'),
    ('ParallelTool', 'a28560a3bd45cbdc5a62250f8d6c2d5a90b0930485428c781f5d0161927b02bc'),
}

# Constructor recovery may only repeat these local projection/config readers.
AUDITED_INIT_HOOKS = {
    ('InitialMessage', '6f481bc1336f0ff03ba63813a4acc12658322ca4576ca59ce26d9af3c618c7df'),
    ('LoadProfileSettings', 'bcdb72dd58bf73787ec480de4c9044769b78d563d156dde91988d57e6be09589'),
}

AUDITED_INITIAL_HISTORY_HOOKS = {
    ('MaskHistoryContent', 'eb613a29492b4e9fa9b238de709d3fcee747b7ab6dee78e7871b0371dafb3f41'),
    ('LogPlainResponses', 'af2df482007afdde59577b962b360358e64749f25faf7d93effc7a6fcbcbb3d9'),
}

# These continuations are safe only with the shared detached broker enabled.
BROKER_HOOKS = {
    ('tool_execute_before', 'InfectionAwaitCheck', '512b014e0a35414b13099dc4054ce087be31a4a5a28a59c616de7468a8486dd8'),
    ('monologue_end', 'MemorizeMemories', '01adba19fa635a81c01021f173d14defcb52177c476c3fd77740904ac5625229'),
    ('monologue_end', 'MemorizeSolutions', 'a2886411446bf1dd9c5ed09aaaf3e42169320b00f51c2edcd066f623afa1ced0'),
    ('message_loop_end', 'OrganizeHistory', '904bdecf80b59ee9263449b4ab24f62b922792cd76674970f11d11a757440fcf'),
}
