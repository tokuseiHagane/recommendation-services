"""Create database tables from Piccolo model definitions."""

import asyncio
import sys
import time

try:
    import logfire

    logfire.configure()
except Exception:
    logfire = None


async def create_tables() -> None:
    """Create all tables from model definitions if they don't exist."""
    from src.Containers.AppSection.VkParser.Models.CachedPeriod import CachedPeriod
    from src.Containers.AppSection.VkParser.Models.VkGroup import VkGroup
    from src.Containers.AppSection.VkParser.Models.VkPost import VkPost

    for table_class in [VkGroup, VkPost, CachedPeriod]:
        await table_class.create_table(if_not_exists=True)
        print(f"  Table '{table_class._meta.tablename}' OK")


async def run() -> bool:
    max_retries = 5
    retry_delay = 3

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Migration attempt {attempt}/{max_retries}...")
            await create_tables()
            print("All tables created successfully.")
            return True
        except Exception as exc:
            print(f"Migration attempt {attempt} failed: {exc}")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("All migration attempts exhausted.")
                return False


def main() -> None:
    success = asyncio.run(run())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
