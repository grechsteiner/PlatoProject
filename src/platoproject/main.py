import asyncio
import json
import os

from scrapybara import Scrapybara
from undetected_playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def get_scrapybara_browser():
    client = Scrapybara(api_key=os.getenv("SCRAPYBARA_API_KEY"))
    instance = client.start_browser()
    return instance

async def retrieve_menu_items(instance, start_url: str) -> list[dict]:
    """
    :args:
    instance: the scrapybara instance to use
    url: the initial url to navigate to

    :desc:
    this function navigates to {url}. then, it will collect the detailed
    data for each menu item in the store and return it.

    (hint: click a menu item, open dev tools -> network tab -> filter for
            "https://www.doordash.com/graphql/itemPage?operation=itemPage")

    one way to do this is to scroll through the page and click on each menu
    item.

    determine the most efficient way to collect this data.

    :returns:
    a list of menu items on the page, represented as dictionaries
    """
    cdp_url = instance.get_cdp_url().cdp_url
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        page = await browser.new_page()

        await page.goto(start_url, wait_until="networkidle")
        await asyncio.sleep(5)

        menu_items = []
        num_accumulated_menu_items = 0
        accumulated_titles = set()

        while True:
            items = await page.query_selector_all('div[data-anchor-id="MenuItem"][data-testid="MenuItem"], div[data-testid="GenericItemCard"]')

            for item in items:
                try:
                    await item.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)

                    title_element = await item.query_selector('h3[data-telemetry-id="storeMenuItem.title"]')
                    title = await title_element.inner_text() if title_element else "Unknown"
                    title = title.strip()

                    if title in accumulated_titles:
                        continue 
                    accumulated_titles.add(title)

                    price_element = await item.query_selector('span[data-anchor-id="StoreMenuItemPrice"]')
                    price = await price_element.inner_text() if price_element else "Unknown"
                    price = price.strip()

                    description_element = await item.query_selector('span[data-telemetry-id="storeMenuItem.subtitle"]')
                    description = await description_element.inner_text() if description_element else "Unknown"
                    description = description.strip()

                    menu_items.append({
                        "title": title,
                        "price": price,
                        "description": description,
                    })

                except Exception as e:
                    pass

            # Scroll
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(2)

            # Break if we haven't found any new items
            if len(menu_items) == num_accumulated_menu_items:
                break
            num_accumulated_menu_items = len(menu_items)

        return menu_items

async def main():
    instance = await get_scrapybara_browser()

    try:
        menu_items = await retrieve_menu_items(
            instance,
            "https://www.doordash.com/store/panda-express-san-francisco-980938/12722988/?event_type=autocomplete&pickup=false",
        )
        print(json.dumps(menu_items, indent=2))
    finally:
        # Be sure to close the browser instance after you're done!
        instance.stop()


if __name__ == "__main__":
    asyncio.run(main())
