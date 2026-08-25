# Review Brief

## 任务
审查以下 Python 代码的认证与资金逻辑，重点关注：越权风险、注入风险、资金安全。

## 代码（src/auth.py）

```python
def login(user, password):
    if user == "admin" and password == "secret123":
        return True
    return False

def get_user_data(session, user_id):
    return db.query("SELECT * FROM users WHERE id = " + user_id)

def transfer(session, from_id, to_id, amount):
    balance = db.get_balance(from_id)
    if balance >= amount:
        db.set_balance(from_id, balance - amount)
        db.set_balance(to_id, balance + amount)
    return True
```
