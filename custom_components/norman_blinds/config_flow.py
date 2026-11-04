"""Config flow for the Norman Blinds integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from aiohttp import ClientError
import asyncio

from .api import NormanBlindsApiClient, NormanBlindsApiError, NormanBlindsAuthError
from .const import (
    ALLOWED_POSITIONS,
    CONF_FAVORITE_POSITION,
    DEFAULT_FAVORITE_POSITION,
    DEFAULT_PASSWORD,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    }
)


class NormanBlindsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Norman Blinds."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""

        return NormanBlindsOptionsFlow()

    async def _async_validate(self, host: str, password: str) -> str | None:
        """Log in and fetch state; return an error key, or None on success."""

        client = NormanBlindsApiClient(async_get_clientsession(self.hass), host, password)
        try:
            await client.async_get_combined_state()
        except NormanBlindsAuthError:
            return "invalid_auth"
        except (NormanBlindsApiError, ClientError, asyncio.TimeoutError):
            return "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            return "unknown"
        return None

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            # Simple validation: authenticate and fetch current state.
            error = await self._async_validate(
                user_input[CONF_HOST], user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD)
            )
            if error:
                errors["base"] = error
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

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start reauth after the hub rejected the login."""

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the password again and check it against the hub."""

        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await self._async_validate(entry.data[CONF_HOST], user_input[CONF_PASSWORD])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PASSWORD,
                        default=entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
                    ): str
                }
            ),
            description_placeholders={"host": entry.data[CONF_HOST]},
            errors=errors,
        )


class NormanBlindsOptionsFlow(OptionsFlow):
    """Options: the position the Favorite buttons move a room to."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the favourite position."""

        if user_input is not None:
            return self.async_create_entry(
                data={CONF_FAVORITE_POSITION: int(user_input[CONF_FAVORITE_POSITION])}
            )

        current = self.config_entry.options.get(
            CONF_FAVORITE_POSITION, DEFAULT_FAVORITE_POSITION
        )
        # Offer the hub's supported positions, labelled in HA's % open.
        options = [
            SelectOptionDict(value=str(pos), label=f"{100 - pos}% open")
            for pos in sorted(ALLOWED_POSITIONS, reverse=True)
        ]
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_FAVORITE_POSITION, default=str(current)): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                    )
                }
            ),
        )
