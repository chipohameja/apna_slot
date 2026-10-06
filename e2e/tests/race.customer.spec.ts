import { expect, test, tomorrowISO } from "../helpers/app";
import { cleanupTestVenues, createTestVenue, postAsPage } from "../helpers/apna_slot";
import { gotoApp, holdSlot, openVenue, slotButton } from "../helpers/ui";

test.describe("Two customers, one slot", () => {
	test.afterAll(async ({ request }) => {
		await cleanupTestVenues(request);
	});

	test("refuses the second hold and shows the slot booked", async ({ page, browser, request }) => {
		const arena = await createTestVenue(request);
		await holdSlot(page, arena.venue.slug, "19:00");

		// a second browser, logged in as someone else
		const other = await browser.newContext({ storageState: "e2e/.auth/user.json" });
		const rival = await other.newPage();
		await openVenue(rival, arena.venue.slug);
		await expect(slotButton(rival, "19:00")).toBeDisabled();
		await expect(slotButton(rival, "19:00")).toContainText("Booked");

		const refusal = await postAsPage(rival, "apna_slot.api.booking.create", {
			resource: arena.resource,
			slot_date: tomorrowISO(),
			start_time: "19:00:00",
		});
		expect(refusal.status).toBe(409);
		expect(refusal.message).toMatch(
			/^19:00 on \d{1,2} \w{3} is no longer available\. Pick another slot\.$/,
		);
		await other.close();

		await gotoApp(page, "/bookings");
		await expect(page.getByRole("link").filter({ hasText: arena.venue.venue_name })).toHaveCount(1);
	});
});
