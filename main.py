"""
This add-on will monitor a website for documents and upload them to your DocumentCloud account
"""


import cgi
import json
import mimetypes
import os
import urllib.parse as urlparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from documentcloud.addon import AddOn
from documentcloud.constants import BULK_LIMIT
from documentcloud.toolbox import grouper, requests_retry_session
from ratelimit import limits, sleep_and_retry

DOC_CUTOFF = 10
MAX_NEW_DOCS = 100
FILECOIN_ID = 104


class Document:
    """Class to hold information about scraped documents"""

    def __init__(self, url, headers):
        self.url = url
        self.headers = headers

    @property
    def title(self):
        title = self.title_from_headers()
        if title:
            return title
        return self.title_from_url()

    def title_from_headers(self):
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
    def check_permissions(self):
        """The user must be a verified journalist to upload a document"""
        self.set_message("Checking permissions...")
        user = self.client.users.get("me")
        if not user.verified_journalist:
            self.set_message(
                "You need to be verified to use this add-on. Please verify your "
                "account here: https://airtable.com/shrZrgdmuOwW0ZLPM"
            )
            self.send_mail(
                "You must verify your account to use the Scraper Add-On",
                "You need to be verified to use the scraper add-on. Please verify your "
                "account here: https://airtable.com/shrZrgdmuOwW0ZLPM",
            )
            sys.exit(1)

    def check_crawl(self, url, content_type):
        # check if it is from the same site
        scheme, netloc, path, qs, anchor = urlparse.urlsplit(url)
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
        print("getting headers", url)
        scheme, netloc, path, qs, anchor = urlparse.urlsplit(url)
        if scheme not in ["http", "https"]:
            return {"content-type": None, "content-disposition": None}
        try:
            resp = requests_retry_session().head(url, allow_redirects=True, timeout=10)
        except requests.exceptions.RequestException:
            return {"content-type": None, "content-disposition": None}
        return {
            "content-type": resp.headers.get("content-type"),
            "content-disposition": resp.headers.get("content-disposition"),
        }

    def get_content_type(self, headers):
        if headers["content-type"] is None:
            return ""
        return cgi.parse_header(headers["content-type"])[0]

    @sleep_and_retry
    @limits(calls=5, period=1)
    def scrape(self, site, depth=0):
        """Scrape the site for new documents"""
        print(f"Scraping {site} (depth {depth})")
        resp = requests_retry_session().get(site)
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
                new = False
            self.site_data[full_href]["last_seen"] = now

            content_type = self.get_content_type(headers)
            print("link", href, content_type)
            # if this is a document type, store it
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
                    "access": "public",
                }
                for d in doc_group
            ]
            # do a bulk upload
            if not self.data.get("dry_run"):
                resp = self.client.post("documents/", json=doc_group)
                doc_ids.extend(d["id"] for d in resp.json())
        # store event data here in case we time out, we don't repeat the same files next time
        self.store_event_data(self.site_data)
        if self.data.get("filecoin") and doc_ids:
            self.client.post(
                "addon_runs/",
                json={"addon": FILECOIN_ID, "parameters": {}, "documents": doc_ids},
            )

        if self.total_new_doc_count >= MAX_NEW_DOCS:
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

        project = self.data["project"]
        # if project is an integer, use it as a project ID
        try:
            self.project = int(project)
        except ValueError:
            project, created = self.client.projects.get_or_create_by_title(project)
            self.project = project.id

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
