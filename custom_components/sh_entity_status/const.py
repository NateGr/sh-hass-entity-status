DOMAIN = "sh_entity_status"
# Human-readable brand name — change this single constant to rebrand across all Python code.
# NOTE: JSON files (manifest.json, strings.json, translations/*.json) contain the name inline
# and must be updated separately when changing the brand name.
INTEGRATION_NAME = "SmartHass Entity Status"
CONF_IGNORE_LABEL = "ignore_label"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_POLL_INTERVAL = "poll_interval"
DEFAULT_IGNORE_LABEL = "ignore_unavailable"
DEFAULT_REFRESH_INTERVAL = 60  # minutes
DEFAULT_POLL_INTERVAL = 30     # seconds
