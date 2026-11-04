# Norman Gen 1 hub — local HTTP API

This is a reverse-engineered reference for the local API of the Norman Gen 1 hub (the hub driven by the iOS **Norman remote control** app). Norman doesn't publish an official API.

Each fact is tagged with where it comes from:

| Tag | Source |
|-----|--------|
| **[observed]** | Seen on this repo's hub (`NORMANHUB_9DDD2D`, 2 rooms, 6 blinds), or used by this integration in production. |
| **[ref]** | Taken from the gen1 client in [Herbertmt978/Norman-HA-Integration](https://github.com/Herbertmt978/Norman-HA-Integration), which talks to the same hub. |
| **[inferred]** | Worked out from the data here, but not yet confirmed by a test. |
| **[app]** | Seen in a capture of the official iOS app's traffic to this hub (2026-11-04, via an HTTP proxy). |

The Gen 2 **ShadeAuto** hub (`com.norman.SmartShutter`) uses a different protocol on port 10123. This document doesn't cover it.

---

## Contents

- [The hub](#the-hub)
- [Protocol basics](#protocol-basics)
- [Session lifecycle](#session-lifecycle)
- [Endpoints](#endpoints)
  - [GatewayLogin](#gatewaylogin)
  - [GatewayLogout](#gatewaylogout)
  - [AdminLogin / AdminLogout](#adminlogin--adminlogout)
  - [getRoomInfo](#getroominfo)
  - [getWindowInfo](#getwindowinfo)
  - [getSceneInfo](#getsceneinfo)
  - [getScheduleInfo](#getscheduleinfo)
  - [UploadGPS](#uploadgps)
  - [RemoteControl](#remotecontrol)
- [Data model: rooms, groups, levels](#data-model-rooms-groups-levels)
- [Positions](#positions)
- [Room styles](#room-styles)
- [Error codes and failure modes](#error-codes-and-failure-modes)
- [Hub behaviour and quirks](#hub-behaviour-and-quirks)
- [Open questions](#open-questions)

---

## The hub

| | |
|---|---|
| Hardware | Linux 4.1.15, armv7l, kernel built 26 Jun 2017 (from the SNMP `sysDescr`). **[observed]** |
| Web server | Cherokee 1.2.98. The web root only serves the default Cherokee test page. **[observed]** |
| API base | `http://<hub>/cgi-bin/cgi/<Endpoint>` on port 80. **[observed]** |
| Discovery | mDNS `_http._tcp.local`, instance `NORMANHUB_<last 6 MAC hex digits>`, port 80. **[observed]** |
| Other open ports | TCP 53 (doesn't answer DNS), 111 (rpcbind, nothing registered), 199 (SMUX), and UDP 161 (SNMP, `public` community, `system` view only). None of these is part of the API. **[observed]** |
| Official app | iOS **Norman remote control**, bundle `com.norman.SmartShutterControlPlus`, v2.11.21, last updated 2023-01-03. There was never an Android build. It sends `User-Agent: SmartShutterControl/103 CFNetwork/… Darwin/…`. **[observed] [app]** |

The integration only needs TCP 80.

---

## Protocol basics

- **Method:** every endpoint is `POST`. **[observed]**
- **Body:** JSON, `Content-Type: application/json`. Endpoints that take no parameters get `{}`. **[observed]**
- **Response:** JSON, but don't rely on the `Content-Type` header. Parse the body regardless (`response.json(content_type=None)`). **[observed]**
- **Auth:** a session cookie named `Session`, issued by `GatewayLogin` and sent back on every later request. **[observed] [ref]**
- **User-Agent:** the reference client sends `SmartShutterControl/103 …`, which mirrors the app's bundle name. The hub works without it. **[ref]**
- **Identifiers:** room and window IDs are integers. The hub accepts them as numbers or strings in `RemoteControl`. **[observed]**

---

## Session lifecycle

```
GatewayLogin  ──►  getRoomInfo / getWindowInfo / RemoteControl …  ──►  (AdminLogout) GatewayLogout
```

There are two ways to manage the session:

- **This integration** keeps one session open. It logs in again only when the hub reports that the session has expired. **[observed]**
- **The reference client** wraps every operation as login → request(s) → logout, behind a lock, so that no two requests ever overlap at the hub. It logs out with `AdminLogout` followed by `GatewayLogout`. **[ref]**

- **The official app** logs in once when it opens and uses that session for everything. It didn't log out at any point in the capture, and it never calls `AdminLogin`. **[app]**

The session cookie is `Session=<number>`. Later responses echo it back in a lowercase `session: Session=…` header rather than `Set-Cookie`. **[app]**

The official app and an integration can hold separate sessions at the same time. **[ref]**

The hub can drop sessions without warning. This happens at fixed times; see [Hub behaviour](#hub-behaviour-and-quirks).

---

## Endpoints

### GatewayLogin

Creates a session.

```http
POST /cgi-bin/cgi/GatewayLogin
Content-Type: application/json

{ "password": "123456789", "app_version": "2.11.21" }
```

| Field | Notes |
|-------|-------|
| `password` | `123456789` on every hub seen so far. It doesn't appear to be configurable. **[observed]** |
| `app_version` | The hub accepts several values (for example `2.10.0`, `2.11`, `2.11.21`). `2.11.21` matches the current app. **[observed]** |

**Success** (`200`, with no `errorCode` or `errorCode: 0`):

```json
{
    "initiated": "0",
    "hubName": "home",
    "latitude": "nn.nnn",
    "longitude": "nn.nnn",
    "timezone": "1.000000",
    "hubId": "MBAHUB_FAE224",
    "swVer": "2.0.7.15(1.0.2)",
    "needUpdate": "0",
    "admin": 0,
    "sunset": 1680810481,
    "sunrise": 1680762786,
    "leave": 0,
    "version_control": 0
}
```

| Field | Meaning |
|-------|---------|
| `hubName`, `hubId`, `swVer` | Hub identity and firmware version. The integration uses these for the HA device. **[observed]** |
| `latitude`, `longitude`, `timezone` | Location settings from the app. These drive the hub's own sunrise/sunset schedules. **[inferred]** |
| `sunrise`, `sunset` | Unix timestamps for today. **[observed]** |
| `needUpdate` | `"1"` when a hub firmware update is available. **[inferred]** |
| `initiated`, `admin`, `leave`, `version_control` | Meaning not known. |

**Failure:**

| Response | Meaning | How to handle it |
|----------|---------|------------------|
| HTTP `401` or `403` | Credentials rejected. | Treat as an auth failure. **[observed]** |
| HTTP `500` | The hub is busy with a scheduled job, or its CGI service is stuck. | Retry. The reference client sends a logout first to clear the dead session. **[observed] [ref]** |
| `200` + `errorCode: -15` | The hub is busy (scheduled job). | Retry. It clears by itself. **[observed]** |
| `200` + `errorCode: -12` | The hub is stuck. Seen on 2026-10-18; a reload didn't clear it. | Power-cycle the hub. **[observed]** |
| `200` + `errorCode: -13` | Password or session rejected. | Treat as an auth failure. **[ref]** |

### GatewayLogout

Ends the session.

```http
POST /cgi-bin/cgi/GatewayLogout
{}
```

```json
{ "status": "Success" }
```

### AdminLogin / AdminLogout

These need a gateway session first. `AdminLogin` appears to raise the session's privileges. Nothing the integration does requires it, although `getRoomInfo` was once noted as possibly needing it. The reference client never calls `AdminLogin`, but it does call `AdminLogout` before `GatewayLogout`. **[observed] [ref]**

```http
POST /cgi-bin/cgi/AdminLogin      {}
POST /cgi-bin/cgi/AdminLogout     {}
```

```json
{ "status": "Success" }
```

### getRoomInfo

Lists the rooms and each room's group names. Needs a session.

```http
POST /cgi-bin/cgi/getRoomInfo
{}
```

```json
{
    "totalRooms": 2,
    "rooms": [
        {
            "groupname": ["Left", "Middle", "Right", "All", "group5"],
            "Id": 17488,
            "Name": "Study",
            "Color": 11,
            "Style": 13,
            "Sort": 0
        },
        {
            "groupname": ["Left", "Middle", "Right", "All", "group5"],
            "Id": 6385,
            "Name": "Living Room",
            "Color": 8,
            "Style": 1,
            "Sort": 1
        }
    ]
}
```

| Field | Meaning |
|-------|---------|
| `Id` | Room ID. It's the target for room commands. |
| `Name` | Room name, set in the app. |
| `groupname` | Five group slots, indexed 0–4. Slots 0–2 are named by the user, slot 3 is "All", and slot 4 is spare. See [Data model](#data-model-rooms-groups-levels). **[observed]** |
| `Style` | The room's covering type. It changes how positions map to open and closed; see [Room styles](#room-styles). **[ref]** |
| `Color`, `Sort` | The room's colour and display order in the app. |

### getWindowInfo

Lists every blind and its current state. Needs a session. In the real response, records may contain extra keys and some values may be strings (for example `battery`).

```http
POST /cgi-bin/cgi/getWindowInfo
{}
```

A single record (`Id 3cce`, Study):

```json
{
    "Id": 15566,
    "Name": "Id 3cce",
    "Level": 0,
    "Sort": 0,
    "RId": 17488,
    "roomId": 17488,
    "scenes": [{ "Id": 0, "Position": 0, "Angle": 0 }],
    "groupId": 10,
    "level": [0, 1, 0, 1, 0],
    "levelsort": [0, 1, 0, 1, 0],
    "battery": "100",
    "position": 37,
    "angle": 0,
    "model": 1,
    "Rssi": 65,
    "temp": 21,
    "ver": "0.6.8",
    "solar": 65535,
    "usb": 0,
    "speed": 0,
    "model_detail": 0
}
```

The wrapper is `{ "totalWindow": 6, "windows": [ … ] }`.

| Field | Meaning |
|-------|---------|
| `Id` | Window (blind) ID. It's the target for `type: "window"` commands. |
| `Name` | Name set in the app. The default is `Id <last 4 hex digits of the motor ID>`. |
| `RId`, `roomId` | The ID of the blind's room. Both carry the same value. |
| `Level` | A single number (`0` for every blind here). The reference client sends it as `Lid` in `level` commands, but on this hub `Lid` turned out to be a `groupname` slot, so `Lid: 0` moves only the Left group. Its meaning is unknown; it may number the panel tier on stacked shutters. **[observed] [ref]** |
| `level` | A 5-element array: which of the room's `groupname` slots this blind belongs to. Confirmed by test: `Lid` 0, 1 and 2 each moved exactly the blinds with that slot set. **[observed]** |
| `levelsort` | A 5-element array: the blind's position within each group it belongs to. **[inferred]** |
| `groupId` | `level` packed into a bitmask: bit *n* is set when `level[n] == 1`. **[inferred]** |
| `position` | Current position, `0`–`100`, on the hub's scale. See [Positions](#positions). |
| `angle` | Louver angle. Always `0` on these blinds. |
| `battery` | Battery percentage, sent as a string. |
| `Rssi` | Signal strength. Some blinds don't report this field. **[observed]** |
| `temp` | Motor temperature, °C. |
| `solar` | Solar charge reading. `65535` (`0xFFFF`) means no reading. **[observed]** |
| `usb` | USB charge reading (`0` when not charging). |
| `ver` | Motor firmware version. |
| `model`, `model_detail` | Motor model. `model` is sent back in position commands. |
| `scenes` | Per-blind scene positions (`Position`, `Angle`). |
| `speed`, `Sort` | Motor speed, and display order in the app. |

#### Rooms on this hub

| Blind | Room | `Level` | `level` | `groupId` | `levelsort` | Group |
|-------|------|---------|---------|-----------|-------------|-------|
| `b8b7` (47287) | Living Room | 0 | `[1,0,0,1,0]` | 9 | `[1,0,0,2,0]` | Left + All |
| `3182` (12674) | Living Room | 0 | `[0,1,0,1,0]` | 10 | `[0,1,0,1,0]` | Middle + All |
| `bc0f` (48143) | Living Room | 0 | `[0,0,1,1,0]` | 12 | `[0,0,1,3,0]` | Right + All |
| `83ee` (33774) | Study | 0 | `[1,0,0,1,0]` | 9 | `[1,0,0,2,0]` | Left + All |
| `3cce` (15566) | Study | 0 | `[0,1,0,1,0]` | 10 | `[0,1,0,1,0]` | Middle + All |
| `ab36` (43830) | Study | 0 | `[0,0,1,1,0]` | 12 | `[0,0,1,3,0]` | Right + All |

### getSceneInfo

Lists scenes. Needs a session. The official app calls it twice at startup, with `Type` `2` and then `1`. **[app]**

```http
POST /cgi-bin/cgi/getSceneInfo
{ "Type": 2 }
```

```json
{ "totalScences": 0, "Scenes": [] }
```

```http
POST /cgi-bin/cgi/getSceneInfo
{ "Type": 1 }
```

```json
{ "totalMScences": 0, "MScenes": [] }
```

The keys are spelled `Scences` by the hub. What distinguishes `Type: 1` (`MScenes`) from `Type: 2` (`Scenes`) is unknown, and this hub has none of either, so the record format is unknown too.

### getScheduleInfo

Lists the hub's schedules. Needs a session. **[app]**

```http
POST /cgi-bin/cgi/getScheduleInfo
{}
```

```json
{ "totalschedule": 0, "schedule": [] }
```

This hub has no schedules, so the record format is unknown.

### UploadGPS

**Writes** the hub's location. Needs a session. The official app sends this every time it opens, with the phone's location. The hub uses it for the `latitude`, `longitude`, `timezone`, `sunrise` and `sunset` values in the `GatewayLogin` response. **[app] [inferred]**

```http
POST /cgi-bin/cgi/UploadGPS
{ "latitude": nn.nnn, "longitude": nn.nnn, "timezone": 0.0 }
```

```json
{ "action": "set", "status": "Success" }
```

This request sends numbers, while `GatewayLogin` returns the same values as strings.

### RemoteControl

Moves blinds. Needs a session. The response is fire-and-forget: a `200` with no `errorCode` (or `errorCode: 0`) means the hub accepted the command, not that the blind has finished moving. A nonzero `errorCode` means the hub rejected the command. **[observed] [ref]**

```http
POST /cgi-bin/cgi/RemoteControl
```

#### Move one blind

```json
{ "type": "window", "id": 15566, "action": 37, "model": 1 }
```

| Field | Value |
|-------|-------|
| `type` | `"window"` |
| `id` | The window `Id`. |
| `action` | Target position, on the hub's scale. See [Positions](#positions). |
| `model` | The window's `model` value (`1`). |

**[observed]** This integration uses this command for each blind's own cover entity. The reference client doesn't use it.

#### Move a room (position)

```json
{ "type": "level", "Lid": 3, "id": 17488, "action": 50, "model": 1 }
```

| Field | Value |
|-------|-------|
| `type` | `"level"` |
| `Lid` | The `groupname` slot to move: `0` Left, `1` Middle, `2` Right, `3` All. **[observed]** |
| `id` | The room `Id`. |
| `action` | Target position, on the hub's scale. |
| `model` | The blinds' `model` value (`1`). |

Tested on the Living Room on 2026-11-04. The Study never moved, so `id` scopes the command to the room. **[observed]**

| `Lid` | Moved | Hub's stored `position` |
|-------|-------|-------------------------|
| `0` | Left only | Updated |
| `1` | Middle only | Updated |
| `2` | Right only | Updated |
| `3` | Whole room (All) | Updated |
| `9` | Whole room | **Not updated** |

Use **`Lid: 3`** for a whole room. `Lid: 9` (sent by this integration up to v0.3.7) moves the blinds, but the hub doesn't record the new positions, so `getWindowInfo` keeps reporting the old ones. `Lid: <window Level>` (the reference client's approach) is `0` here, which moves only the Left group.

#### Room presets

```json
{ "type": "fullopen",  "action": 2, "id": 17488 }
{ "type": "fullclose", "action": 2, "id": 17488 }
{ "type": "Favorite",  "action": 2, "id": 17488 }
```

| `type` | App label | This integration's button |
|--------|-----------|---------------------------|
| `fullopen` | View | `button.<room>_view` |
| `fullclose` | Privacy | `button.<room>_privacy` |
| `Favorite` | Favourite (capital F) | `button.<room>_favorite`, but from v0.3.9 it sends a `level` command with `Lid: 3` to the **Favorite position** option (default `65`) instead, because the hub doesn't record `Favorite` |

The hub replies `{"Favorite": "ok"}` (keyed by the command type) rather than `{"remote": "ok"}`. **[observed]**

`action` **must be `2`**. With `action: 1`, every room moved, whatever `id` was sent. The official app and the reference client also send `action: 2` for `fullopen` and `fullclose`. **[observed] [app] [ref]**

The official app sends `Favorite` **without** an `action` field: `{"type": "Favorite", "id": <room id>}`. With `action: 2` it works the same. The app never reads or sends the favourite position itself, so it isn't exposed by the API; it's presumably stored in the motors or the hub. **[app] [observed]**

---

## Data model: rooms, groups, levels

```
Hub
 └─ Room (getRoomInfo.Id, Style, groupname[0..4])
     └─ Blind (getWindowInfo.Id, RId → room)
          ├─ level[0..4]     membership in groupname slots
          ├─ groupId         same membership as a bitmask
          ├─ levelsort[0..4] order within each group
          └─ Level           0 here; meaning unknown (not the Lid to send)
```

Confirmed by the `Lid` tests on the Living Room (2026-11-04): **[observed]**

- Each room has five group slots: `Left`, `Middle`, `Right`, `All`, `group5`.
- Every blind is in exactly one of Left, Middle or Right, and also in **All** (slot 3).
- The slot numbers are what `Lid` selects in `level` commands (`0` Left … `3` All).

Inferred from the 6 blinds on this hub, not tested: **[inferred]**

- `groupId` encodes the same membership as a bitmask: `9` = `0b01001` (Left + All), `10` = `0b01010` (Middle + All), `12` = `0b01100` (Right + All).
- `levelsort` gives each blind's order within a group. In its own group (Left, Middle or Right) every blind is `1`. In All (slot 3) the order is Middle `1`, Left `2`, Right `3` in both rooms, which isn't left-to-right. It may be the order the blinds were paired in.
- `Level` is `0` everywhere here. On hubs with stacked shutters it probably numbers the panel tier, but that's unconfirmed.

---

## Positions

The wire `position` / `action` is on the hub's own scale, `0`–`100`. Only these values are reliable, and other values behave like `0`:

| Value | On this hub (Living Room, checked 2026-11-04) |
|-------|-------------------------------|
| `100` | Fully closed (up) |
| `81` | |
| `65` | Favourite. The hub's own `Favorite` moves the blinds here (35% open in HA). |
| `50` | |
| `37` | Open. This integration's "open" target (63% open in HA). |
| `25` | |
| `12` | |
| `0` | Nearly fully closed (down) |

**[observed]** Both ends of the travel are closed and the louvers are open around the middle. That's the behaviour of tilt shutters (see [Room styles](#room-styles)). This integration inverts and snaps values for HA (`ALLOWED_POSITIONS`, `_normalize_position`), and sends `37` for "open".

---

## Room styles

The reference client uses `getRoomInfo.Style` to decide how positions map to open and closed: **[ref]**

| `Style` | Behaviour |
|---------|-----------|
| `2`, `3`, `13` | **Tilt-open.** The middle of the travel (`37`) is visually open, and both ends (`0` and `100`) are closed. |
| `13` | Also **reversed close**: the preferred close is `100` rather than `0`. |
| anything else (e.g. `1`) | Linear: `100` is open and `0` is closed. |

On this hub, the Study is `Style 13` and the Living Room is `Style 1`.

---

## Error codes and failure modes

| Signal | Where | Meaning | How to handle it |
|--------|-------|---------|------------------|
| HTTP `401` | any request | Session expired. | Log in again, then retry once. **[observed]** |
| HTTP `401`/`403` | `GatewayLogin` | Credentials rejected. | Auth failure. **[observed]** |
| HTTP `500` | `GatewayLogin` | Busy (scheduled job) or stuck CGI. | Retry up to 3 times, 5 s apart. If it persists, the hub needs a restart. **[observed] [ref]** |
| `{"error": -2}` with HTTP `200` | data endpoints | Session expired, reported without a 401. | Force a new login and retry once. **[observed]** |
| `errorCode: -12` | `GatewayLogin` | Stuck. A reload doesn't clear it. | Power-cycle the hub. **[observed]** |
| `errorCode: -13` | any request | Password or session rejected. | On login, treat as an auth failure. On a session request, log in again. **[ref]** |
| `errorCode: -15` | `GatewayLogin` | Busy (scheduled job). | Transient: retry. **[observed]** |
| other nonzero `errorCode` | `RemoteControl` | Command rejected. | Report the failure. **[ref]** |

Note that the error field has two different names. Data endpoints report expired sessions as **`error`**, while login and control use **`errorCode`**. **[observed]**

Up to v0.3.7, this integration treated only `-15` as transient on login and every other code as an auth failure. v0.3.8 changes that: only `-13` is an auth failure, and every other nonzero login code is treated as transient.

---

## Hub behaviour and quirks

- **Scheduled session drops.** The hub drops sessions and refuses logins (HTTP 500, or `-15`) at **02:10 and 02:24 every night**, and at **:08 past the hour from 05:00 to 09:00**. Each drop lasts about 30–40 s. The hub doesn't reboot during these windows: its uptime keeps counting, and it stays on the network. Don't schedule commands at these times. **[observed]**
- **The CGI can lock up.** Cherokee can still be running a failed CGI request after it has sent the response headers. Read the whole response body before starting the next request, so that requests never overlap. **[ref]**
- **Rapid commands.** The reference client spaces multi-command room moves 1 s apart, for reliability across firmware variants. **[ref]**
- **The scheduled drops aren't schedules.** This hub has no schedules and no scenes (`getScheduleInfo` and `getSceneInfo` return empty lists), so the 02:10, 02:24 and morning :08 login failures come from the firmware itself. **[app]**
- **No push.** The hub never pushes state changes. After sending a command, wait about 5 s and then poll `getWindowInfo`. **[observed]**
- **Positions are the last command, not a measurement.** The blinds don't report where they are. `getWindowInfo.position` is whatever the hub last commanded, and only for commands it records. Moving a blind any other way, such as by hand, leaves the reported position wrong. **[observed]**

  | Command | Hub records the new position? |
  |---------|-------------------------------|
  | `level` with `Lid` 0–3 | Yes **[observed]** |
  | `level` with `Lid: 9` | No **[observed]** |
  | `fullopen` (View) | Yes **[observed]**: `cover.study` changed to open 19 s after View was pressed |
  | `fullclose` (Privacy) | Yes **[observed]**: Living Room stored 50 → 100 |
  | `Favorite` | **No** **[observed]**: blinds moved to favourite, stored positions stayed at 100 |
  | `window` | Not checked |

- **Resyncing wrong positions.** If the reported positions don't match the blinds, send the room's real position as a `level` command with `Lid: 3` (for example `100` if the blinds are closed). The blinds don't move if they're already there, and the hub records the position. **[observed]**
- **Stale readings.** `solar` is `65535` when there's no reading. Some blinds don't report `Rssi` at all. **[observed]**

---

## Open questions

1. **Resolved (2026-11-04):** `Lid` in `type: "level"` is the `groupname` slot (`0` Left, `1` Middle, `2` Right, `3` All). See [Move a room](#move-a-room-position).
2. **Per-group entities.** Because `Lid` 0–2 move a single group, Left, Middle and Right could each become their own entity, without needing `type: "window"`.
3. **What do `errorCode: -12` and `-13` mean exactly?** The app's error strings would answer this, but the app is iOS-only and App Store builds are encrypted, so they can't be read from the app itself. Capturing the app's plain-HTTP traffic is the way forward.
4. **Endpoints that aren't documented yet.** The 2026-11-04 capture found `getSceneInfo`, `getScheduleInfo` and `UploadGPS`, and showed the drops aren't caused by schedules. Still not captured: creating a schedule or scene (the record formats), and the hub settings and firmware screens.
5. **The meaning of `initiated`, `admin`, `leave` and `version_control`** in the login response.
6. **Does `type: "window"` record positions?** `fullclose` does and `Favorite` doesn't (tested 2026-11-04). Check by sending it and comparing `getWindowInfo.position` before and after.
7. **Where is the favourite position stored?** Not in anything the API returns. The hub doesn't record it after a `Favorite` command, nothing in `getRoomInfo` or `getWindowInfo` holds it (`scenes[].Position` is `0` everywhere), and the official app never reads it either. It's presumably stored in the motors. An integration has to be told the position (this one has a **Favorite position** option). **[app] [observed]**
