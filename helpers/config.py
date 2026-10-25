"""Plugin settings; framework settings and dependencies remain untouched."""
from helpers.plugins import get_plugin_config


def values():
    config = get_plugin_config("durable_execution") or {}
    backend = config.get("backend", "local")
    if backend not in {"local", "postgres"}:
        raise ValueError("Durable Execution backend must be local or postgres")
    result = {"backend": backend}
    for key, default, maximum in (("retention_runs", 100, 10000), ("retention_days", 30, 3650)):
        value = config.get(key, default)
        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError(f"Invalid {key}")
        result[key] = value
    interactive = config.get("interactive_shells", True)
    known_hosts = config.get("ssh_known_hosts", "")
    if type(interactive) is not bool:
        raise ValueError("interactive_shells must be a boolean")
    if type(known_hosts) is not str or len(known_hosts) > 4096 or "\0" in known_hosts:
        raise ValueError("Invalid ssh_known_hosts path")
    result.update(interactive_shells=interactive, ssh_known_hosts=known_hosts)
    return result
