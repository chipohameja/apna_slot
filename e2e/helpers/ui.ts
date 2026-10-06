import { expect, type Locator, type Page } from "@playwright/test";

/**
 * Locators and flows for the Apna Slot SPA.
 *
 * Specs go through these instead of reaching for markup so a frappe-ui bump
 * changes one file rather than every spec. Roles and labels first; where
 * frappe-ui publishes nothing to hold on to, the app carries a `data-testid`.
 */

/** Open an SPA route and wait for its data to settle. */
export async function gotoApp(page: Page, path: string): Promise<void> {
	await page.goto(path.startsWith("/apnaslot") ? path : `/apnaslot${path}`);
	await page.waitForLoadState("networkidle");
}

/* -------------------------------------------------------------------------- */
/* Discovery                                                                  */
/* -------------------------------------------------------------------------- */

/** A venue card on the home page, by venue name. */
export function venueCard(page: Page, venueName: string): Locator {
	return page.getByRole("link").filter({
		has: page.getByRole("heading", { name: venueName, exact: true }),
	});
}

/* -------------------------------------------------------------------------- */
/* Venue page                                                                 */
/* -------------------------------------------------------------------------- */

/** Every slot button in the day grid. */
export function slotButtons(page: Page): Locator {
	return page.getByRole("button", { name: /^\d\d:\d\d–\d\d:\d\d/ });
}

/** A slot button by its start time, e.g. `"19:00"`. */
export function slotButton(page: Page, start: string): Locator {
	return page.getByRole("button", { name: new RegExp(`^${start}–`) });
}

/** Open a venue's page and wait for its grid. */
export async function openVenue(page: Page, slug: string): Promise<void> {
	await gotoApp(page, `/venues/${slug}`);
	await expect(slotButtons(page).first()).toBeVisible();
}

/** Hold a slot and land on its checkout. */
export async function holdSlot(page: Page, slug: string, start: string): Promise<void> {
	await openVenue(page, slug);
	await slotButton(page, start).click();
	await page.waitForURL(/\/apnaslot\/checkout\//);
}

/* -------------------------------------------------------------------------- */
/* Checkout and mock payment                                                  */
/* -------------------------------------------------------------------------- */

/** The booking status badge on checkout or a My bookings row. */
export function statusBadge(scope: Page | Locator, status: string): Locator {
	return scope.getByText(status, { exact: true });
}

/**
 * Pay from checkout and choose the mock gateway's outcome. Paying leaves the
 * SPA for `/pay/:token`, as a real hosted checkout would.
 */
export async function payWith(
	page: Page,
	outcome: "Succeed" | "Fail" | "Abandon",
): Promise<string> {
	await page.getByRole("button", { name: /^Pay / }).click();
	await page.waitForURL(/\/apnaslot\/pay\//);
	const payUrl = page.url();
	await page.getByRole("button", { name: outcome, exact: true }).click();
	await page.waitForURL((url) => !url.pathname.includes("/pay/"));
	return payUrl;
}

/* -------------------------------------------------------------------------- */
/* Account                                                                    */
/* -------------------------------------------------------------------------- */

/** A row in My bookings, by venue name. */
export function bookingRow(page: Page, venueName: string): Locator {
	return page.getByRole("link").filter({ hasText: venueName });
}

/* -------------------------------------------------------------------------- */
/* Selects                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * frappe-ui's `Combobox` and `Select` are reka-ui listboxes, not native
 * `<select>`s: the trigger opens a portal outside the component, so this opens
 * the trigger and clicks the option by role. A searchable combobox is typed
 * into first, so a long list (300 countries) need not be scrolled.
 */
export async function selectOption(
	page: Page,
	trigger: Locator,
	option: string | RegExp,
): Promise<void> {
	await trigger.click();
	if (typeof option === "string" && (await trigger.isEditable().catch(() => false))) {
		await trigger.fill(option);
	}
	const item = page.getByRole("option", { name: option, exact: true });
	await expect(item.first()).toBeVisible({ timeout: 5000 });
	await item.first().click();
}
