"""Validate repository references and backend metadata without a ChirpStack host."""
import json
from pathlib import Path
import tomllib
import uuid

ROOT = Path(__file__).resolve().parents[1]


def read_toml(path):
    with path.open("rb") as stream:
        return tomllib.load(stream)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_uuid(value):
    parsed = uuid.UUID(value)
    require(parsed.int != 0, "UUID must not be nil")
    return str(parsed)


def validate():
    for path in (ROOT / "vendors").rglob("*.toml"):
        read_toml(path)
    models = set()
    vendor_ids = set()
    profiles = {}
    for vendor_dir in sorted((ROOT / "vendors").iterdir()):
        if not vendor_dir.is_dir() or vendor_dir.name == "example-vendor":
            continue
        vendor = read_toml(vendor_dir / "vendor.toml")["vendor"]
        vendor_id = valid_uuid(vendor["id"])
        require(vendor_id not in vendor_ids, "Duplicate vendor UUID")
        vendor_ids.add(vendor_id)
        devices = sorted((vendor_dir / "devices").glob("*.toml"))
        require(set(vendor.get("devices", [])) == {p.name for p in devices},
                "Vendor device list does not match device files")
        for path in devices:
            device = read_toml(path)["device"]
            device_id = valid_uuid(device["id"])
            require(device_id not in models, "Duplicate device UUID")
            models.add(device_id)
            require(device["name"] and device["description"], "Device description is missing")
            for firmware in device["firmware"]:
                require(firmware["version"], "Firmware version is missing")
                codec = vendor_dir / "codecs" / firmware["codec"]
                require(codec.is_file(), "Missing codec: " + str(codec))
                fixtures = codec.with_name("test_decode_" + codec.stem + ".json")
                vectors = json.loads(fixtures.read_text(encoding="utf-8"))
                fields = [set(v["expected"]["data"]) for v in vectors if "data" in v["expected"]]
                require(fields, "Codec needs a successful decode fixture")
                for name in firmware["profiles"]:
                    profile = read_toml(vendor_dir / "profiles" / name)["profile"]
                    key = (device_id, firmware["version"], profile["region"])
                    require(key not in profiles, "Duplicate device/firmware/region identity")
                    require(0 <= profile["vendor_profile_id"] <= 65535, "Invalid vendor profile number")
                    for flag in ("supports_otaa", "supports_class_b", "supports_class_c"):
                        require(type(profile[flag]) is bool, "Capability must be boolean")
                    require("ping_slot_nb_k" not in profile.get("class_b", {}),
                            "Use ping_slot_periodicity with the current importer")
                    profiles[key] = fields

    metadata = json.loads((ROOT / "backend-profiles.json").read_text(encoding="utf-8"))
    require(set(metadata) == {"profiles"} and metadata["profiles"], "Metadata profiles are required")
    seen = set()
    allowed = {"catalog_device_id", "firmware_version", "region",
               "idle_threshold_seconds", "payload_descriptor"}
    for entry in metadata["profiles"]:
        require(set(entry) <= allowed, "Unknown backend metadata field")
        key = (valid_uuid(entry["catalog_device_id"]), entry["firmware_version"], entry["region"])
        require(key in profiles and key not in seen, "Missing or duplicate metadata identity")
        seen.add(key)
        idle = entry.get("idle_threshold_seconds", 3600)
        require(type(idle) is int and idle > 0, "Idle threshold must be a positive integer")
        descriptor = entry.get("payload_descriptor", {})
        for fields in profiles[key]:
            require(set(descriptor) <= fields, "Descriptor names an absent codec output field")
        for field in descriptor.values():
            require(isinstance(field, dict) and field.get("type") in
                    {"number", "integer", "boolean", "string", "object", "array"},
                    "Descriptor field needs a supported type")
    print(f"Validated {len(vendor_ids)} vendors, {len(models)} devices, "
          f"{len(profiles)} profiles and {len(seen)} backend entries")


if __name__ == "__main__":
    validate()
