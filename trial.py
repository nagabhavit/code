import requests
import threading
import glob
import os
from bs4 import BeautifulSoup
from time import sleep

### CONFIG ###
BASE_URL = "https://www.udemyfreebies.com"
categories_list = ['development', 'it-and-software']
rating_stars = 4.2
rating_people = 200
MAX_THREADS = 20
HEADERS = {"User-Agent": "Mozilla/5.0"}
#### END CONFIG ####

enrolled_urls = []
potential_urls = []

def url_is_new(url):
    return url not in enrolled_urls

def find_last_page(category):
    try:
        url = f"{BASE_URL}/course-category/{category}/"
        source = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(source.content, 'lxml')
        pagination = soup.find("ul", {"class": "theme-pagination"})
        pages = pagination.find_all("li") if pagination else []
        return int(pages[-2].text) + 1 if pages else 2
    except Exception as e:
        print(f"\n[!] Error finding last page for category {category}: {e}")
        return 2

def is_valid_coupon(element):
    button = element.find("a", {"class": "button-icon"})
    return button and "Expired" not in button.text

def get_udemy_link(element):
    try:
        intermediate_url = element.find("a", {"class": "button-icon"})['href']
        inter_page = requests.get(intermediate_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(inter_page.content, 'lxml')
        final_link = soup.find("a", {"class": "button-icon"})['href']
        return final_link
    except Exception as e:
        return None

def is_rate_valid(udemy_url):
    try:
        response = requests.get(udemy_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'lxml')

        rating = float(soup.find("span", {"data-purpose": "rating-number"}).text.strip())
        rating_text = soup.find("div", {"data-purpose": "rating"}).text.strip()
        people = int(rating_text.split("(")[1].split(" ")[0].replace(',', ''))

        return rating >= rating_stars and people >= rating_people
    except Exception as e:
        return False

def process_page(soup):
    for course in soup.find_all("div", {"class": "col-md-4 col-sm-6"}):
        if is_valid_coupon(course):
            url = get_udemy_link(course)
            if url and url_is_new(url) and is_rate_valid(url):
                potential_urls.append(url)
                enrolled_urls.append(url)  # update to prevent duplicates in same run
                print(f"\r{len(potential_urls)} valid courses found", end='', flush=True)

def check_category(category, last_page):
    for page in range(1, last_page):
        while threading.active_count() > MAX_THREADS:
            sleep(0.5)
        try:
            url = f"{BASE_URL}/course-category/{category}/{page}"
            response = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.content, 'lxml')
            threading.Thread(target=process_page, args=(soup,), daemon=True).start()
        except Exception as e:
            print(f"\n[!] Error loading category page {url}: {e}")
            continue

def scrape_all():
    print("Starting scrape...")
    for category in categories_list:
        last = find_last_page(category)
        check_category(category, last)

    while threading.active_count() > 1:
        sleep(1)

    print(f"\nScraping completed. {len(potential_urls)} new courses found.")

    with open("urls.txt", "a") as f:
        for url in potential_urls:
            f.write(url + "\n")

if __name__ == '__main__':
    if glob.glob("urls.txt"):
        with open("urls.txt") as f:
            enrolled_urls = f.read().splitlines()

    scrape_all()
