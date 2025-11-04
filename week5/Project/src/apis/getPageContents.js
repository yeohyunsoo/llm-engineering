// 2925319a-55b8-8027-baa4-fc8b515bce21 ; Sample Page ID

const { notion } = require("../utils/connectNotionClient");
const { getPageProperties } = require("./getPageProperties");

async function fetchBlockWithChildren(notion, block) {
    if (!block.has_children) return block;
  
    const children = [];
    let cursor;
  
    do {
      const { results, has_more, next_cursor } =
        await notion.blocks.children.list({
          block_id: block.id,
          start_cursor: cursor,
        });
  
      for (const child of results) {
        children.push(await fetchBlockWithChildren(notion, child));
      }
  
      cursor = has_more ? next_cursor : undefined;
    } while (cursor);
  
    return { ...block, children };
}

// blockId 아래 모든 블록을 재귀적으로 수집
async function getAllBlocks(pageId) { //최상위의 Block인 PageId로 시작해서 모든 블록을 재귀적으로 수집
    let pageRichText = [];
    let allBlockIds = [];
    let parentBlockIds = [];

    try {
        const raw = await notion.blocks.children.list({ block_id: pageId });
        for (let i = 0; i < raw.results.length; i++) {
        parentBlockIds.push(raw.results[i].id);
        }
        // console.log("Parent Block IDs: ", parentBlockIds);
    } catch (err) {
        throw err;
    }

    try {
        for (let i = 0; i < parentBlockIds.length; i++) {
            let cursor = undefined;
            let childBlockIds = [];

            while (true) {
                const raw = await notion.blocks.children.list({
                    block_id: parentBlockIds[i],
                    start_cursor: cursor,
                });

                for (let j = 0; j < raw.results.length; j++) {
                    childBlockIds.push(raw.results[j].id);
                    const blockType = raw.results[j].type;          // 예: "paragraph"
                    const blockData = raw.results[j][blockType];    // 해당 타입에 맞는 데이터 객체
                    const richText = blockData?.rich_text?.[0]?.text?.content ?? "";    // 일부 블록은 rich_text가 없을 수 있으니 안전하게 처리
                    pageRichText.push(richText);
                    // console.log("이것이 컨텐츠가 맞는가?: ", richText);

                    if (raw.results[j].has_children) {
                        // console.log("yayaya");
                        const child = await fetchBlockWithChildren(notion, raw.results[j].id);
                        // console.log("내가증손자다: ", child)
                        for(let k = 0; k < child.length; k++) {
                            childBlockIds.push(child[k].id);
                            const blockType = child[k].type;          // 예: "paragraph"
                            const blockData = child[k][blockType];    // 해당 타입에 맞는 데이터 객체
                            const richText = blockData?.rich_text?.[0]?.text?.content ?? "";  // 일부 블록은 rich_text가 없을 수 있으니 안전하게 처리
                            pageRichText.push(richText);
                        }
                    }
                    
                }

                if (!raw.has_more) {
                    break;
                }

                cursor = raw.next_cursor || undefined;
            }

            allBlockIds.push({ parentBlockId: parentBlockIds[i], childBlockIds });

        }

        // console.log("All Block IDs: ", allBlockIds);
    } catch (err) {
        throw err;
    }
    pageRichText = pageRichText.join("").trim();
    return pageRichText;
}


async function getPageContents(pageId) {
    let pageContents = [];
    const pageTitle = await getPageProperties(pageId);
//   console.log("Page Title:", pageTitle);

    const pageRichTexts = await getAllBlocks(pageId);
//   return { pageId, pageTitle, blocks };
    pageContents.push({metadata: {pageId: pageId, pageTitle: pageTitle}, contents: pageRichTexts});
    return pageContents;
}

// 샘플 실행
getPageContents("2925319a-55b8-8027-baa4-fc8b515bce21")
    .then((result) => console.log("done", result))
    .catch(console.error);

module.exports = { getPageContents };