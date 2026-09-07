# WR-TH Device Profile Example Using the SHT40 Sensor

This repository is the source of device profiles and codecs for the project. The White Raven example uses the real SHT40 temperature and humidity sensor, but the firmware contract below is a **proposed example**. Firmware and physical board compatibility have not been tested here. The SHT40 is an I2C component, not a standalone LoRaWAN device.

One model has two firmware versions: **1.0.0 without battery reporting** and **2.0.0 with battery percentage reporting**. The four-byte contract below describes version 1. See the [two-firmware example](docs/firmware-versions.md) for a comparison and upgrade steps.

## Files and Responsibilities

| Path | Purpose |
| --- | --- |
| `vendors/white-raven/vendor.toml` | Vendor information |
| `vendors/white-raven/devices/wr-th.toml` | Stable model identity, firmware versions, profile and codec references |
| `vendors/white-raven/profiles/wr-th-EU868-otaa-a.toml` | LoRaWAN network capabilities |
| `vendors/white-raven/codecs/wr-th-payload-v1.js` | Decode the example temperature and humidity payload |
| `vendors/white-raven/codecs/test_decode_wr-th-payload-v1.json` | Decoder inputs and expected outputs |
| `vendors/white-raven/codecs/test_encode_wr-th-payload-v1.json` | Test rejection of unsupported downlinks |
| `vendors/white-raven/codecs/wr-th-payload-v2.js` | Standalone version 2 codec, including battery |
| `vendors/white-raven/codecs/test_decode_wr-th-payload-v2.json` | Version 2 decoder tests |
| `vendors/white-raven/codecs/test_encode_wr-th-payload-v2.json` | Version 2 downlink rejection test |
| `backend-profiles.json` | Backend-specific metadata; ChirpStack does not consume this file |
| `scripts/test-codecs.cjs` | Run codec tests with Node.js, without installing packages |
| `scripts/validate-catalog.py` | Validate TOML, UUIDs, file references and metadata with Python 3.11+ |

The `example-vendor` directory remains unchanged. Our example for further development is in `white-raven`.

## Example Firmware 1.0.0 Contract

Proposed settings: EU868, LoRaWAN 1.0.4, Regional Parameters RP002-1.0.3, Class A and OTAA. These settings describe the **LoRaWAN board and its firmware**; the SHT40 model does not determine them.

The proposed uplink interval is 3600 seconds, and the firmware must implement this schedule. The metadata field `expected_uplink_interval_seconds` is descriptive only. With `idle_threshold_seconds=7200`, the backend marks the device idle on the next watchdog run after more than two hours of silence.

### Uplink Payload

FPort is **1**, and the payload is exactly **4 bytes**:

| Bytes | Type | Value |
| --- | --- | --- |
| 0..1 | Signed int16, big-endian | Temperature in degrees Celsius multiplied by 100 |
| 2..3 | Unsigned int16, big-endian | Relative humidity in percent multiplied by 100 |

Examples:

- `09 C4 15 7C` -> temperature 25, humidity 55.
- `FB 2E 11 D7` -> temperature -12.34, humidity 45.67.
- `F0 60 27 10` -> temperature -40, humidity 100.

Successful codec output:

```json
{
  "data": {
    "temperature": 25,
    "humidity": 55
  }
}
```

ChirpStack places the contents of `data` in the uplink event's `object`; the backend stores that object.

An incorrect port, invalid length, invalid byte, temperature outside -40..125, or humidity outside 0..100 produces `errors`, not fabricated readings. This payload is **not raw sensor I2C output**. The firmware must use the sensor driver to read the SHT40 data and check its CRC, convert the readings to engineering units, and then construct the four-byte payload.

Firmware packing pseudocode, after validating the measurement ranges:

```c
int16_t t = (int16_t)lroundf(temperature_c * 100.0f);
uint16_t h = (uint16_t)lroundf(relative_humidity * 100.0f);
uint16_t unsigned_t = (uint16_t)t;
uint8_t payload[4] = {
    (uint8_t)(unsigned_t >> 8), (uint8_t)unsigned_t,
    (uint8_t)(h >> 8), (uint8_t)h
};
// Send payload on FPort 1 using your board's LoRaWAN library.
```

Do not turn driver errors or invalid values into zero or valid measurements. The example has no application downlink commands, so `encodeDownlink` returns an explicit error. This does not disable network MAC downlinks.

## Field Reference

### Vendor and Device

- `vendor.id`: Stable vendor UUID. The existing value has been preserved.
- `vendor.name` and `vendor.metadata.homepage`: Vendor name and project homepage.
- `vendor.vendor_id`: Numeric identifier assigned by the LoRa Alliance, not the internal UUID. Because no official assignment has been confirmed for this project, the previous value 601 was replaced with 0, the ChirpStack example default. Zero is not your assigned identity and must not be used as the product's official Vendor ID in a standard QR code.
- `vendor.ouis`: IEEE-assigned OUIs owned by the vendor, each represented by six hexadecimal digits without separators. The unverified value 24e124 was removed, leaving an empty list. A purchased module's prefix or another manufacturer's EUI does not establish OUI ownership for your brand. Enter official values after confirming the assignments; the internal catalog UUID remains unchanged.
- `vendor.devices`: Device filenames for readability and compatible tools; keep the list synchronized. The current ChirpStack importer scans the devices directory.
- `device.id`: WR-TH model identity in the catalog: `66f81612-6b81-4609-89d6-d2c5bcd861a3`. This is **not a physical device's DevEUI**.
- `device.name/description`: Model name and description.
- `device.metadata`: Descriptive string values. The product URL refers to the Sensirion component. Example status, payload format and reporting interval are also documented here. These values do not configure firmware execution.
- `device.firmware`: Firmware version, regional profile files and the codec for that version.

### Profile

- `vendor_profile_id`: Private example number 1. It does not replace a UUID or establish official registration.
- `region/mac_version/reg_params_revision`: Settings matching the firmware and region.
- `supports_otaa=true`: OTAA activation. Manage each device's keys and DevEUI separately, outside this repository.
- `supports_class_b=false` and `supports_class_c=false`: This is a Class A example.
- `max_eirp=16`: Example board and antenna assumption; verify before real deployment.
- `abp`: RX1 delay/offset and RX2 data rate/frequency. Inactive because OTAA is enabled.
- `class_b`: Timeout, periodicity, data rate and frequency. Inactive because Class B is disabled. The current importer uses the key `ping_slot_periodicity`.
- `class_c.timeout_secs`: Inactive Class C timeout.
- `app_layer_params`: Versions and ports for TS003/TS004/TS005. An empty version means the capability is not implemented. The zero ports in these sections are **not sensor payload ports**.

Inactive sections are filled in for learning purposes; their presence does not enable the capabilities. Not every UI setting is an importable TOML field. The current importer supplies defaults for some values, such as the uplink interval; adding an arbitrary key does not necessarily change them.

### Backend Metadata

In `backend-profiles.json`:

- `catalog_device_id` exactly matches `device.id`.
- `firmware_version` and `region` must match the corresponding files.
- `idle_threshold_seconds` configures the backend watchdog, not the firmware.
- `payload_descriptor` describes codec output fields. Version 1.0.0 has `temperature` and `humidity`; version 2.0.0 also has `battery`.
- `type/unit` describe the type and unit; `label/min/max/decimals` provide suggested display metadata. Metadata alone does not implement UI features or validation; consumers must support it. Two decimal places in the contract do not imply that level of sensor accuracy.

Do not confuse the three identifiers: the model UUID in this repository, the profile UUID in ChirpStack, and the local profile UUID in the backend. Refresh maps the latter two using model identity + firmware + region.

## Testing and Usage

From this repository's root:

```sh
python scripts/validate-catalog.py
node scripts/test-codecs.cjs
```

Then, on the ChirpStack host using that installation's configuration:

```sh
chirpstack -c /etc/chirpstack import-device-profiles -d /opt/device-profile-template
```

From the backend repository's root:

```sh
go run ./cmd/profile-refresh --metadata /opt/device-profile-template/backend-profiles.json
```

Paths are examples; on Windows you can also supply the full JSON path. The workflow is: manually fetch the repository revision -> test -> manually import -> manually refresh. Import and hardware testing have not been performed for this example. Do not put device secrets or network tokens in this repository.

## Adding a Device, Firmware Version or Region

1. For a new model, create a Device file with a new UUID. Preserve the UUID when renaming the same model or adding firmware.
2. Complete the regional profile using the board's actual capabilities. Do not copy EU868 and merely rename the file for another region.
3. Document the byte format, FPort, units, ranges and error behavior. Add a codec and valid/invalid fixtures.
4. Reference the profile and codec from the firmware entry, and update the vendor's device list.
5. Add backend metadata for each required model + firmware + region combination.
6. If the payload format changes, add a new firmware version and codec file. Retain the previous version for older devices.
7. Run tests, import and refresh. Do not recreate the profile through the backend.
8. Removing an entry from the JSON makes it inactive for new provisioning after refresh; existing devices are not deleted. For safety, the current refresh implementation rejects an entirely empty catalog.

## References

- [SHT40 component](https://sensirion.com/products/catalog/SHT40)
- [Official profile repository](https://github.com/chirpstack/chirpstack-device-profiles)
- [Current ChirpStack importer fields and behavior](https://github.com/chirpstack/chirpstack/blob/master/chirpstack/src/cmd/import_device_profiles.rs)

Check the importer schema for your target ChirpStack version. The older example-vendor template may not show every field supported by a newer importer.

