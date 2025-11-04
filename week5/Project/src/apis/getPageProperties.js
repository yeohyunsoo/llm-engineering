// 2925319a-55b8-8027-baa4-fc8b515bce21 ; Sample Page ID

const { notion } = require("../utils/connectNotionClient");
const { getPageIds } = require("./getPageIds");

async function getPageProperties(pageId) {
    // console.log("Getting Page Properties...")
    const pageProperties = await notion.pages.retrieve({ page_id: pageId });
    // console.log("Page Properties: ", pageProperties)
    // console.log("구분선 yayaya")
    // console.log(pageProperties.properties.title)
    const pageTitle = pageProperties.properties?.title?.title[0]?.plain_text ?? pageProperties.properties?.Title?.title[0]?.plain_text ?? "undefined";
    // console.log("pageTitle", pageTitle);
    return pageTitle
}

getPageProperties("2995319a-55b8-8072-a282-e2a14f0dbde0").then((result) => console.log("done", result));

module.exports = { getPageProperties };