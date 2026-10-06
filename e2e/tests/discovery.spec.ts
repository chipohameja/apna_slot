import { GUEST, expect, test } from "../helpers/app";
import { SEED } from "../helpers/apna_slot";
import { gotoApp, openVenue, slotButton, slotButtons, venueCard } from "../helpers/ui";

test.use({ storageState: GUEST });

test.describe("Discovery as a guest", () => {
	test("lists the published venue with its starting price", async ({ page }) => {
		await gotoApp(page, "/");
		const card = venueCard(page, SEED.venue);
		await expect(card).toBeVisible();
		await expect(card).toContainText(/from AED\s250 per slot · 1 resource/);
	});

	test("shows tomorrow's four slots at the base price", async ({ page }) => {
		await gotoApp(page, "/");
		await venueCard(page, SEED.venue).click();
		await expect(page).toHaveURL(new RegExp(`/venues/${SEED.venueSlug}$`));

		const slots = slotButtons(page);
		await expect(slots).toHaveCount(4);
		for (const slot of await slots.all()) {
			await expect(slot).toContainText(/AED\s250/);
			await expect(slot).toBeEnabled();
		}
	});

	test("sends a guest who picks a slot to log in first", async ({ page }) => {
		await openVenue(page, SEED.venueSlug);
		await slotButton(page, "19:00").click();
		await expect(page).toHaveURL(
			new RegExp(`/apnaslot/login\\?redirect=.*venues.*${SEED.venueSlug}`),
		);
		await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
	});
});
