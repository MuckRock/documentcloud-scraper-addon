"""
This add-on will monitor a website for documents and upload them to your DocumentCloud account
"""


import cgi
import mimetypes
import os
import sys
import urllib.parse as urlparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from documentcloud.addon import AddOn
from documentcloud.constants import BULK_LIMIT
from documentcloud.toolbox import grouper, requests_retry_session
from ratelimit import limits, sleep_and_retry
from clouddl import GDRIVE_URL, grab


DOC_CUTOFF = 10
MAX_NEW_DOCS = 100
MAX_NEW_GOOGLE_DOCS = 30
FILECOIN_ID = 104
HEADER = {
    "User-Agent": "DocumentCloud Scraper Add-On: Contact us at info@documentcloud.org"
}


class Document:
    """Class to hold information about scraped documents"""

    def __init__(self, url, headers):
        self.url = url
        self.headers = headers

    @property
    def title(self):
        """ Grabs title """
        title = self.title_from_headers()
        if title:
            return title
        return self.title_from_url()

    def title_from_headers(self):
        """ Grabs title from headers """
        if self.headers["content-disposition"] is None:
            return ""
        _, params = cgi.parse_header(self.headers["content-disposition"])
        filename = params.get("filename")
        if filename:
            root, _ext = os.path.splitext(filename)
            return root

        return ""

    def title_from_url(self):
        """Get the base name of the file to use as a title"""
        parsed_url = urlparse.urlparse(self.url)
        basename = os.path.basename(parsed_url.path)
        root, _ext = os.path.splitext(basename)
        return root

    @property
    def extension(self):
        """ Grabs extension type from url """
        if self.headers["content-type"] is None:
            return "pdf"
        content_type = cgi.parse_header(self.headers["content-type"])[0]
        extension = mimetypes.guess_extension(content_type)
        if extension:
            return extension.strip(".")
        return "pdf"

    # https://stackoverflow.com/questions/33049729/
    # how-to-handle-links-containing-space-between-them-in-python
    @property
    def fixed_url(self):
        """Fixes quoting of characters in file names to use with requests"""
        scheme, netloc, path, qs, anchor = urlparse.urlsplit(self.url)
        path = urlparse.quote(path, "/%")
        qs = urlparse.quote_plus(qs, ":&=")
        return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))


class Scraper(AddOn):
    """ DocumentCloud Scraper Add-On class """

    def __init__(self):
        super().__init__()
        self.base_netloc = None
        self.seen = set()
        self.new_docs = {}
        self.content_types = []
        self.total_new_doc_count = 0
        self.total_new_gdoc_count = 0
        self.project = None
        self.access_level = None
        self.site_data = {}

        os.makedirs("./out/", exist_ok=True)  # Ensure the directory exists

    def check_permissions(self):
        """The user must be a verified journalist to upload a document"""
        self.set_message("Checking permissions...")
        user = self.client.users.get("me")
        if not user.verified_journalist:
            self.set_message(
                "You need to be verified to use this add-on. Please verify your "
                "account."
            )
            sys.exit(1)

    def check_crawl(self, url, content_type):
        """Checks crawl depth of the site"""
        # check if it is from the same site
        _, netloc,_, _, _  = urlparse.urlsplit(url)
        if netloc != self.base_netloc:
            return False
        # do not crawl the same site more than once
        if url in self.seen:
            return False
        self.seen.add(url)
        return content_type == "text/html"

    @sleep_and_retry
    @limits(calls=5, period=1)
    def get_headers(self, url):
        """ Gets response headers from a url """
        print("getting headers", url)
        scheme, _, _, _,_ = urlparse.urlsplit(url)
        if scheme not in ["http", "https"]:
            return {"content-type": None, "content-disposition": None, "etag": None}
        try:
            resp = requests_retry_session().head(
                url, allow_redirects=True, timeout=10, headers=HEADER
            )
        except requests.exceptions.RequestException:
            return {"content-type": None, "content-disposition": None, "etag": None}
        return {
            "content-type": resp.headers.get("content-type"),
            "content-disposition": resp.headers.get("content-disposition"),
            "etag": resp.headers.get("etag"),
        }

    def get_content_type(self, headers):
        """ Gets content type from headers from the site """
        if headers["content-type"] is None:
            return ""
        return cgi.parse_header(headers["content-type"])[0]

    @sleep_and_retry
    @limits(calls=5, period=1)
    def scrape(self, site, depth=0):
        """Scrape the site for new documents"""
        print(self.site_data)
        print(f"Scraping {site} (depth {depth})")
        resp = requests_retry_session().get(site, headers=HEADER)
        if depth == 0:
            resp.raise_for_status()
        elif resp.status_code != 200:
            print(f"{site} returned code {resp.status_code}")
            return
        soup = BeautifulSoup(resp.text, "html.parser")
        docs = []
        sites = []
        now = datetime.now().isoformat()

        for link in soup.find_all("a"):
            new = False
            href = link.get("href")
            if href is None:
                continue
            full_href = urlparse.urljoin(resp.url, href)

            if full_href not in self.site_data:
                headers = self.get_headers(full_href)
                self.site_data[full_href] = {"headers": headers, "first_seen": now}
                new = True
            else:
                headers = self.site_data[full_href].get("headers")
                if not headers:
                    headers = self.get_headers(full_href)
                    self.site_data[full_href]["headers"] = headers
                else:
                    current_etag = headers.get("etag")
                    print(f"Current etag: {current_etag}")
                    previous_etag = self.site_data[full_href].get("etag")
                    print(f"Previous etag: {previous_etag}")
                    if previous_etag != current_etag and current_etag is not None:
                        print("Etag updated")
                        new = True
            self.site_data[full_href]["etag"] = current_etag
            self.site_data[full_href]["last_seen"] = now

            content_type = self.get_content_type(headers)
            print("link", href, content_type)
            # if this is a document type, store it
            if new:
                if self.total_new_gdoc_count >= MAX_NEW_GOOGLE_DOCS:
                    break
                if GDRIVE_URL in full_href:
                    self.set_message(f"Processing Google Drive URL: {full_href}")
                    try:
                        if grab(href, "./out"):
                            self.set_message(f"Captured Google Drive file: {full_href}")
                            self.total_new_gdoc_count += 1
                    except:
                        # If there is gdrive site that fails to download,
                        # we can remove it from the seen list and move on.
                        self.site_data.pop(full_href)
            if content_type in self.content_types:
                # track when we first and last saw this document
                # on this page
                if new:
                    # only download if haven't seen before
                    print("found new docs", full_href)
                    docs.append(Document(full_href, headers))
                    self.total_new_doc_count += 1
                # stop looking for new documents if we hit the max
                if self.total_new_doc_count >= MAX_NEW_DOCS:
                    break
            elif depth < self.data.get("crawl_depth", 0):
                # if not a document, check to see if we should crawl
                if self.check_crawl(full_href, content_type):
                    sites.append(full_href)

        self.new_docs[site] = docs
        doc_ids = []
        for doc_group in grouper(docs, BULK_LIMIT):
            # filter out None's from grouper padding
            doc_group = [d for d in doc_group if d]
            doc_group = [
                {
                    "file_url": d.fixed_url,
                    "source": f"Scraped from {site}",
                    "title": d.title,
                    "projects": [self.project],
                    "original_extension": d.extension,
                    "access": self.access_level,
                }
                for d in doc_group
            ]
            # do a bulk upload
            if not self.data.get("dry_run"):
                resp = self.client.post("documents/", json=doc_group)
                doc_ids.extend(d["id"] for d in resp.json())

        # Upload all of the uploadable Google Drive content
        self.client.documents.upload_directory(
            "./out", access=self.access_level, projects=[self.project]
        )

        # store event data here in case we time out, we don't repeat the same files next time
        self.store_event_data(self.site_data)
        if self.data.get("filecoin") and doc_ids:
            self.client.post(
                "addon_runs/",
                json={"addon": FILECOIN_ID, "parameters": {}, "documents": doc_ids},
            )

        if (
            self.total_new_doc_count >= MAX_NEW_DOCS
            or self.total_new_gdoc_count >= MAX_NEW_GOOGLE_DOCS
        ):
            return

        # recurse on sites we want to crawl
        for site_ in sites:
            self.scrape(site_, depth=depth + 1)

    def send_notification(self, subject, message):
        """Send notifications via slack and email"""
        self.send_mail(subject, message)
        if self.data.get("slack_webhook"):
            requests_retry_session().post(
                self.data.get("slack_webhook"), json={"text": f"{subject}\n\n{message}"}
            )

    def send_scrape_message(self):
        """Alert on all new documents"""
        if not self.data.get("notify_all"):
            return

        msg = []
        for site, docs in self.new_docs.items():
            if docs:
                msg.append(f"\n\nFound {len(docs)} new documents from {site}\n")
                msg.extend(d.fixed_url for d in docs[:DOC_CUTOFF])
                if len(docs) > DOC_CUTOFF:
                    msg.append(f"Plus {len(docs) - DOC_CUTOFF} more documents")
        if msg:
            self.send_notification(
                f"Found new documents from {self.data['site']}", "\n".join(msg)
            )

    def alert(self):
        """Run queries for the keywords to generate additional alerts"""
        for keyword in self.data.get("keywords", "").split(","):
            if not keyword:
                continue
            query = f"+project:{self.project} {keyword} created_at:[NOW-1HOUR TO *]"
            documents = self.client.documents.search(query)
            documents = list(documents)
            if documents:
                message = [
                    f"Documents containing {keyword} found at {datetime.now()} "
                    f"from {self.data['site']}"
                ]
                message.extend(
                    [f"{d.title} - {d.canonical_url}" for d in documents[:DOC_CUTOFF]]
                )
                if len(documents) > DOC_CUTOFF:
                    message.append(f"Plus {len(documents) - DOC_CUTOFF} more documents")
                self.send_notification(
                    f"New documents found for: {keyword} from {self.data['site']}",
                    "\n".join(message),
                )

    def main(self):
        """Checks that you can run the Add-On, scrapes the site, sends alert"""
        self.check_permissions()

        # grab the base of the URL to stay on site during crawling
        _scheme, netloc, _path, _qs, _anchor = urlparse.urlsplit(self.data["site"])
        self.base_netloc = netloc
        self.seen = set()
        self.new_docs = {}
        self.content_types = [
            mimetypes.types_map[f]
            for f in self.data.get("filetypes", ".pdf").split(",")
        ]
        self.total_new_doc_count = 0
        self.total_new_gdoc_count = 0

        project = self.data["project"]
        # if project is an integer, use it as a project ID
        try:
            self.project = int(project)
        except ValueError:
            project, created = self.client.projects.get_or_create_by_title(project)
            self.project = project.id

        self.access_level = self.data["access_level"]
        self.site_data = self.load_event_data()
        if self.site_data is None:
            self.site_data = {}
        self.set_message("Scraping the site...")
        self.scrape(self.data["site"])
        self.set_message("Scraping complete!")
        self.store_event_data(self.site_data)
        self.send_scrape_message()

        self.alert()


if __name__ == "__main__":
    mimetypes.init()
    Scraper().main()
