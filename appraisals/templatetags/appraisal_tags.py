from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """{{ my_dict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0


@register.simple_tag
def radio_checked(current_values, fname, val):
    """{% radio_checked current_values fname 3 %} — returns 'checked' if match."""
    try:
        if current_values.get(fname) == int(val):
            return 'checked'
    except Exception:
        pass
    return ''
