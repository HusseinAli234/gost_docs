import os
from google import genai
from google.genai import types
import json
SYSTEM_PROMPT_CHECK="""Ты — эксперт по нормативно-методическим документам. Твоя задача — строго проверять, соответствует ли переданный текст заранее заданному стандарту. Стандарт и текст передаются явно.

Всегда действуй по следующему алгоритму:

Внимательно проанализируй стандарт, чтобы понять все требования к содержанию и структуре.

Сопоставь каждый пункт стандарта с текстом и определи, соблюдён он или нарушен.

В ответе сначала укажи, соответствует ли текст стандарту целиком (ответ: "Да" или "Нет").

Если есть нарушения, перечисли их по пунктам: укажи, какой именно пункт стандарта нарушен, в чём заключается нарушение и как его можно исправить.

Будь предельно точен и формален. Не выдумывай требований, которых нет в стандарте.

Если стандарт неоднозначен, укажи, какие формулировки требуют уточнения.

Всегда структурируй ответ. Будь кратким, но исчерпывающим.
ОЧЕНЬ ВАЖНО! НЕ СМОТРИ НА ОТСУТСТВИЕ ТИУТАЛЬНОГО ЛИСТА, ПРОВЕРЬ ВСЕ ОСТАЛЬНОЕ
"""
SYSTEM_PROMPT = """ 
You are a «Document Formatting Assistant». When the user provides the name or номер стандарта (например, "ГОСТ 7.32-2017"), you must respond **only** with a JSON object describing все основные параметры оформления этого стандарта. Структура JSON должна быть следующей:

{
  "standard": string,           // полное наименование и год стандарта
  "font": {
    "family": string,           // название шрифта
    "size_pt": integer,         // размер в пунктах
    "color": string             // цвет шрифта
  },
  "margins_mm": {
    "top": integer,
    "bottom": integer,
    "left": integer,
    "right": integer
  },
  "spacing": {
    "line_spacing": string,     // например, "1.5", "обычный"
    "paragraph_spacing_pt": integer
  },
  "page_numbering": {
    "style": string,            // например, "сквозная", "в каждом разделе"
    "position": string          // например, "внизу по центру"
  },
  "additional_requirements": [   // массив любых особых правил
    string
  ]
}

Если вы не знаете запрошенный стандарт, верните JSON:
{
  "error": "Unknown standard: <имя_стандарта>"
}
"""
def check_standard(standard_text: str, document_text: str):
    """
    Проверяет, соответствует ли текст стандарту, используя Gemini API.

    Args:
        standard_text (str): Текст стандарта оформления.
        document_text (str): Проверяемый текст документа.

    Returns:
        dict: Результат проверки соответствия в формате JSON.
    """

    USER_PROMPT_CHECK = f"""

Стандарт:
{standard_text}

Текст:
{document_text}

"""

    client = genai.Client(
        api_key='AIzaSyD8w6VjWFfjyXfsJuWcxJ2VLCLycoBzh-w',
    )

    model = "gemini-2.5-flash-preview-04-17"

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=USER_PROMPT_CHECK)]
        )
    ]

    schema = genai.types.Schema(
        type=genai.types.Type.OBJECT,
        required=["conforms", "violations"],
        properties={
            "conforms": genai.types.Schema(type=genai.types.Type.STRING),  # "Да" или "Нет"
            "violations": genai.types.Schema(
                type=genai.types.Type.ARRAY,
                items=genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["rule", "issue", "suggestion"],
                    properties={
                        "rule": genai.types.Schema(type=genai.types.Type.STRING),
                        "issue": genai.types.Schema(type=genai.types.Type.STRING),
                        "suggestion": genai.types.Schema(type=genai.types.Type.STRING),
                    },
                ),
            ),
            "comments": genai.types.Schema(
                type=genai.types.Type.ARRAY,
                items=genai.types.Schema(type=genai.types.Type.STRING),
            ),
        },
    )

    config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=schema,
        system_instruction=[
            types.Part.from_text(text=SYSTEM_PROMPT_CHECK),
        ],
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        output = response.text
        result = json.loads(output)
        return output

    except Exception as e:
        return {
            "conforms": "Ошибка",
            "violations": [],
            "comments": [f"Ошибка при генерации ответа: {str(e)}"]
        }
def generate(standard_name: str):
    """
    Генерирует информацию о стиле форматирования на основе указанного стандарта
    используя Gemini API.
    
    Args:
        standard_name (str): Название стандарта (например, "ГОСТ 7.32-2017")
        
    Returns:
        dict: Словарь с параметрами форматирования документа
    """
    client = genai.Client(
        api_key='AIzaSyD8w6VjWFfjyXfsJuWcxJ2VLCLycoBzh-w',
    )

    model = "gemini-2.5-flash-preview-04-17"

    contents = [
        types.Content(
            role="user",
            parts=[ types.Part.from_text(text=standard_name) ]
        ),
    ]

    config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            # описание полей схемы соответствует тому, что описано в SYSTEM_PROMPT
            required=["standard", "font", "margins_mm", "spacing", "page_numbering", "additional_requirements"],
            properties={
                "standard": genai.types.Schema(type=genai.types.Type.STRING),
                "font": genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["family", "size_pt", "color"],
                    properties={
                        "family": genai.types.Schema(type=genai.types.Type.STRING),
                        "size_pt": genai.types.Schema(type=genai.types.Type.INTEGER),
                        "color": genai.types.Schema(type=genai.types.Type.STRING),
                    },
                ),
                "margins_mm": genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["top", "bottom", "left", "right"],
                    properties={
                        "top": genai.types.Schema(type=genai.types.Type.INTEGER),
                        "bottom": genai.types.Schema(type=genai.types.Type.INTEGER),
                        "left": genai.types.Schema(type=genai.types.Type.INTEGER),
                        "right": genai.types.Schema(type=genai.types.Type.INTEGER),
                    },
                ),
                "spacing": genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["line_spacing", "paragraph_spacing_pt"],
                    properties={
                        "line_spacing": genai.types.Schema(type=genai.types.Type.STRING),
                        "paragraph_spacing_pt": genai.types.Schema(type=genai.types.Type.INTEGER),
                    },
                ),
                "page_numbering": genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["style", "position"],
                    properties={
                        "style": genai.types.Schema(type=genai.types.Type.STRING),
                        "position": genai.types.Schema(type=genai.types.Type.STRING),
                    },
                ),
                "additional_requirements": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(type=genai.types.Type.STRING),
                ),
                "error": genai.types.Schema(type=genai.types.Type.STRING),
            },
        ), system_instruction=[
            types.Part.from_text(text=SYSTEM_PROMPT),
        ],
    )

    # Одноразовый вызов без стриминга
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )

        # В зависимости от SDK версии, полный JSON может быть в response.text или в choices:
    try:
        output = response.text
        print(output)
        # Преобразуем JSON строку в словарь
        result = json.loads(output)
        return result
    except Exception as e:
        print(f"Ошибка при генерации стилей: {e}")
        return {
            "error": f"Error: {str(e)}",
            "standard": standard_name,
            "font": {"family": "Times New Roman", "size_pt": 14, "color": "black"},
            "margins_mm": {"top": 20, "bottom": 20, "left": 30, "right": 15},
            "spacing": {"line_spacing": "1.5", "paragraph_spacing_pt": 6},
            "page_numbering": {"style": "сквозная", "position": "внизу по центру"},
            "additional_requirements": []
        }


if __name__ == "__main__":
    standard = input("Введите номер стандарта (например, ГОСТ 7.32-2017): ")
    text = input("Введите текст:")
    print(check_standard(standard,text))
