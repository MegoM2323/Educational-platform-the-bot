# Page snapshot

```yaml
- generic [ref=e2]:
  - region "Notifications (F8)":
    - list
  - region "Notifications alt+T"
  - generic [ref=e3]:
    - banner [ref=e4]:
      - generic [ref=e5]:
        - link "THE BOT" [ref=e6] [cursor=pointer]:
          - /url: /
          - img [ref=e8]
          - generic [ref=e11]: THE BOT
        - button "На главную" [ref=e12] [cursor=pointer]:
          - img
          - text: На главную
    - generic [ref=e14]:
      - generic [ref=e15]:
        - heading "Добро пожаловать!" [level=1] [ref=e16]
        - paragraph [ref=e17]: Войдите в свой аккаунт
      - generic [ref=e18]:
        - generic [ref=e19]:
          - button "Email" [ref=e20] [cursor=pointer]
          - button "Логин" [ref=e21] [cursor=pointer]
        - generic [ref=e22]:
          - text: Email
          - textbox "Email" [ref=e23]
        - generic [ref=e24]:
          - text: Пароль
          - textbox "Пароль" [ref=e25]:
            - /placeholder: Password
        - button "Войти" [ref=e26] [cursor=pointer]
```