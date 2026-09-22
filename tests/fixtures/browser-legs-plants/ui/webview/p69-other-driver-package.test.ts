import { test } from "node:test";
import puppeteer from "puppeteer";
test("p69", async () => { const b = await puppeteer.launch(); await b.close(); });
