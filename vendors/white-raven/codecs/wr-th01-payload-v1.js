// Firmware 1.0.0 example contract; these are not raw SHT40 I2C bytes.
function decodeUplink(input) {
  if (!input || input.fPort !== 1) {
    return { errors: ["Expected FPort 1"] };
  }
  if (!Array.isArray(input.bytes) || input.bytes.length !== 4) {
    return { errors: ["Expected exactly 4 payload bytes"] };
  }
  for (var i = 0; i < input.bytes.length; i++) {
    var value = input.bytes[i];
    if (typeof value !== "number" || !isFinite(value) ||
        Math.floor(value) !== value || value < 0 || value > 255) {
      return { errors: ["Payload bytes must be integers between 0 and 255"] };
    }
  }

  var temperatureRaw = (input.bytes[0] << 8) | input.bytes[1];
  if (temperatureRaw & 0x8000) {
    temperatureRaw -= 0x10000;
  }
  var temperature = temperatureRaw / 100;
  var humidity = ((input.bytes[2] << 8) | input.bytes[3]) / 100;
  if (temperature < -40 || temperature > 125) {
    return { errors: ["Temperature must be between -40 and 125 degrees Celsius"] };
  }
  if (humidity > 100) {
    return { errors: ["Relative humidity must be between 0 and 100 percent"] };
  }
  return { data: { temperature: temperature, humidity: humidity } };
}

// The example firmware has no application downlink command protocol.
function encodeDownlink(input) {
  return { errors: ["Application downlinks are not supported by SHT40 example firmware 1.0.0"] };
}
