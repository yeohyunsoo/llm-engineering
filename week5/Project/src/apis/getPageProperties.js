// 2925319a-55b8-8027-baa4-fc8b515bce21 ; Sample Page ID

const { notion } = require("../utils/connectNotionClient");

async function getPageProperties(pageId) {
    // console.log("Getting Page Properties...")
    const pageProperties = await notion.pages.retrieve({ page_id: pageId });
    // console.log("Page Properties: ", pageProperties)
    // console.log("구분선 yayaya")
    // console.log(pageProperties.properties.title)
    return pageProperties.properties;
}

module.exports = { getPageProperties };