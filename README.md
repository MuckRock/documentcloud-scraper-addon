
# DocumentCloud Scraper and Alerting Add-On

This simple DocumentCloud scraper Add-On will monitor a given site for documents and upload them to your DocumentCloud account, alerting you to any documents that meet given keyword criteria.

Documents that are scraped are tracked in a data.json file which is checked in to the repository.  If you copy this template or fork this repository, you may want to delete that file before pointing the scraper to a new site.

## Getting started with your own document alert tool

**Important Note:** *Because of the way GitHub works, you might stumble upon these directions in a variety of directories. The canonical version lives at `https://github.com/MuckRock/documentcloud-scraper-cron-addon` so if you're on a different page and you're new to GitHub and DocumentCloud Add-Ons, we recommend going to that page for the latest instructions and most straight-forward flow. Down the road, you might want to build off other versions, but always check to make sure you trust and can verify the creators of the code.*

### 1) Create your accounts if needed

First, you'll need to have a verified MuckRock account. If you've ever uploaded documents to DocumentCloud before, you're already set. If not, [register a free account here](https://accounts.muckrock.com/accounts/signup/?intent=squarelet) and then [request verification here](https://airtable.com/shrZrgdmuOwW0ZLPM).

You'll also need a free GitHub account. [Register for it here](https://github.com/join) if you don't already have one.

### 2) Create a DocumentCloud project for your documents

Next, log in to DocumentCloud and create a new project to store the documents that your scraper grabs.

![An image of the project create button in DocumentCloud](https://user-images.githubusercontent.com/136939/159478474-53a770e5-a826-44f1-bb80-b1844bf4c263.png)

Click on your newly created project on the left-hand side of the screen, and note the numbers to the right of its name — this is the project ID, in this example, `207354`.

![Screen Shot 2022-03-22 at 8 08 11 AM](https://user-images.githubusercontent.com/136939/159478630-c6cbcb24-308c-4b0e-a42c-f10cf2653836.png)

### 3) Fork this template

Next, up above, click the green `Use this template` button above. It will take you to a new page, but will bring along a new version of these instructions with them so no need to keep this open in another tab. If you don't see the button above, make sure you're logged in to GitHub. If you're logged in, you can [click here instead](https://github.com/MuckRock/documentcloud-scraper-cron-addon/generate) and it will have the same effect.

![Screen Shot 2022-03-22 at 8 18 42 AM](https://user-images.githubusercontent.com/136939/159480367-f1589e96-726a-4d15-a468-2d68a969f359.png)

On the following page, if presented with an option choose either your personal account or an organizational one if you want to more easily share access with your colleagues to the underlying code, and name your repository something that will remind you what it's scraping, like "Dallas Daily Police Reports Alert" or "Springfield School Meeting Minutes Scraper."

Give it a helpful description — we like to include the URL to the DocumentCloud project so that people can find the actual data as well.

> A tool to monitor for and backup public records opinions issued by the Texas Attorney General. Search the documents here: https://www.documentcloud.org/app?q=%2Bproject%3Atexas-ag-foia-decisions-207375%20

Generally, you'll want to make the repository public. This will make it easier for others to build on your own work with their own scrapers, and you'll save money. These templates will work if private, but you'll have to pay for GitHub Actions, which are free for public repositories. If the repository is public, you can still make the underlying data private, although keep in mind that others will be able to see what it was able to pull in if they look closely at the code.

Leave "Include all branches" unchecked.

![Screen Shot 2022-03-22 at 8 46 08 AM](https://user-images.githubusercontent.com/136939/159485096-1877e6a7-0bb9-4c71-8bde-367865bba0f5.png)

### 4) Edit the configuration files

On your newly created GitHub repository, click the settings icon towards the top right of the main area:

![Screen Shot 2022-03-22 at 8 53 51 AM](https://user-images.githubusercontent.com/136939/159486465-f0158341-990e-43b5-b2ef-a7fd12eae9ad.png)

And then click "Secrets" and "Actions" under Secrets. Here's where you'll store your sensitive user data — passwords and other security information should **only** go here, or else it may be read by other people.

The page you should be at after clicking through the above should look like this:

![Screen Shot 2022-03-22 at 8 55 33 AM](https://user-images.githubusercontent.com/136939/159486787-71e8fa7f-f389-4231-b89d-2fe580e360bf.png)

Click "New Repository Secret" and you'll need to create two different secrets separately:

`DC_PASSWORD` and `DC_USERNAME`. The title of the secret should be that text exactly, with the body being your actual password or username. Other viewers of the repository will not be able to see this information — it's securely stored and transmitted from GitHub to DocumentCloud's servers.

![Screen Shot 2022-03-22 at 9 03 32 AM](https://user-images.githubusercontent.com/136939/159488115-d4c8a211-776a-498f-8112-01cad22db45e.png)

### 5) Optional Slack alerts

You can create a third secret, `SLACK_WEBHOOK`, if you'd like to get alerts sent to your Slack account. You'll probably neeed admin permissions to your Slack account. If you have them, [go here](
slack.com/apps/A0F7XDUAZ-incoming-webhooks?tab=more_info) and click "Add to Slack," then follow the prompts:

![Screen Shot 2022-03-22 at 9 09 15 AM](https://user-images.githubusercontent.com/136939/159489230-dfab5dfc-c9d7-4c4f-a00f-974f5c9b55a7.png)

You'll get a URL that looks like this:

<img width="721" alt="Screen Shot 2022-03-23 at 9 56 26 AM" src="https://user-images.githubusercontent.com/136939/159716228-0fa81b6e-ec4f-49f4-a895-91a88f62d671.png">

That's what you'll want to store in the `SLACK_WEBHOOK` secret.

### 6) Configure the scraper and alerts

Now it's time to point the scraper at the content we want to grab. From your repository (at the top of this page, if you've been following along the instructions), click `config.yaml` and then the pencil icon to edit the text:

![Screen Shot 2022-03-22 at 9 16 37 AM](https://user-images.githubusercontent.com/136939/159490436-e5351a6c-c912-466d-a03d-1682c1c41c2b.png)

Under `properties` in this text, look for `site` and put the URL you want scraped after `default:`

<img width="732" alt="Screen Shot 2022-03-22 at 10 42 28 AM" src="https://user-images.githubusercontent.com/136939/159508492-0abeb224-82b1-4438-b424-179107fe70c3.png">

Similarly, put the project you want documents stored in after the `default:` under `project:` 

<img width="711" alt="Screen Shot 2022-03-22 at 10 42 32 AM" src="https://user-images.githubusercontent.com/136939/159508431-677f1a6b-c070-4d7f-ae60-b786b4a02497.png">


To get alerts for when specific keywords are mentioned in the text, put those keywords under the "default" areas in the relevant section:

![Screen Shot 2022-03-22 at 9 21 58 AM](https://user-images.githubusercontent.com/136939/159491353-10c5d890-015e-4204-bd2d-efacb8a22227.png)

Finally, if you'd like the crawler to go through not just the primary URL you give it but other pages linked to from that page, increase the crawl depth from `1` to `2` or `3` — we don't recommend a higher number as the scraper is than likely to time out or run into issues.

![Screen Shot 2022-03-22 at 9 22 44 AM](https://user-images.githubusercontent.com/136939/159491775-46317a87-9a96-434f-a85f-f36ad9d55ec5.png)

Once you're done with all those edits, click "Commit changes" below the text field to save your updates.

### 7) Delete the old data.json file

data.json is where the scraper stores what it has and hasn't seen before. Since this is a fresh scraper, you'll want to delete that old data. From the main repository view, click into data.json similarly to how you click into config.yaml, but instead of clicking the pencil icon, click the trash can.

![Screen Shot 2022-03-22 at 9 28 09 AM](https://user-images.githubusercontent.com/136939/159492494-c61f96e9-57d8-4590-9572-b14351ccc4b4.png)

Click "Confirm changes."

### 8) Run the scraper

Now it's time to run the scraper for the first time. At the top of the repository (generally, this page) click "Actions" then "Run Add-On" then "Run Workflow" twice:

![Screen Shot 2022-03-22 at 9 42 17 AM](https://user-images.githubusercontent.com/136939/159495167-1c96e745-4cec-42a1-9b04-b740a60d9252.png)

If succesful, the Add-On will grab all the documents it can pull from the site, load them into DocumentCloud, and then send you an email. It will now run hourly and will only alert you if it pulls new documents, with a second alert highlighting any documents that meet your key terms.

This is a relatively simple Add-On, but one of the powerful things about this approach is that it can be mixed and matched with other tools. Once your comfortable with the basics, [you can explore other example Add-Ons](https://www.documentcloud.org/help/add-ons/) that let you automatically extract data, use machine learning to classify documents into categories, and more. [Subscribe to the DocumentCloud newsletter](https://muckrock.us2.list-manage.com/subscribe?u=74862d74361490eca930f4384&id=89227411b1) to get more examples of code and opportunities to get help building out tools that help your newsroom needs.

