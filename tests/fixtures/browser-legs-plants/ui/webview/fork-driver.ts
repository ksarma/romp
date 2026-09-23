import { firefox } from "playwright";
const b = await firefox.launch(); await b.close();
