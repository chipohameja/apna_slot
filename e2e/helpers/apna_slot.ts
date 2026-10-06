import { APIRequestContext, Page } from "@playwright/test";
import { createDoc, getList, updateDoc } from "./frappe";

/** Seeded by `apna_slot.e2e_seed.setup_e2e_data`. */
export const SEED = {
	publisher: "E2E Sports",
	venue: "E2E Sports Arena",
	venueSlug: "e2e-sports-arena",
	customer: "customer@example.com",
} as const;

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export interface Venue {
	name: string;
	venue_name: string;
	slug: string;
	status: string;
	publisher: string;
}

export interface TestVenue {
	venue: Venue;
	resource: string;
}

export interface MethodResult<T = unknown> {
	status: number;
	data: T;
	message: string;
}

/** Generate a unique venue name for tests. */
export function generateVenueName(prefix = "E2E Test Venue"): string {
	const random = Math.random().toString(36).substring(2, 8);
	return `${prefix} ${Date.now()}-${random}`;
}

/** The seeded publisher's docname. */
export async function seedPublisher(request: APIRequestContext): Promise<string> {
	const [publisher] = await getList<{ name: string }>(request, "Publisher", {
		fields: ["name"],
		filters: { publisher_name: SEED.publisher },
		limit: 1,
	});
	if (!publisher) throw new Error(`Run apna_slot.e2e_seed.setup_e2e_data: no ${SEED.publisher}`);
	return publisher.name;
}

/**
 * A published venue with one resource, open 18:00–22:00 at AED 250 a slot.
 * Specs that take slots book on their own venue, so a retry never finds its slot gone.
 */
export async function createTestVenue(
	request: APIRequestContext,
	venueName = generateVenueName(),
): Promise<TestVenue> {
	const draft = await createDoc<Venue>(request, "Venue", {
		publisher: await seedPublisher(request),
		venue_name: venueName,
		address_line_1: "1 Playwright Road",
		city: "Dubai",
		country: "United Arab Emirates",
		timezone: "Asia/Dubai",
	});
	const resource = await createDoc<{ name: string }>(request, "Bookable Resource", {
		venue: draft.name,
		resource_name: "Turf A",
		slot_duration_minutes: "60",
		base_price: 250,
		weekly_schedule: DAYS.map((day) => ({
			day_of_week: day,
			opens_at: "18:00:00",
			closes_at: "22:00:00",
		})),
	});
	const venue = await updateDoc<Venue>(request, "Venue", draft.name, { status: "Published" });
	return { venue, resource: resource.name };
}

/**
 * Unlist test venues matching a name pattern. Their bookings are the ledger's
 * history, so they stay; unlisting keeps the home page from growing every run.
 */
export async function cleanupTestVenues(
	request: APIRequestContext,
	namePattern = "E2E Test Venue",
): Promise<void> {
	const venues = await getList<Venue>(request, "Venue", {
		fields: ["name"],
		filters: { venue_name: ["like", `${namePattern}%`], status: "Published" },
		limit: 100,
	});
	for (const venue of venues) {
		try {
			await updateDoc(request, "Venue", venue.name, { status: "Unlisted" });
		} catch (error) {
			console.warn(`Failed to unlist ${venue.name}:`, error);
		}
	}
}

/**
 * POST a whitelisted method from inside the page, as whoever the page is logged
 * in as. Returns the status rather than throwing, so a spec can assert a refusal.
 */
export async function postAsPage<T = unknown>(
	page: Page,
	method: string,
	args: Record<string, unknown>,
): Promise<MethodResult<T>> {
	return page.evaluate(
		async ({ method, args }) => {
			const response = await fetch(`/api/v2/method/${method}`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					"X-Frappe-CSRF-Token": (window as unknown as { csrf_token: string }).csrf_token,
				},
				body: JSON.stringify(args),
			});
			const body = await response.json();
			return {
				status: response.status,
				data: body.data,
				message: body.errors?.[0]?.message ?? "",
			};
		},
		{ method, args },
	);
}
