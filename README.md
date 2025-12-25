# Norman Blinds

[![hacs_badge](https://img.shields.io/badge/HACS-Default-gren.svg)](https://github.com/custom-components/hacs)
![version](https://img.shields.io/github/v/release/nsleigh/norman_blinds)
![GitHub all releases](https://img.shields.io/github/downloads/nsleigh/norman_blinds/total)
![GitHub release (latest by SemVer)](https://img.shields.io/github/downloads/nsleigh/norman_blinds/latest/total)

![Norman Blinds Logo](images/logo@2x.png)

Reverse engineering the Norman Blinds hub protocol

## Linking hub to blinds 

Process to reset and detect blinds (this worked when other methods didn't)

- On hub press for 3 seconds in to user setting mode
- Press three times: Norman Hub factory reset.

Other

- Press for 3 seconds in to user setting mode
- Press one time: Search shutters.
- Press two times: Station mode switch to AP mode.

## API

### GatewayLogin

POST: http://NORMANHUB_9DDD2D.local/cgi-bin/cgi/GatewayLogin \

```json
{ "password":"123456789","app_version":"2.11.21" }
```

Various versions work e.g. 2.10.0, 2.11 \
Password doesn't appear to be set anywhere but has to be 123456789. \
Returns

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

### GatewayLogout

POST: http://NORMANHUB_9DDD2D.local/cgi-bin/cgi/GatewayLogout \
Returns

```json
{ "status": "Success" }
```

### AdminLogin

(Needs GatewayLogin first) \
POST: http://NORMANHUB_9DDD2D.local/cgi-bin/cgi/AdminLogin \
Returns

```json
{ "status": "Success" }
```

### AdminLogout

POST: http://NORMANHUB_9DDD2D.local/cgi-bin/cgi/AdminLogout \
Returns

```json
{ "status": "Success" }
```

### RemoteControl

POST: http://NORMANHUB_9DDD2D.local/cgi-bin/cgi/RemoteControl \

#### Blind control

```json
{ "type":"window", "id":<blind id>, "action":<position>, "model":1 }
```

|Position|Description|
|--------|-----------|
|100|Fully closed (up)|
|81||
|65|Nearly fully open|
|50||
|37|Like favourite|
|25||
|12||
|0|Nearly fully closed (down)|

Other position values seem to be the same as 0.

#### Room control

```json
{ "type":"level", "id":<room id>, "action":<position>, "model":1 }
```

### getRoomInfo

(Needs GatewayLogin first - may need AdminLogin) \
POST: http://192.168.20.78/cgi-bin/cgi/getRoomInfo \
Returns

```json
{
    "totalRooms": 2,
    "rooms": [
        {
            "groupname": [
                "Left",
                "Middle",
                "Right",
                "All",
                "group5"
            ],
            "Id": 17488,
            "Name": "Study",
            "Color": 11,
            "Style": 13,
            "Sort": 0
        },
        {
            "groupname": [
                "Left",
                "Middle",
                "Right",
                "All",
                "group5"
            ],
            "Id": 6385,
            "Name": "Living Room",
            "Color": 8,
            "Style": 1,
            "Sort": 1
        }
    ]
}
```

### getWindowInfo

(Needs GatewayLogin first) \
POST: http://NORMANHUB_9DDD2D.local/cgi-bin/cgi/getWindowInfo \
Returns

```json
{
    "totalWindow": 6,
    "windows": [
        {
            "Id": 15566,
            "Name": "Id 3cce",
            "Level": 0,
            "Sort": 0,
            "RId": 17488,
            "roomId": 17488,
            "scenes": [
                {
                    "Id": 0,
                    "Position": 0,
                    "Angle": 0
                }
            ],
            "groupId": 10,
            "level": [
                0,
                1,
                0,
                1,
                0
            ],
            "levelsort": [
                0,
                1,
                0,
                1,
                0
            ],
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
        },
        {
            "Id": 12674,
            "Name": "Id 3182",
            "Level": 0,
            "Sort": 1,
            "RId": 6385,
            "roomId": 6385,
            "scenes": [
                {
                    "Id": 0,
                    "Position": 0,
                    "Angle": 0
                }
            ],
            "groupId": 10,
            "level": [
                0,
                1,
                0,
                1,
                0
            ],
            "levelsort": [
                0,
                1,
                0,
                1,
                0
            ],
            "battery": "74",
            "position": 81,
            "angle": 0,
            "model": 1,
            "Rssi": 66,
            "temp": 17,
            "ver": "0.0.39",
            "solar": 4388,
            "usb": 0,
            "speed": 0,
            "model_detail": 0
        },
        {
            "Id": 47287,
            "Name": "Id b8b7",
            "Level": 0,
            "Sort": 2,
            "RId": 6385,
            "roomId": 6385,
            "scenes": [
                {
                    "Id": 0,
                    "Position": 0,
                    "Angle": 0
                }
            ],
            "groupId": 9,
            "level": [
                1,
                0,
                0,
                1,
                0
            ],
            "levelsort": [
                1,
                0,
                0,
                2,
                0
            ],
            "battery": "15",
            "position": 25,
            "angle": 0,
            "model": 1,
            "Rssi": 74,
            "temp": 17,
            "ver": "0.0.39",
            "solar": 7597,
            "usb": 1929,
            "speed": 0,
            "model_detail": 0
        },
        {
            "Id": 33774,
            "Name": "Id 83ee",
            "Level": 0,
            "Sort": 3,
            "RId": 17488,
            "roomId": 17488,
            "scenes": [
                {
                    "Id": 0,
                    "Position": 0,
                    "Angle": 0
                }
            ],
            "groupId": 9,
            "level": [
                1,
                0,
                0,
                1,
                0
            ],
            "levelsort": [
                1,
                0,
                0,
                2,
                0
            ],
            "battery": "100",
            "position": 37,
            "angle": 0,
            "model": 1,
            "Rssi": 70,
            "temp": 22,
            "ver": "0.6.8",
            "solar": 65535,
            "usb": 0,
            "speed": 0,
            "model_detail": 0
        },
        {
            "Id": 48143,
            "Name": "Id bc0f",
            "Level": 0,
            "Sort": 4,
            "RId": 6385,
            "roomId": 6385,
            "scenes": [
                {
                    "Id": 0,
                    "Position": 0,
                    "Angle": 0
                }
            ],
            "groupId": 12,
            "level": [
                0,
                0,
                1,
                1,
                0
            ],
            "levelsort": [
                0,
                0,
                1,
                3,
                0
            ],
            "battery": "100",
            "position": 65,
            "angle": 0,
            "model": 1,
            "Rssi": 71,
            "temp": 17,
            "ver": "0.0.39",
            "solar": 16868,
            "usb": 0,
            "speed": 0,
            "model_detail": 0
        },
        {
            "Id": 43830,
            "Name": "Id ab36",
            "Level": 0,
            "Sort": 5,
            "RId": 17488,
            "roomId": 17488,
            "scenes": [
                {
                    "Id": 0,
                    "Position": 0,
                    "Angle": 0
                }
            ],
            "groupId": 12,
            "level": [
                0,
                0,
                1,
                1,
                0
            ],
            "levelsort": [
                0,
                0,
                1,
                3,
                0
            ],
            "battery": "100",
            "position": 37,
            "angle": 0,
            "model": 1,
            "Rssi": 65,
            "temp": 22,
            "ver": "0.6.8",
            "solar": 65535,
            "usb": 0,
            "speed": 0,
            "model_detail": 0
        }
    ]
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⚠️ Disclaimer**: This is an unofficial integration not affiliated with Norman Blinds (aka Shutters). Use at your own risk.
