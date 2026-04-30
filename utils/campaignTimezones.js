/**
 * Builds timezone options for campaign settings: Windows-style labels with UTC offset + IANA id.
 * Values sent to the API remain canonical IANA strings (e.g. Asia/Karachi).
 */

const FALLBACK_TIMEZONE_IDS = [
  "UTC",
  "Africa/Cairo",
  "Africa/Johannesburg",
  "Africa/Lagos",
  "America/Anchorage",
  "America/Bogota",
  "America/Buenos_Aires",
  "America/Caracas",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Mexico_City",
  "America/New_York",
  "America/Phoenix",
  "America/Santiago",
  "America/Sao_Paulo",
  "America/Toronto",
  "America/Vancouver",
  "Asia/Baghdad",
  "Asia/Bangkok",
  "Asia/Dhaka",
  "Asia/Dubai",
  "Asia/Hong_Kong",
  "Asia/Jakarta",
  "Asia/Jerusalem",
  "Asia/Karachi",
  "Asia/Kolkata",
  "Asia/Kuala_Lumpur",
  "Asia/Manila",
  "Asia/Riyadh",
  "Asia/Seoul",
  "Asia/Shanghai",
  "Asia/Singapore",
  "Asia/Taipei",
  "Asia/Tehran",
  "Asia/Tokyo",
  "Asia/Yangon",
  "Australia/Adelaide",
  "Australia/Brisbane",
  "Australia/Melbourne",
  "Australia/Perth",
  "Australia/Sydney",
  "Europe/Amsterdam",
  "Europe/Athens",
  "Europe/Berlin",
  "Europe/Brussels",
  "Europe/Dublin",
  "Europe/Helsinki",
  "Europe/Istanbul",
  "Europe/Lisbon",
  "Europe/London",
  "Europe/Madrid",
  "Europe/Moscow",
  "Europe/Paris",
  "Europe/Prague",
  "Europe/Rome",
  "Europe/Stockholm",
  "Europe/Vienna",
  "Europe/Warsaw",
  "Pacific/Auckland",
  "Pacific/Fiji",
  "Pacific/Guam",
  "Pacific/Honolulu",
];

let cachedOptions = null;

function parseGmtStringToMinutes(s) {
  if (!s || s === "GMT") return 0;
  const inner = String(s).replace(/^GMT/i, "").trim();
  if (!inner) return 0;
  const m = inner.match(/^([+-])(\d{1,2})(?::(\d{2}))?$/);
  if (!m) return 0;
  const sign = m[1] === "-" ? -1 : 1;
  const h = parseInt(m[2], 10);
  const min = m[3] ? parseInt(m[3], 10) : 0;
  return sign * (h * 60 + min);
}

function formatUtcOffsetFromMinutes(totalMinutes) {
  const sign = totalMinutes >= 0 ? "+" : "-";
  const abs = Math.abs(Math.round(totalMinutes));
  const h = Math.floor(abs / 60);
  const m = abs % 60;
  return `(UTC${sign}${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")})`;
}

/**
 * Current offset for zone (respects DST for `referenceDate`).
 */
export function getOffsetMinutesForZone(timeZone, referenceDate = new Date()) {
  try {
    const dtf = new Intl.DateTimeFormat("en-US", {
      timeZone,
      timeZoneName: "longOffset",
    });
    const parts = dtf.formatToParts(referenceDate);
    const raw = parts.find((p) => p.type === "timeZoneName")?.value ?? "GMT";
    return parseGmtStringToMinutes(raw);
  } catch {
    return 0;
  }
}

export function buildTimezoneOption(timeZoneId, referenceDate = new Date()) {
  const minutes = getOffsetMinutesForZone(timeZoneId, referenceDate);
  const offsetLabel = formatUtcOffsetFromMinutes(minutes);
  const label = `${offsetLabel} ${timeZoneId}`;
  return {
    value: timeZoneId,
    label,
    sortKey: minutes,
    id: timeZoneId,
  };
}

function collectTimeZoneIds() {
  if (typeof Intl !== "undefined" && typeof Intl.supportedValuesOf === "function") {
    try {
      const list = Intl.supportedValuesOf("timeZone");
      if (Array.isArray(list) && list.length > 0) return list;
    } catch {
      /* ignore */
    }
  }
  return [...FALLBACK_TIMEZONE_IDS];
}

/**
 * Sorted list: west → east (by current UTC offset), then by IANA id.
 */
export function getCampaignTimezoneOptions() {
  if (cachedOptions) return cachedOptions;
  const referenceDate = new Date();
  const ids = collectTimeZoneIds();
  const rows = ids.map((id) => buildTimezoneOption(id, referenceDate));
  rows.sort((a, b) => a.sortKey - b.sortKey || a.id.localeCompare(b.id));
  cachedOptions = rows;
  return cachedOptions;
}

export function filterTimezoneOptions(options, query) {
  const q = query.trim().toLowerCase();
  if (!q) return options;
  return options.filter(
    (o) => o.value.toLowerCase().includes(q) || o.label.toLowerCase().includes(q)
  );
}
