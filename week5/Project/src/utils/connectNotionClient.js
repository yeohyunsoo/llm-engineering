const path = require("path");

require("dotenv").config({
  path: path.resolve(__dirname, "../../.env"),
});

const { Client } = require("@notionhq/client");

const notion = new Client({ auth: process.env?.NOTION_API_KEY || "" });

module.exports = { notion };