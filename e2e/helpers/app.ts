import { test as base, expect, type Locator, type Page } from "@playwright/test";

/** A storage state with no session, for `test.use({ storageState: GUEST })`. */
export const GUEST = { cookies: [], origins: [] };

/** Tomorrow as `YYYY-MM-DD` in UTC — the date the venue page opens on. */
export function tomorrowISO(): string {
	return new Date(Date.now() + 86400000).toISOString().slice(0, 10);
}

/**
 * The suite's `test`. Import this instead of `@playwright/test` in specs so a
 * fixture every page needs lands in one place; the auth setup files keep the
 * base `test`.
 */
export const test = base;

export { expect };
export type { Page, Locator };
