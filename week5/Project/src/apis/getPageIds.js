const { notion } = require("../utils/connectNotionClient");


async function getPageIds() {
    console.log("Getting Page IDs...")
    const pageIds = [];
    let cursor = undefined;
        
    while (true) {
        const res = await notion.search({
        start_cursor: cursor,
        page_size: 100,
        filter: { property: "object", value: "page" },
        });

        for (const item of res.results) {
        pageIds.push(item.id);
        }

        if (!res.has_more) break;
        cursor = res.next_cursor;
    }

    console.log("Retrieved page IDs: ", pageIds)
    return pageIds;
}

module.exports = { getPageIds };