from fastmcp import FastMCP

from dotenv import load_dotenv
import os

load_dotenv()

# if os.getenv('DEV', "FALSE").upper() == 'TRUE':
#     _PORT = os.getenv("PORT_DEV")
# else:
#     _PORT = os.getenv("PORT")


mcp = FastMCP("Ubuntu-OS-Filesystem")

@mcp.tool()
async def get_test(location:str) -> str:
    """ return test string """
    result = "SUCCESS: {data}".format(data=location)
    return result

if __name__ == "__main__":
    mcp.run(transport="streamable-http")