# Practical Example: One WR-TH Model and Two Firmware Versions

The device model is **WR-TH**, using an SHT40 sensor. The filename changed from sht40 to wr-th, but the model UUID remains unchanged:

`66f81612-6b81-4609-89d6-d2c5bcd861a3`

"Version 1 without battery" means without **battery percentage reporting**. Both versions can still be battery-powered.

## Comparison

| Feature | Firmware 1.0.0 | Firmware 2.0.0 |
| --- | --- | --- |
| Device file | `devices/wr-th.toml` | Same file and UUID |
| Profile file | `profiles/wr-th-EU868-otaa-a.toml` | Same network capabilities |
| Codec | `wr-th-payload-v1.js` | `wr-th-payload-v2.js` |
| FPort | 1 | 1 |
| Payload length | 4 bytes | 5 bytes |
| Output | temperature, humidity | temperature, humidity, battery |
| Backend metadata | Entry with firmware_version=1.0.0 | Separate entry with firmware_version=2.0.0 |

One shared network profile file is sufficient because the region, class and activation method have not changed. However, each firmware and region combination receives its own corresponding ChirpStack profile after import, and refresh maintains a separate local backend record for it.

## What Changed in the Device File?

```toml
[[device.firmware]]
version = "1.0.0"
profiles = ["wr-th-EU868-otaa-a.toml"]
codec = "wr-th-payload-v1.js"

[[device.firmware]]
version = "2.0.0"
profiles = ["wr-th-EU868-otaa-a.toml"]
codec = "wr-th-payload-v2.js"
```

The previous section was not removed; a second section was added to the same model. Each version has its own standalone codec, without depending on another codec file. The old sht40 filenames are no longer used; version 1 codec logic was preserved.

## Example Payloads

The first four bytes are the same in both versions:

- Two bytes of signed int16 temperature, multiplied by 100, big-endian.
- Two bytes of unsigned int16 humidity, multiplied by 100, big-endian.

In version 2, the fifth byte contains battery percentage from 0 to 100. For example, hexadecimal `50` equals **80** in decimal.

```text
1.0.0: 09 C4 15 7C
2.0.0: 09 C4 15 7C 50
```

Version 1 output:

```json
{"data":{"temperature":25,"humidity":55}}
```

Version 2 output:

```json
{"data":{"temperature":25,"humidity":55,"battery":80}}
```

Version 1 has no battery field; an absent field does not mean zero percent. In version 2, zero and 100 percent are valid, while 101 through 255 are invalid. This contract does not define an "unknown battery" value. The firmware must measure or calculate the percentage; the codec does not infer it from temperature or voltage.

The version 1 codec rejects a five-byte packet, and the version 2 codec rejects a four-byte packet. Selecting the wrong firmware profile is not silently hidden.

## The backend-profiles.json File

There are two entries with the **same catalog_device_id** and different firmware versions. The first describes only temperature and humidity. The second also contains this field definition:

```json
"battery": {
  "type": "integer",
  "label": "Battery",
  "unit": "%",
  "min": 0,
  "max": 100,
  "decimals": 0
}
```

This definition is not a battery reading; it only describes how the field can be displayed. The actual value of 80 comes from the example payload above.

**Current backend behavior:** This battery value is part of the uplink, stored in `decoded.battery`. It is not automatically copied into `device_status.battery_level`. The device battery snapshot still updates from a separate StatusEvent. To chart this example, select the battery field from telemetry; these changes do not implement a new UI.

## What Should Happen When a Device Is Upgraded?

1. Run the repository tests.
2. Manually import the profiles and codecs for both versions into ChirpStack.
3. Manually refresh the backend catalog. Keep version 1 available for older devices.
4. Devices that actually received firmware 2.0.0 must use the 2.0.0 profile. Other devices must remain on the 1.0.0 profile.

Importing profiles does not upgrade board firmware, and refreshing the catalog does not automatically change existing device assignments. This example does not add a backend endpoint for changing an existing device's profile. Coordinating the local and ChirpStack assignments is a separate task. Changing only the profile in the ChirpStack UI can leave it inconsistent with the mapping stored by the backend.

For a new device, choose the local profile ID matching its installed firmware during provisioning. Do not identify the firmware version using the WR-TH display name alone.

## Running the Checks

From the repository root:

```sh
python scripts/validate-catalog.py
node scripts/test-codecs.cjs
```

This example consists only of profile, codec, metadata and test files. No flashable firmware was built, and no physical board or live ChirpStack testing was performed.

