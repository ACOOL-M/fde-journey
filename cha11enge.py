customers = ["腾讯云", "拼多多", "美的", ]
amounts = [120000,80000,95000]

for i in range(len(customers)):
       print(f"客户 {customers[i]} 的订单金额是 {amounts[i]} 元")


print(f"今天共跟进 {len(customers)} 个客户")

