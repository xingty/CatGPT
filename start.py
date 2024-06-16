import asyncio
import sys

from src.catgpt.main import main

if __name__ == '__main__':
    print(sys.path)
    asyncio.run(main())
