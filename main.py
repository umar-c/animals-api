import requests
import asyncio
import aiohttp
import json
from datetime import datetime

API_URL = "http://localhost:3123/animals/v1"
BATCH_SIZE = 100
MAX_RETRIES = 5


def fetch_animal_ids():
    ids = []
    page = 1
    while True:
        response = requests.get(f"{API_URL}/animals?page={page}")
        if response.status_code != 200:
            return
        data = response.json()
        ids.extend([animal["id"] for animal in data["items"]])
        if len(data) < 10:  # Assuming the page size is 10
            break
        page += 1
    return ids


def transform_animal(animal):
    if "friends" in animal:
        animal["friends"] = animal["friends"].split(",")
    return animal


async def fetch_animal_detail(session, animal_id):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            async with session.get(f"{API_URL}/animals/{animal_id}") as response:
                if response.status == 200:
                    animal = await response.json()
                    return transform_animal(animal)
                elif response.status in (500, 502, 503, 504):
                    retries += 1
                    await asyncio.sleep(2**retries)
                else:
                    response.raise_for_status()
        except aiohttp.ClientError as e:
            retries += 1
            await asyncio.sleep(2**retries)
    raise Exception(f"Failed to fetch animal {animal_id} after {MAX_RETRIES} retries")


async def post_animals(session, animals):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            async with session.post(f"{API_URL}/home", json=animals) as response:
                if response.status in (200, 201):
                    return
                elif response.status in (500, 502, 503, 504):
                    retries += 1
                    await asyncio.sleep(2**retries)
                else:
                    response.raise_for_status()
        except aiohttp.ClientError as e:
            retries += 1
            await asyncio.sleep(2**retries)
    raise Exception(f"Failed to post animals after {MAX_RETRIES} retries")


async def main():
    animal_ids = fetch_animal_ids()

    async with aiohttp.ClientSession() as session:
        animals = []
        for animal_id in animal_ids:
            try:
                animal = await fetch_animal_detail(session, animal_id)
                animals.append(animal)
                if len(animals) == BATCH_SIZE:
                    await post_animals(session, animals)
                    animals = []
            except Exception as e:
                print(f"Failed to process animal {animal_id}: {e}")

        if animals:
            await post_animals(session, animals)


if __name__ == "__main__":
    asyncio.run(main())
