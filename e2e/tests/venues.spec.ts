import { expect, test, type Page } from "../helpers/app";
import { cleanupTestVenues, generateVenueName, getList } from "../helpers";
import { gotoApp, selectOption } from "../helpers/ui";

const PREFIX = "E2E Test Venue";

async function fillNewVenue(page: Page, venueName: string, closesAt: string) {
	await gotoApp(page, "/manage/venues/new");
	await page.getByLabel("Venue name").fill(venueName);
	await page.getByLabel("Address").fill("1 Playwright Road");
	await page.getByLabel("City").fill("Dubai");
	await selectOption(page, page.getByRole("combobox").first(), "United Arab Emirates");
	await page.getByLabel("Resource name").fill("Turf A");
	await page.getByLabel(/Price per slot/).fill("250");
	await page.getByLabel("Closes at").fill(closesAt);
}

function venueRow(page: Page, venueName: string) {
	return page.getByTestId("venue-row").filter({ hasText: venueName });
}

test.describe("Publisher venues", () => {
	test.afterAll(async ({ request }) => {
		await cleanupTestVenues(request, PREFIX);
	});

	test("creates a draft venue, refusing hours that do not divide into slots", async ({
		page,
		request,
	}) => {
		const venueName = generateVenueName(PREFIX);
		await fillNewVenue(page, venueName, "22:30");
		await page.getByRole("button", { name: "Create venue" }).click();
		await expect(
			page.getByText(
				"Row 1: Monday is open for 270 minutes, which is 30 short of a whole 60-minute slot",
			),
		).toBeVisible();

		await page.getByLabel("Closes at").fill("22:00");
		await page.getByRole("button", { name: "Create venue" }).click();
		await expect(page).toHaveURL(/\/manage\/venues$/);
		await expect(venueRow(page, venueName)).toContainText("Draft");

		const created = await getList(request, "Venue", {
			fields: ["name"],
			filters: { venue_name: venueName },
		});
		expect(created).toHaveLength(1);
	});

	test("publishes a draft in place", async ({ page }) => {
		const venueName = generateVenueName(PREFIX);
		await fillNewVenue(page, venueName, "22:00");
		await page.getByRole("button", { name: "Create venue" }).click();
		await expect(page).toHaveURL(/\/manage\/venues$/);

		const row = venueRow(page, venueName);
		await row.getByRole("button", { name: "Publish" }).click();
		await expect(row).toContainText("Published");
		await expect(row.getByRole("button", { name: "Unlist" })).toBeVisible();
	});
});
