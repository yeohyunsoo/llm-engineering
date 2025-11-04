// 2925319a-55b8-8027-baa4-fc8b515bce21 ; Sample Page ID

const { notion } = require("../utils/connectNotionClient");
const { getPageProperties } = require("./getPageProperties");

// blockId 아래 모든 블록을 재귀적으로 수집
async function getAllBlocks(pageId) { //최상위의 Block인 PageId로 시작해서 모든 블록을 재귀적으로 수집
    let allBlockIds = [];
    let parentBlockIds = [];

    try {
        const raw = await notion.blocks.children.list({ block_id: pageId });
        for (let i = 0; i < raw.results.length; i++) {
        parentBlockIds.push(raw.results[i].id);
        }
        console.log("Parent Block IDs: ", parentBlockIds);
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
                    console.log("이것이 컨텐츠가 맞는가?: ", richText);

                    if (raw.results[j].has_children) {
                        console.log("yayaya");
                    }
                    else {
                        console.log(" ");
                    }
                }

                if (!raw.has_more) {
                    break;
                }

                cursor = raw.next_cursor || undefined;
            }

            allBlockIds.push({ parentBlockId: parentBlockIds[i], childBlockIds });
        }

        console.log("All Block IDs: ", allBlockIds);
    } catch (err) {
        throw err;
    }
}


async function getPageContents(pageId) {
  const pageTitle = await getPageProperties(pageId);
  console.log("Page Title:", pageTitle);

  const blocks = await getAllBlocks(pageId);
  return { pageId, pageTitle, blocks };
}

// 샘플 실행
getPageContents("2925319a-55b8-8027-baa4-fc8b515bce21")
  .then(() => console.log("done"))
  .catch(console.error);