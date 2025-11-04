const fs = require("fs");
const { getPageContents } = require("./apis/getPageContents");
const { getPageIds } = require("./apis/getPageIds");

(async () => {
    const pageIds = await getPageIds();
    
    // 디렉토리 생성
    fs.mkdirSync("./exports/pages", { recursive: true });
    
    for(let i = 0; i < pageIds.length; i++) {
        const pageContents = await getPageContents(pageIds[i]);
        console.log("ddfasdfdff", pageContents);
    }
})();