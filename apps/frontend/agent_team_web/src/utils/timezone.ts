/**
 * Timezone utility functions
 */

/**
 * Common timezones grouped by region
 */
export const TIMEZONE_OPTIONS = [
  // UTC
  { value: "UTC", label: "UTC (Coordinated Universal Time)", offset: "+0:00" },

  // Americas
  { value: "America/New_York", label: "Eastern Time (US & Canada)", offset: "-5:00" },
  { value: "America/Chicago", label: "Central Time (US & Canada)", offset: "-6:00" },
  { value: "America/Denver", label: "Mountain Time (US & Canada)", offset: "-7:00" },
  { value: "America/Los_Angeles", label: "Pacific Time (US & Canada)", offset: "-8:00" },
  { value: "America/Anchorage", label: "Alaska", offset: "-9:00" },
  { value: "Pacific/Honolulu", label: "Hawaii", offset: "-10:00" },
  { value: "America/Toronto", label: "Toronto", offset: "-5:00" },
  { value: "America/Vancouver", label: "Vancouver", offset: "-8:00" },
  { value: "America/Mexico_City", label: "Mexico City", offset: "-6:00" },
  { value: "America/Sao_Paulo", label: "São Paulo", offset: "-3:00" },
  { value: "America/Buenos_Aires", label: "Buenos Aires", offset: "-3:00" },

  // Europe
  { value: "Europe/London", label: "London", offset: "+0:00" },
  { value: "Europe/Paris", label: "Paris", offset: "+1:00" },
  { value: "Europe/Berlin", label: "Berlin", offset: "+1:00" },
  { value: "Europe/Rome", label: "Rome", offset: "+1:00" },
  { value: "Europe/Madrid", label: "Madrid", offset: "+1:00" },
  { value: "Europe/Amsterdam", label: "Amsterdam", offset: "+1:00" },
  { value: "Europe/Brussels", label: "Brussels", offset: "+1:00" },
  { value: "Europe/Vienna", label: "Vienna", offset: "+1:00" },
  { value: "Europe/Stockholm", label: "Stockholm", offset: "+1:00" },
  { value: "Europe/Warsaw", label: "Warsaw", offset: "+1:00" },
  { value: "Europe/Athens", label: "Athens", offset: "+2:00" },
  { value: "Europe/Istanbul", label: "Istanbul", offset: "+3:00" },
  { value: "Europe/Moscow", label: "Moscow", offset: "+3:00" },

  // Asia
  { value: "Asia/Dubai", label: "Dubai", offset: "+4:00" },
  { value: "Asia/Karachi", label: "Karachi", offset: "+5:00" },
  { value: "Asia/Kolkata", label: "Mumbai, Kolkata, New Delhi", offset: "+5:30" },
  { value: "Asia/Dhaka", label: "Dhaka", offset: "+6:00" },
  { value: "Asia/Bangkok", label: "Bangkok", offset: "+7:00" },
  { value: "Asia/Singapore", label: "Singapore", offset: "+8:00" },
  { value: "Asia/Hong_Kong", label: "Hong Kong", offset: "+8:00" },
  { value: "Asia/Shanghai", label: "Beijing, Shanghai", offset: "+8:00" },
  { value: "Asia/Tokyo", label: "Tokyo", offset: "+9:00" },
  { value: "Asia/Seoul", label: "Seoul", offset: "+9:00" },
  { value: "Asia/Jakarta", label: "Jakarta", offset: "+7:00" },
  { value: "Asia/Manila", label: "Manila", offset: "+8:00" },

  // Australia & Pacific
  { value: "Australia/Sydney", label: "Sydney", offset: "+11:00" },
  { value: "Australia/Melbourne", label: "Melbourne", offset: "+11:00" },
  { value: "Australia/Brisbane", label: "Brisbane", offset: "+10:00" },
  { value: "Australia/Perth", label: "Perth", offset: "+8:00" },
  { value: "Pacific/Auckland", label: "Auckland", offset: "+13:00" },
  { value: "Pacific/Fiji", label: "Fiji", offset: "+12:00" },

  // Africa
  { value: "Africa/Cairo", label: "Cairo", offset: "+2:00" },
  { value: "Africa/Johannesburg", label: "Johannesburg", offset: "+2:00" },
  { value: "Africa/Lagos", label: "Lagos", offset: "+1:00" },
  { value: "Africa/Nairobi", label: "Nairobi", offset: "+3:00" },

  // Middle East
  { value: "Asia/Jerusalem", label: "Jerusalem", offset: "+2:00" },
  { value: "Asia/Riyadh", label: "Riyadh", offset: "+3:00" },
  { value: "Asia/Tehran", label: "Tehran", offset: "+3:30" },
];

/**
 * Get the user's current timezone using the browser's Intl API
 * @returns IANA timezone string (e.g., "America/New_York", "Europe/London", "Asia/Tokyo")
 */
export function getUserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch (error) {
    console.warn("Failed to detect user timezone, falling back to UTC:", error);
    return "UTC";
  }
}

/**
 * Get a human-readable timezone name with UTC offset
 * @param timezone - IANA timezone string
 * @returns Human-readable timezone (e.g., "America/New_York (UTC-5)")
 */
export function getTimezoneWithOffset(timezone?: string): string {
  const tz = timezone || getUserTimezone();
  try {
    const now = new Date();
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      timeZoneName: "short",
    });
    const parts = formatter.formatToParts(now);
    const offsetPart = parts.find((part) => part.type === "timeZoneName");
    return offsetPart ? `${tz} (${offsetPart.value})` : tz;
  } catch {
    return tz;
  }
}

/**
 * Get UTC offset in hours for a timezone
 * @param timezone - IANA timezone string
 * @returns UTC offset in hours (e.g., -5 for EST, 9 for JST)
 */
export function getTimezoneOffset(timezone?: string): number {
  const tz = timezone || getUserTimezone();
  try {
    const now = new Date();
    const utcDate = new Date(now.toLocaleString("en-US", { timeZone: "UTC" }));
    const tzDate = new Date(now.toLocaleString("en-US", { timeZone: tz }));
    return (tzDate.getTime() - utcDate.getTime()) / (1000 * 60 * 60);
  } catch {
    return 0;
  }
}

/**
 * Check if a timezone string is valid
 * @param timezone - IANA timezone string to validate
 * @returns true if valid, false otherwise
 */
export function isValidTimezone(timezone: string): boolean {
  try {
    Intl.DateTimeFormat(undefined, { timeZone: timezone });
    return true;
  } catch {
    return false;
  }
}
