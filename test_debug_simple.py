print("DEBUG: Starting simple test")

import asyncio

async def main():
    print("DEBUG: Inside main")
    await asyncio.sleep(0.1)
    print("DEBUG: Done")

print("DEBUG: Before running asyncio")
asyncio.run(main())
print("DEBUG: After running asyncio")