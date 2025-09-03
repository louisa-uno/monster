import os
from datetime import datetime, timedelta

import pytz
import requests
from discord_webhook import DiscordEmbed, DiscordWebhook
from lxml import html
from misskey import Misskey

cities = [
    {"city": "Berlin", "lat": 52.520008, "lng": 13.404954, "plz": "10117"},
    {"city": "Hamburg", "lat": 53.575320, "lng": 10.015340, "plz": "20095"},
    {"city": "Munich", "lat": 48.137430, "lng": 11.575490, "plz": "80331"},
    {"city": "Cologne", "lat": 50.937531, "lng": 6.960279, "plz": "50667"},
    {"city": "Frankfurt am Main", "lat": 50.110924, "lng": 8.682127, "plz": "60311"},
    {"city": "Stuttgart", "lat": 48.783333, "lng": 9.183333, "plz": "70173"},
    {"city": "Düsseldorf", "lat": 51.227741, "lng": 6.773456, "plz": "40213"},
    {"city": "Dortmund", "lat": 51.513587, "lng": 7.465298, "plz": "44135"},
    {"city": "Essen", "lat": 51.455643, "lng": 7.011555, "plz": "45127"},
    {"city": "Leipzig", "lat": 51.339695, "lng": 12.373075, "plz": "04109"},
    {"city": "Bremen", "lat": 53.079296, "lng": 8.801694, "plz": "28195"},
    {"city": "Dresden", "lat": 51.050409, "lng": 13.737262, "plz": "01067"},
    {"city": "Hanover", "lat": 52.375892, "lng": 9.732010, "plz": "30159"},
    {"city": "Nuremberg", "lat": 49.452103, "lng": 11.076665, "plz": "90402"},
    {"city": "Duisburg", "lat": 51.434407, "lng": 6.762329, "plz": "47051"},
    {"city": "Bochum", "lat": 51.481845, "lng": 7.216236, "plz": "44787"},
    {"city": "Wuppertal", "lat": 51.256213, "lng": 7.150764, "plz": "42103"},
    {"city": "Bielefeld", "lat": 52.030228, "lng": 8.532471, "plz": "33602"},
    {"city": "Bonn", "lat": 50.737430, "lng": 7.098207, "plz": "53111"},
    {"city": "Münster", "lat": 51.960665, "lng": 7.626135, "plz": "48143"},
]
offers = {}
for city in cities:
    s = requests.Session()
    
    url = 'https://www.kaufda.de/Angebote/Monster-Energy'
    headers = {"User-Agent": "Mozilla/5.0"}
    cookies = {'cookies_are': f'__gsas=ID=; location=%7B%22lat%22%3A{city["lat"]}%2C%22lng%22%3A{city["lng"]}%2C%22city%22%3A%22%22%2C%22cityUrlRep%22%3A%22%22%2C%22zip%22%3A%22{city["plz"]}%22%7D'}
    
    response = s.request("GET", url, headers=headers, cookies=cookies)
    response.raise_for_status()
    doc = html.fromstring(response.content)

    nodes = doc.xpath('//*[@id="OfferGrid"]/div/div')

    for node in nodes:
        product_name = node.xpath('.//div[@class="mt-2"]/p[1]/text()')
        price = node.xpath('.//p[contains(@class,"text-primary")]/text()')
        original_price = node.xpath('.//span[contains(@class,"line-through")]/text()')
        retailer = node.xpath('.//div[@class="mt-2"]/p[3]/text()')
        
        product_name = product_name[0].strip() if product_name else None
        price = float(price[0].strip().replace("ab ", "").replace('€', '').replace(",", ".")) if price else None
        original_price = float(original_price[0].strip().replace('€', '').replace(",", ".")) if original_price else None
        retailer = retailer[0].strip() if retailer else None
        
        if not (product_name and price and retailer):
            continue
        
        # if offer retailer doesnt exist or price is lower than existing offer, add/update it
        if not retailer in offers or price < offers[retailer]["price"]:
            offers[retailer] = {"product_name": product_name, "price": price, "original_price": original_price}

# Sort offers by price
offers = dict(sorted(offers.items(), key=lambda item: item[1]['price']))

# Prepare description
description = ""
for retailer in offers:
    offer = offers[retailer]
    if 'monster' in offer['product_name'].lower() and offer['price'] < 1.3:
        description += f"- {retailer}: {offer['price']} €\n"

print(description)

# Get current week range
german_tz = pytz.timezone('Europe/Berlin')
now = datetime.now(german_tz)
monday = now - timedelta(days = now.weekday())
sunday = monday + timedelta(days = 6)
date_range = f"{monday.day:02}.{monday.month:02}.{monday.year} - {sunday.day:02}.{sunday.month:02}.{sunday.year}"

# Prepare messages
title = "Monster Energy Angebote diese Woche"
discord_title = title
discord_description = description + date_range
misskey_description = title + "\n" + description + "<small>" + date_range + "</small>"

try:
    # Send to Discord
    discord_webhook = os.environ['DISCORD_WEBHOOK']
    webhook = DiscordWebhook(url=discord_webhook)
    embed = DiscordEmbed(title=discord_title, description=discord_description, color="55d600")
    webhook.add_embed(embed)
    response = webhook.execute()
    print("Sent discord webhook with status code: " + str(response.status_code))
except KeyError:
    print("DISCORD_WEBHOOK environment variable not set, skipping Discord notification.")

# Send to Misskey
try:
    misskey_token = os.environ['MISSKEY_TOKEN']
    mk = Misskey("mk.absturztau.be", i=misskey_token)
    mk.notes_create(
        text=misskey_description 
    )
    print("Posted to Misskey")
except KeyError:
    print("MISSKEY_TOKEN environment variable not set, skipping Misskey notification.")
