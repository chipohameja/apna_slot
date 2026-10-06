import * as fs from "fs";
import * as path from "path";
import { expect, test as setup } from "@playwright/test";

const authFile = "e2e/.auth/customer.json";
const csrfFile = "e2e/.auth/customer-csrf.json";

/**
 * Customer authentication setup — runs once before customer tests.
 * Logs in as an Apna Slot Customer (a Website User with no publisher).
 */
setup("authenticate as customer", async ({ page }) => {
	const authDir = path.dirname(authFile);
	if (!fs.existsSync(authDir)) {
		fs.mkdirSync(authDir, { recursive: true });
	}

	const usr = process.env.CUSTOMER_USER || "customer@example.com";
	const pwd = process.env.CUSTOMER_PASSWORD || "admin";

	// Navigate to login page first to establish the domain context
	await page.goto("/login");
	await page.waitForLoadState("domcontentloaded");

	// Login via browser fetch (keeps cookies on the correct domain)
	const loginResult = await page.evaluate(
		async ({ usr, pwd }) => {
			const resp = await fetch("/api/method/login", {
				method: "POST",
				headers: { "Content-Type": "application/x-www-form-urlencoded" },
				body: `usr=${encodeURIComponent(usr)}&pwd=${encodeURIComponent(pwd)}`,
			});
			return { ok: resp.ok, status: resp.status };
		},
		{ usr, pwd },
	);
	expect(loginResult.ok).toBeTruthy();

	// Verify login succeeded
	const loggedUser = await page.evaluate(async () => {
		const resp = await fetch("/api/method/frappe.auth.get_logged_user");
		const data = await resp.json();
		return data.message as string;
	});
	expect(loggedUser).toBe(usr);
	console.log(`Customer authenticated as: ${loggedUser}`);

	// The SPA's boot data carries the session's CSRF token; a Website User has no desk to read it from
	await page.goto("/apnaslot", { waitUntil: "domcontentloaded" });
	const csrfToken = await page.evaluate(
		() => (window as unknown as { csrf_token?: string }).csrf_token,
	);

	if (csrfToken) {
		fs.writeFileSync(csrfFile, JSON.stringify({ csrf_token: csrfToken }));
		console.log("Customer CSRF token saved");
	}

	await page.context().storageState({ path: authFile });
});
