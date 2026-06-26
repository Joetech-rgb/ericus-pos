with open("templates/reports/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# Remove any existing {% load static %}
content = content.replace("{% load static %}\n", "")

# Put it after {% extends "base.html" %}
content = content.replace(
    '{% extends "base.html" %}',
    '{% extends "base.html" %}\n{% load static %}'
)

with open("templates/reports/dashboard.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
