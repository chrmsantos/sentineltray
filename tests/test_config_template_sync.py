from __future__ import annotations

from pathlib import Path

from sentineltray.config_reconcile import apply_template_to_config_text


def test_apply_template_to_config_text_merges_values() -> None:
    template = """
window_title_regex: 'STRING_REQUIRED'
phrase_regex: 'STRING_REQUIRED'
log_level: 'INFO'
email:
  smtp_host: ''
  smtp_port: 587
"""
    legacy = """
window_title_regex: 'APP'
phrase_regex: 'ALERT'
log_level: 'DEBUG'
email:
  smtp_host: 'smtp.local'
  smtp_port: 2525
  smtp_username: 'user'
extra_key: 'keep'
"""

    merged = apply_template_to_config_text(legacy, template)

    assert "window_title_regex: 'APP'" in merged
    assert "phrase_regex: 'ALERT'" in merged
    assert "log_level: 'DEBUG'" in merged
    assert "smtp_host: 'smtp.local'" in merged
    assert "smtp_port: 2525" in merged
    assert "smtp_username: 'user'" in merged
    assert "extra_key: 'keep'" in merged


def test_apply_template_with_real_template_keeps_template_keys() -> None:
  template_text = """
log_level: 'INFO'
email_queue_file: 'logs/email_queue.json'
email_queue_max_items: 500
"""
  legacy = """
window_title_regex: 'APP'
phrase_regex: 'ALERT'
log_level: 'DEBUG'
email:
  smtp_host: 'smtp.local'
  smtp_port: 587
  smtp_username: ''
  smtp_password: ''
  from_address: 'alerts@example.com'
  to_addresses: ['ops@example.com']
  use_tls: true
  timeout_seconds: 10
  subject: 'SentinelTray'
  retry_attempts: 1
  retry_backoff_seconds: 1
  dry_run: true
"""

  merged = apply_template_to_config_text(legacy, template_text)

  assert "log_level: 'DEBUG'" in merged
  assert "email_queue_file" in merged
