
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

### 3) Run the Add-On from within DocumentCloud
Click on the Add-Ons dropdown menu -> "Browse All Add-Ons" -> "RSS Document Fetcher" -> Click the inactive button to mark the Add-On as active and finally hit Done. Click on the Add-Ons dropdown menu once more and click on the RSS Document Fetcher which will now be active. 

If succesful, the Add-On will grab all the documents it can pull from the site, load them into DocumentCloud, and then send you an email. It will now run hourly and will only alert you if it pulls new documents, with a second alert highlighting any documents that meet your key terms.

This is a relatively simple Add-On, but one of the powerful things about this approach is that it can be mixed and matched with other tools. Once your comfortable with the basics, [you can explore other example Add-Ons](https://www.documentcloud.org/help/add-ons/) that let you automatically extract data, use machine learning to classify documents into categories, and more. [Subscribe to the DocumentCloud newsletter](https://muckrock.us2.list-manage.com/subscribe?u=74862d74361490eca930f4384&id=89227411b1) to get more examples of code and opportunities to get help building out tools that help your newsroom needs.

