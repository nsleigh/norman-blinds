# Norman Blinds
Reverse engineering the Norman Blinds hub protocol

Process to reset and detect blinds (this worked when other methods didn't)
- On hub press for 3 seconds in to user setting mode
- Press three times: Norman Hub factory reset.

Other
- Press for 3 seconds in to user setting mode
- Press one time: Search shutters.
- Press two times: Station mode switch to AP mode.

# API

## GatewayLogin
http://192.168.20.78/cgi-bin/cgi/GatewayLogin
POST { "password":"123456789","app_version":"2.11.21" }
Various versions work e.g. 2.10.0
Returns 
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

