/**
 * Converts YEAR+DOY (from .OUT files) or YYDDD (from T files) to ISO date string (YYYY-MM-DD).
 * @param {string|number} yearOrYYDDD - YEAR (for .OUT) or YYDDD (for T).
 * @param {string|number|null} doy - DOY if separate (for .OUT); null for YYDDD.
 * @returns {string|null} ISO date or null if invalid.
 */
function convertToISODate(yearOrYYDDD, doy = null) {
  if (doy !== null) { // From .OUT: separate YEAR and DOY
    const y = parseInt(yearOrYYDDD, 10);
    const d = parseInt(doy, 10);
    if (isNaN(y) || isNaN(d) || d < 1 || d > 366) return null;
    const date = new Date(y, 0, 1); // Start at Jan 1
    date.setDate(date.getDate() + d - 1);
    return date.toISOString().split('T')[0];
  } else { // From T: YYDDD format
    const num = parseInt(yearOrYYDDD, 10);
    if (isNaN(num) || num < 0) return null;
    const yy = Math.floor(num / 1000);
    const d = num % 1000;
    if (d < 1 || d > 366) return null;
    const y = yy >= 40 ? 1900 + yy : 2000 + yy; // Adjust for century (assuming 1940+ are 1900s)
    const date = new Date(y, 0, 1);
    date.setDate(date.getDate() + d - 1);
    return date.toISOString().split('T')[0];
  }
}

module.exports = { convertToISODate };