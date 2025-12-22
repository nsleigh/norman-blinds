"""Config flow for the Norman Blinds integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from aiohttp import ClientError
import asyncio

from .api import NormanBlindsApiClient, NormanBlindsApiError, NormanBlindsAuthError
from .const import DEFAULT_PASSWORD, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    }
)


class NormanBlindsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Norman Blinds."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = NormanBlindsApiClient(
                session,
                user_input[CONF_HOST],
                user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD),
            )

            try:
                # Simple validation: authenticate and fetch current state.
                await client.async_get_combined_state()
            except NormanBlindsAuthError:
                errors["base"] = "invalid_auth"
            except (NormanBlindsApiError, ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
