import httpx

YANDEX_API_URL = "https://speller.yandex.net/services/spellservice.json/checkText"

async def spell_check(text: str) -> list[dict[str, list[str]]]:
    """
    Check the spelling of a given text using Yandex's spell checker API.

    Args:
        text (str): The text to check.

    Returns:
        list[dict[str, list[str]]]: A list of dictionaries, each containing a word from the text and a list of suggested corrections.
    """
    
    async with httpx.AsyncClient() as client:
        response = await client.post(YANDEX_API_URL, data={"text": text})
        response.raise_for_status()
        content = response.json()
        if content:
            result = []
            for word in content:
                result.append({"Word": word['word'], "Suggestions": word['s']})
            return result
        else:
            return None