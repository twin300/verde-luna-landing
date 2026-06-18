import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import http from "node:http";
import { once } from "node:events";

const port = 4173;
const baseUrl = `http://127.0.0.1:${port}`;

function waitForServer(url, timeout = 30000) {
  const started = Date.now();

  return new Promise((resolve, reject) => {
    const attempt = () => {
      http
        .get(url, (response) => {
          response.resume();
          resolve();
        })
        .on("error", (error) => {
          if (Date.now() - started > timeout) {
            reject(error);
            return;
          }

          setTimeout(attempt, 250);
        });
    };

    attempt();
  });
}

const server = spawn("npx", ["vite", "preview", "--host", "127.0.0.1", "--port", String(port)], {
  shell: true,
  stdio: "inherit",
});

server.on("error", (error) => {
  throw error;
});

try {
  await waitForServer(baseUrl);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } });
  await page.goto(baseUrl, { waitUntil: "networkidle" });

  await page.locator("h1").filter({ hasText: "Искусство" }).waitFor();
  await page.locator("#booking-title").waitFor();

  const heroBox = await page.locator(".hero").boundingBox();
  if (!heroBox || heroBox.height < 620) {
    throw new Error("Hero section is shorter than expected on desktop.");
  }

  const galleryCount = await page.locator(".gallery-item").count();
  if (galleryCount !== 5) {
    throw new Error(`Expected 5 gallery images, received ${galleryCount}.`);
  }

  await page.locator(".gallery-item").first().click();
  await page.locator(".lightbox[open]").waitFor();
  await page.keyboard.press("Escape");

  await page.locator(".booking-form button").click();
  await page.locator("[data-form-note]").filter({ hasText: "Подобрали варианты" }).waitFor();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator("[data-menu-toggle]").click();
  await page.locator("[data-mobile-menu].is-open").waitFor();

  const mobileHero = await page.locator(".hero h1").boundingBox();
  if (!mobileHero || mobileHero.width > 360) {
    throw new Error("Mobile hero title overflows the viewport.");
  }

  await browser.close();
} finally {
  server.kill();
  await Promise.race([once(server, "exit"), new Promise((resolve) => setTimeout(resolve, 1000))]);
}
