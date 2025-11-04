const { notion } = require("../utils/connectNotionClient");

async function getUsers(){
    console.log("Getting Users...")
    const response = await notion.users.list();
    console.log("Users: ", response);

    let users = [];
    for(i=0; i<response.results.length; i++){
        users.push({"id":response.results[i].id, "name":response.results[i].name});
    }
    console.log("Retrieved users: ",users)
    return users;
}

getUsers();