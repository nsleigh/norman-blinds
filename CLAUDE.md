# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (`custom_components/norman_blinds`) for Norman Blinds/Shutters hubs, built by reverse-engineering the hub's local HTTP API (there is no official API). It talks directly to the hub over the local network (`local_polling` IoT class) — no cloud dependency.

There is no test suite, linter config, or build step in this repo. It's installed into a Home Assistant instance (manually or eventually via HACS) rather than run/tested standalone. Validate changes by reading the code carefully and cross-checking against the API shapes documented in README.md; there's no `pytest`/`tox` to run.

## Norman hub API

The hub's undocumented HTTP API is fully documented in README.md, including request/response payloads for `GatewayLogin`, `GatewayLogout`, `AdminLogin`/`AdminLogout`, `RemoteControl` (window/room/preset commands), `getRoomInfo`, and `getWindowInfo`. Read it before touching `api.py` — it's the closest thing to a spec this integration has.

Key quirks of the hub API that shape the code:
- Auth is cookie-session based via `GatewayLogin` with a fixed password (`123456789` unless changed) — not a real credential.
- The hub sometimes returns HTTP 401 on session expiry, but other times returns HTTP 200 with `{"error": -2}` in the body instead. `api.py`'s `_request` handles both by forcing re-login and retrying once.
- Blind/room position values are inverted and quantized: the wire protocol's `position`/`action` is 0 (open) to 100 (closed) in fixed steps (`ALLOWED_POSITIONS` in const.py: 100, 81, 65, 50, 37, 25, 12, 0). Home Assistant's `CoverEntity` convention is the opposite (0 = closed, 100 = open), so the entity layer converts and snaps to the nearest allowed step (`_normalize_position` in cover.py).
- Room-level "preset" commands (`view`/`privacy`/`favorite`) map to distinct wire command types (`fullopen`/`fullclose`/`Favorite`) — see `ROOM_PRESETS` in const.py — and are separate from plain position commands (`type: "level"` for rooms, `type: "window"` for individual blinds).

## Architecture

Standard HA integration layering — `__init__.py` wires these together at `async_setup_entry`:

- **`api.py`** — `NormanBlindsApiClient`: thin async HTTP client, owns login/session/retry logic. All hub communication goes through here; nothing else should call `aiohttp` directly. `async_get_combined_state()` fetches rooms + windows and merges each window with its owning room (matched by room ID across several possible key names — the hub's field naming isn't fully consistent between endpoints) plus a `suggested_area` for HA's area assignment.
- **`coordinator.py`** — `NormanBlindsDataUpdateCoordinator` (HA `DataUpdateCoordinator`), polls `async_get_combined_state()` every `DEFAULT_SCAN_INTERVAL` (30s) and translates API exceptions into HA's `ConfigEntryAuthFailed`/`UpdateFailed`.
- **`cover.py`** — two entity classes: `NormanBlindsCover` (one per physical blind/window) and `NormanBlindsRoomCover` (one per room, aggregating/averaging its member blinds' positions and issuing room-level commands). Both do optimistic local state update immediately after sending a command, then schedule `_delayed_refresh()` (sleeps `DEFAULT_REFRESH_DELAY` before polling) since the hub doesn't push state changes.
- **`sensor.py`** — diagnostic sensors per window (battery, RSSI, temperature, position, solar, USB power, firmware version, model), generated from `WINDOW_SENSORS` descriptions; skips creating a sensor if the underlying field is absent from that window's payload.
- **`button.py`** — one button per room per preset (`view`/`privacy`/`favorite`); derives rooms from `getRoomInfo` when available, otherwise reconstructs a room list from window payloads (hub responses aren't always internally consistent about which rooms exist).
- **`config_flow.py`** — single-step config flow (host + password) that validates by calling `async_get_combined_state()` before creating the entry.

**Entity lifecycle pattern** (repeated in cover.py, sensor.py, button.py): each platform's `async_setup_entry` builds entities from the coordinator's current data, then registers a coordinator listener that rebuilds the entity list on every update and adds only entities whose `unique_id` hasn't been seen yet — this is how newly-detected blinds/rooms get added to HA without a restart.

**Device identity**: all entities for a given window share device identifier `(DOMAIN, f"window_{window_id}")`; the hub itself is `(DOMAIN, "hub")`, used as the `via_device` for windows and as the device for room-level covers/buttons. `__init__.py`'s `async_remove_config_entry_device` only allows removing devices that aren't in the hub's last-known set of windows — this stops users from deleting still-live devices from the UI while allowing cleanup of blinds physically removed from the gateway.

## Versioning

Bump `version` in `manifest.json` when making a release-worthy change (see recent commit history for the pattern, e.g. `6a093b2 Bump version to 0.3.0`).
