from django import template

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    """
    Разделяет строку по указанному разделителю.
    
    Пример использования:
    {{ value|split:"," }}
    """
    if value:
        return value.split(arg)
    return []

@register.filter(name='strip')
def strip(value):
    """
    Удаляет пробельные символы с начала и конца строки.
    
    Пример использования:
    {{ value|strip }}
    """
    if value:
        return value.strip()
    return "" 