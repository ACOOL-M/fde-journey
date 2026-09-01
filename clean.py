raw_names = [
    "腾讯云",
    " 腾讯云 ",
    "拼多多",
    "拼多多",
    "美的集团",
    " 美的集团",
    "BYD",
    "byd",
    "",
    "  ",
    "A",
]

def clean_name(name):
    cleaned = name.strip().lower()
    return cleaned

def is_valid(name):
    if len(name) < 2:
        return False
    return True

cleaned_names = []
for name in raw_names:
    cleaned = clean_name(name)
    if is_valid(cleaned):
        cleaned_names.append(cleaned)

unique_names = list(set(cleaned_names))
print(f"原始 {len(raw_names)} 条，有效 {len(unique_names)} 条")
print("干净名单:", unique_names)
