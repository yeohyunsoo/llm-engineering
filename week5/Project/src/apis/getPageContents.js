// 2925319a-55b8-8027-baa4-fc8b515bce21 ; Sample Page ID

const { notion } = require("../utils/connectNotionClient");
const { getPageProperties } = require("./getPageProperties");

const UNSUPPORTED_CHILD_BLOCK_TYPES = new Set(["transcription"]);

async function fetchBlockTree(blockId) {
    const blocks = [];
    let cursor;

    do {
        let response;

        try {
            response = await notion.blocks.children.list({
                block_id: blockId,
                start_cursor: cursor,
            });
        } catch (error) {
            if (error?.code === "validation_error" && /transcription/i.test(error?.message ?? "")) {
                console.warn("transcription 블록은 하위 목록 조회가 지원되지 않아 건너뜁니다.", { blockId });
                break;
            }

            throw error;
        }

        const { results, has_more, next_cursor } = response;

        for (const block of results) {
            if (UNSUPPORTED_CHILD_BLOCK_TYPES.has(block.type)) {
                blocks.push({ ...block, children: [] });
                continue;
            }

            const children = block.has_children && block.type !== "child_page"
                ? await fetchBlockTree(block.id)
                : [];

            blocks.push({ ...block, children });
        }

        cursor = has_more ? next_cursor : undefined;
    } while (cursor);

    return blocks;
}

function getRichText(block) {
    const type = block.type;
    const data = block[type];

    const richTextTypes = new Set([
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
        "toggle",
        "quote",
        "callout",
        "synced_block",
        "table_row",
    ]);

    if (richTextTypes.has(type)) {
        return (data?.rich_text ?? [])
            .map((fragment) => fragment?.plain_text ?? fragment?.text?.content ?? "")
            .join("")
            .trim();
    }

    if (type === "child_page") {
        return data?.title ?? "";
    }

    return "";
}

function flattenBlocks(blocks) {
    const contents = [];

    for (const block of blocks) {
        const text = getRichText(block);
        if (text) {
            contents.push(text);
        }

        if (block.children?.length) {
            contents.push(...flattenBlocks(block.children));
        }
    }

    return contents;
}

async function getPageContents(pageId) {
    const pageTitle = await getPageProperties(pageId);
    const blocks = await fetchBlockTree(pageId);
    const pageRichTexts = flattenBlocks(blocks);

    return [{
        metadata: {
            pageId,
            pageTitle,
        },
        contents: pageRichTexts,
    }];
}

if (require.main === module) {
    getPageContents("2995319a-55b8-8072-a282-e2a14f0dbde0")
        .then((result) => console.log("done", result))
        .catch(console.error);
}

module.exports = { getPageContents };