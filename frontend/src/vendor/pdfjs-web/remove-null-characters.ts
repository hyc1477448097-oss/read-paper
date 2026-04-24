/* SPDX-License-Identifier: Apache-2.0 */
/* Derived from mozilla/pdf.js v5.6.205 web/ui_utils.js (removeNullCharacters only). */

const InvisibleCharsRegExp = /[\x00-\x1F]/g

/**
 * Strip NUL and optionally other control characters (viewer copy path).
 */
export function removeNullCharacters(str: string, replaceInvisible = false): string {
  if (!InvisibleCharsRegExp.test(str)) {
    return str
  }
  if (replaceInvisible) {
    return str.replaceAll(InvisibleCharsRegExp, (m) => (m === '\x00' ? '' : ' '))
  }
  return str.replaceAll('\x00', '')
}
