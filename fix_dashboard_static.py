with open("templates/reports/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

if "{% load static %}" not in content:
    content = "{% load static %}\n" + content

with open("templates/reports/dashboard.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
