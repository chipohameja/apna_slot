import { expect, test } from "../helpers/app";
import { cleanupTestVenues, createTestVenue, type TestVenue } from "../helpers/apna_slot";
import {
	bookingRow,
	gotoApp,
	holdSlot,
	openVenue,
	payWith,
	slotButton,
	statusBadge,
} from "../helpers/ui";

test.describe("Customer booking", () => {
	let arena: TestVenue;

	test.beforeEach(async ({ request }) => {
		arena = await createTestVenue(request);
	});

	test.afterAll(async ({ request }) => {
		await cleanupTestVenues(request);
	});

	test("holds a slot, pays, and sees it confirmed everywhere", async ({ page }) => {
		await holdSlot(page, arena.venue.slug, "19:00");
		await expect(page.getByRole("heading", { name: "Your hold" })).toBeVisible();
		await expect(statusBadge(page, "Pending Payment")).toBeVisible();
		await expect(page.getByText(/yours for another (10:00|9:\d\d)/)).toBeVisible();

		await payWith(page, "Succeed");
		await expect(page.getByRole("heading", { name: "Your booking" })).toBeVisible();
		await expect(statusBadge(page, "Confirmed")).toBeVisible();
		await expect(page.getByRole("button", { name: /^Pay / })).toHaveCount(0);

		await openVenue(page, arena.venue.slug);
		await expect(slotButton(page, "19:00")).toBeDisabled();
		await expect(slotButton(page, "19:00")).toContainText("Booked");

		await gotoApp(page, "/bookings");
		const row = bookingRow(page, arena.venue.venue_name);
		await expect(row).toContainText("Turf A");
		await expect(statusBadge(row, "Confirmed")).toBeVisible();
	});

	test("frees the slot at once when payment fails", async ({ page }) => {
		await holdSlot(page, arena.venue.slug, "20:00");
		await payWith(page, "Fail");
		await expect(statusBadge(page, "Payment Failed")).toBeVisible();

		await openVenue(page, arena.venue.slug);
		await expect(slotButton(page, "20:00")).toBeEnabled();
	});

	test("keeps the hold when payment is abandoned", async ({ page }) => {
		await holdSlot(page, arena.venue.slug, "21:00");
		const checkoutUrl = page.url();
		const payUrl = await payWith(page, "Abandon");
		await expect(page).toHaveURL(/\/apnaslot\/?$/);

		await page.goto(checkoutUrl);
		await expect(statusBadge(page, "Pending Payment")).toBeVisible();

		await page.goto(payUrl);
		await expect(page.getByText("This payment is already abandoned.")).toBeVisible();
		await expect(page.getByRole("button", { name: "Succeed" })).toHaveCount(0);
	});
});
