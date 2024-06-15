# CatGPT 

CatGPt is a Telegram bot that integrates with OpenAI's api for users who like to use OpenAI in Telegram.

### Features
* Multiple topics
  
 * Multiple endpoints

 * Powerful and easy to use


 ### Commands

 * /key `{access key}`

   The `access key` is the key configured in the config file `config.json`

   You will be enrolled into the system if a correct access key is supplied

 * **/list**

   Display all topics in the **current chat window**. This indicates that the chat histories for Private Chats, Channels, and Groups are kept separate.

   ![display all topics](assets/list.png)

   You can click a button to view the next step you can take.

   ![clicked](assets/list_clicked.png)

   As you see, you can share, download, or delete the topic on which you clicked

 * /new `[title]`

   Create a new topic with the given title. 

   For example, using `/new english learning` will create a topic with the title `english learning`. A default title will be used if you do not supply a specific title.

   ![new topic](assets/new.png)

* **/topic** `[share | download | title]`

  There are three optional operations that you can use to perform some task quickly.

  * `share`

    Use `/topic share` to share the topic directly without a confirmation operation

  * `download`

    Use `/topic download` to download the topic directly without a confirmation operation.
	  
  * **other characters**

    Any other characters will be treated as the title, and the topic's title will be updated."
	

​		![operations](assets/dl_share.png)

​	if none of the operations is supplied, it displays the chat history.

​		![operations](assets/topic.png)

* **/profile**

  Display user's profile (including the current endpoint, model, and topic)

* **/endpoints** `[endpoint name]`

  Display all endpoints.

​	You can also swtich to an endpoint directly with the command `/endpoints [your endpoint name]`

* **/models** `[model name]`

  Display all the support models of the endpoint.

  Use `/models [model name]` to switch to it directly. Otherwise, the list of models will be displayed in the  chat window.

  There are some short names that map to the full names of those models

  ```json
  {
      "gpt4": "gpt-4",
      "gpt4_32k": "gpt-4-32k",
      "gpt4_16k": "gpt-4-16k",
      "0314": "gpt-4-0314",
      "0613": "gpt-4-0613",
      "1106": "gpt-4-1106-preview",
      "0125": "gpt-4-0125-preview",
      "0409": "gpt-4-turbo-2024-04-09",
      "gpt4o": "gpt-4o",
    	"4o": "gpt-4o"
  }
	```
	For example, you can use `/models 0409` to switch to the model `gpt-4-turbo-2024-04-09` directly.
	
	![](assets/model.png)
	
	It displays all the models if a invalid short name is provided.
	
* **/revoke**

  Removes the latest messages from the chat window and chat histories so that you can have another attempt.

* **/clear** `[history | all]`

  Clears all the messages of the topic
  
  * `history`: Only clear the chat history, messages are remained in the chat window.
  * `all`: Clears both chat history and messages.



### Configuration

* `tg_token`: the token of your telegram bot

* `access_key`: access key

* `proxy`: a http or https proxy server. the chatbot will run behind the proxy server if it's supplied

* `endpoinds`: your endpoints

  endpint:

  * `name`: endpoint name
  * `api_url`: api url. e.g. `https://api.openai.com/v1`
  * `secret_key`: secret_key
  * `models`: list of supporting models for this endpoint
  * `generate_title`: If `true`, the endpoint will be used to automatically generate titles for topics that lack one, based on their chat history."

* `share`: a share provider(only supports github c)

```json
{
  "tg_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "access_key": "Specify Access Key to use this bot",
  "proxy": "http://proxy:port",
  "share": {
    "repo": "github repo name",
    "owner": "github username",
    "token": "github access token"
  },
  "endpoints": [
    {
      "name": "endpoint_1",
      "api_url": "https://api.openai.com",
      "secret_key": "YOUR_API_KEY",
      "models": [
        "gpt-4o",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-0125-preview",
        "gpt-4-1106-preview",
        "gpt-4"
      ]
    }
  ]
}
```



### How to create a telegram bot

1. Talk to [BotFather](https://t.me/BotFather)
2. Use the command `/newbot` to create a new bot
3. Follows the guideline of BotFather and then get the access token of your bot
