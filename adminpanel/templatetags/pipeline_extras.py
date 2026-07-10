from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def bullet_list(text):
    lines = [line.strip('- ').strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return ''
    items = ''.join(f'<li>{line}</li>' for line in lines)
    return mark_safe(f'<ul class="auto-bullets">{items}</ul>')
