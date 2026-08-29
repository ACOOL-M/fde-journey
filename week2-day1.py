customer_name = "腾讯云"
deal_amount = 120000
is_renewed = False

print(customer_name)
print(deal_amount)
print(is_renewed)
print(f"客户 {customer_name} 的订单金额是 {deal_amount} 元")
print(f"打八折后是 {deal_amount * 0.8} 元")
customers = ["腾讯云", "拼多多", "美的", "比亚迪", "顺丰"]
print(customers)
print(customers[0])
print(customers[2])
print(len(customers))
print(customers[4])
for name in customers:
    print(f"正在跟进客户：{name}")

print("全部客户跟进完毕")

for name in customers:
    if name == "比亚迪":
        print(f"{name} 是重点客户，今天必须跟进")
    else:
         print(f"{name} 常规跟进")
