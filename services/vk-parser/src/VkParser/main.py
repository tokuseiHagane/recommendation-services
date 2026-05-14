import datetime as dt
import json

import anyio

from src.VkParser.config import get_vk_access_token
from src.VkParser.output_paths import get_output_paths
from src.VkParser.service import get_vk_data


async def main(token: str) -> None:
    links = ["https://vk.com/lentach"]
    start_date = dt.datetime(2018, 3, 1)
    end_date = dt.datetime(2021, 1, 19)

    data = await get_vk_data(token, links, start_date, end_date)

    paths = get_output_paths()
    with open(paths.data_json, "w", encoding="utf-8") as f:
        f.write(json.dumps(data.model_dump(), indent=4, ensure_ascii=False, default=str))


def run() -> None:
    token = get_vk_access_token()
    anyio.run(main, token)


if __name__ == "__main__":
    run()
