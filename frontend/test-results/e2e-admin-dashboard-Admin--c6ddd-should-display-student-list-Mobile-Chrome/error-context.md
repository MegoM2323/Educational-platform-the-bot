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
          - generic [ref=e10]: THE BOT
        - button "На главную" [ref=e11] [cursor=pointer]:
          - img
          - text: На главную
    - generic [ref=e13]:
      - generic [ref=e14]:
        - heading "Добро пожаловать!" [level=1] [ref=e15]
        - paragraph [ref=e16]: Войдите в свой аккаунт
      - generic [ref=e17]:
        - generic [ref=e18]:
          - button "Email" [ref=e19] [cursor=pointer]
          - button "Логин" [ref=e20] [cursor=pointer]
        - generic [ref=e21]:
          - text: Email
          - textbox "Email" [ref=e22]
        - generic [ref=e23]:
          - text: Пароль
          - textbox "Пароль" [ref=e24]:
            - /placeholder: Password
        - button "Войти" [ref=e25] [cursor=pointer]
```