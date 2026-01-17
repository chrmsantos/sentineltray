from __future__ import annotations

import logging
from dataclasses import dataclass

from playwright.sync_api import sync_playwright

from .config import WhatsappConfig

LOGGER = logging.getLogger(__name__)


class WhatsappSender:
    def send(self, message: str) -> None:
        raise NotImplementedError()


@dataclass
class WebWhatsappSender(WhatsappSender):
    config: WhatsappConfig

    def send(self, message: str) -> None:
        if self.config.dry_run:
            LOGGER.info("Dry run enabled, skipping send", extra={"category": "send"})
            return

        if not self.config.chat_target:
            raise ValueError("chat_target is required for web mode")

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=self.config.user_data_dir,
                headless=False,
            )
            page = context.new_page()
            page.goto("https://web.whatsapp.com", timeout=60_000)
            page.wait_for_selector("div[role='textbox']", timeout=60_000)

            search_box = page.locator("div[role='textbox']").first
            search_box.click()
            search_box.fill(self.config.chat_target)
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")

            message_box = page.locator("div[contenteditable='true']")
            message_box.last.click()
            message_box.last.type(message)
            page.keyboard.press("Enter")

            context.close()


def build_sender(config: WhatsappConfig) -> WhatsappSender:
    mode = config.mode.lower().strip()
    if mode == "web":
        return WebWhatsappSender(config=config)
    raise ValueError("Only web mode is supported")
