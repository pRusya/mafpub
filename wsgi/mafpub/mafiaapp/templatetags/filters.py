from django import template
import re

register = template.Library()


@register.filter
def filter_tag(object_list, tag):
    return [p for p in object_list if tag in p.tags]

register.filter('filter_tag', filter_tag)


@register.filter
def filter_state(object_list, state):
    return [p for p in object_list if p.state == state]

register.filter('filter_tag', filter_tag)


@register.filter
def to_list(item):
    return [item]

register.filter('to_list', to_list)


@register.filter
def add_class2(html, css_class):
    fields = re.split('(?s)</p>', re.sub('<p>', '', html))
    for x in range(0, len(fields)):
        if 'checkbox' in fields[x]:
            pass
        elif 'number' in fields[x] or '<select' in fields[x]:
            fields[x] = re.sub('(<select|<input)', '\n\\1 class=\''+css_class+' col-centered\' ', fields[x])
        else:
            fields[x] = re.sub('(<input|<textarea)', '<br>\n\\1 class=\''+css_class+'\'', fields[x])
    return ''.join(f+'<br>\n' for f in fields)

register.filter('add_class2', add_class2)
