// 2925319a-55b8-8027-baa4-fc8b515bce21 ; Sample Page ID

const { notion } = require("../utils/connectNotionClient");

async function getPageProperties(pageId) {
    // console.log("Getting Page Properties...")
    const pageProperties = await notion.pages.retrieve({ page_id: pageId });
    // console.log("pageProperties", pageProperties);
    // console.log("Page Properties: ", pageProperties)
    // console.log("구분선 yayaya")
    // console.log(pageProperties.properties.title)
    const properties = pageProperties.properties ?? {};
    const titleProperty = Object.values(properties).find((prop) => prop?.type === "title");

    const pageTitle = (titleProperty?.title ?? [])
        .map((fragment) => fragment?.plain_text ?? fragment?.text?.content ?? "")
        .join("")
        .trim() || "undefined";

    console.log("pageTitle: ", pageTitle);

    return pageTitle;
}

/* TEST CODE */
// let pageId = "22a5319a-55b8-801b-8471-f9558979b06c";
// getPageProperties(pageId)

module.exports = { getPageProperties };