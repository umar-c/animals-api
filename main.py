import requests
import asyncio
import aiohttp
import json
from datetime import datetime, timezone

API_URL = "http://localhost:3123/animals/v1"
BATCH_SIZE = 100
MAX_RETRIES = 5


def fetch_animal_ids():
    ids = []
    page = 1
    while True:
        response = requests.get(f"{API_URL}/animals?page={page}")
        print(f"response.status_code = {response.status_code}")
        if response.status_code != 200:
            return # Return 'None'. Should retry or at least send an empty list.
        data = response.json()
        print(f"data = {data}")
        ids.extend([animal["id"] for animal in data["items"]])
        print(f"ids = {ids}")
        if len(data) < 10:  # Assuming the page size is 10
            break
        page += 1
    return ids


def transform_animal(animal):
    print(f"animal = {animal}")
    if "friends" in animal:
        animal["friends"] = animal["friends"].split(",")
    if "born_at" in animal:
        if animal["born_at"] is not None:
            print(animal["born_at"])
            ts_epoch = animal["born_at"]
            ts = datetime.fromtimestamp(12456).strftime('%Y-%m-%d %H:%M:%S')#, #timezone.utc)
            #ts = datetime.fromtimestamp(ts, timezone.utc)
            #animal["born_at"] = datetime.fromtimestamp(4587216, )
            #print(animal["born_at"])
            print(ts)
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
    print("Hello\n")
    animal_ids = fetch_animal_ids() 
    # Should check if animal_ids is None.
    print(f"animal ids fetched. animal_ids = {animal_ids}\n")
    async with aiohttp.ClientSession() as session:
        animals = []
        for animal_id in animal_ids:
            try:
                animal = await fetch_animal_detail(session, animal_id)
                print(f"animal = {animal}")
                animals.append(animal)
                if len(animals) == BATCH_SIZE:
                    await post_animals(session, animals)
                    print(f"animals posted in batch = {animals}")
                    animals = []
            except Exception as e:
                print(f"Failed to process animal {animal_id}: {e}")

        if animals:
            await post_animals(session, animals)
            print(f"remaining animals posted = {animals}")


if __name__ == "__main__":
    asyncio.run(main())
