const fs = require("fs");
const path = require("node:path");
const { getPageContents } = require("./apis/getPageContents");
const { getPageIds } = require("./apis/getPageIds");

(async () => {
  const pageIds = await getPageIds();
  const exportDir = path.join(__dirname, "../exports/pages");
  fs.mkdirSync(exportDir, { recursive: true });

  for (const pageId of pageIds) {
    const [pageContents] = await getPageContents(pageId);

    const rawTitle = pageContents?.metadata?.pageTitle || pageId;
    const safeTitle = rawTitle.replace(/[<>:"/\\|?*\x00-\x1F]/g, "_").slice(0, 80);
    const filePath = path.join(exportDir, `${safeTitle}.json`);

    fs.writeFileSync(filePath, JSON.stringify(pageContents, null, 2));
    console.log("exported:", filePath);
  }
})();