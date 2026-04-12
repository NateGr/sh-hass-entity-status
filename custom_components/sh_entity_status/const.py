DOMAIN = "sh_entity_status"
# Human-readable brand name — change this single constant to rebrand across all Python code.
# NOTE: JSON files (manifest.json, strings.json, translations/*.json) contain the name inline
# and must be updated separately when changing the brand name.
INTEGRATION_NAME = "SmartHass Entity Status"

# Slug prefix stamped onto every sensor's entity_id to group all integration
# entities together in the HA registry (e.g. sensor.sh_entity_status_unavailable_count).
# To rebrand: change this string — but note existing deployments will need their
# entities removed and re-added (or manually renamed in HA) after any change.
# To use bare names with no prefix: set ENTITY_ID_PREFIX = ""
ENTITY_ID_PREFIX = "sh_entity_status"
CONF_IGNORE_LABEL = "ignore_label"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_POLL_INTERVAL = "poll_interval"
DEFAULT_IGNORE_LABEL = "ignore_unavailable"
DEFAULT_REFRESH_INTERVAL = 60  # minutes
DEFAULT_POLL_INTERVAL = 30  # seconds
