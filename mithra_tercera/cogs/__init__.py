_enabled_cogs: list[str] = [
    "commands.search",
    "monitors.events",
]

ENABLED_COGS = [f"mithra_tercera.cogs.{x}" for x in _enabled_cogs]
