customer = {
    "name": "腾讯云",
    "amount": 120000,
    "renewed": False,
    "contact": "王经理",
}

customer["renewed"] = True

print(customer["name"])
print(customer["amount"])
print(customer["contact"])
print(customer["renewed"])

print("--- 函数开始 ---")

def calc_discount(price, rate):
    result = price * rate
    return result

print(calc_discount(120000, 0.8))
print(calc_discount(80000, 0.9))
print(calc_discount(95000, 0.85))

def greet(name):
    return f"您好，{name}经理，我是WorkBuddy销售顾问"

print(greet("王"))
print(greet("李"))
