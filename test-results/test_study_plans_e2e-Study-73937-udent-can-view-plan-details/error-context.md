# Page snapshot

```yaml
- generic [ref=e2]:
  - region "Notifications (F8)":
    - list
  - region "Notifications alt+T"
  - generic [ref=e3]:
    - banner [ref=e4]:
      - link "THE BOT" [ref=e6] [cursor=pointer]:
        - /url: /
        - img [ref=e8]
        - generic [ref=e10]: THE BOT
    - generic [ref=e12]:
      - generic [ref=e13]:
        - heading "Добро пожаловать!" [level=1] [ref=e14]
        - paragraph [ref=e15]: Войдите в свой аккаунт
      - generic [ref=e16]:
        - generic [ref=e17]:
          - button "Email" [ref=e18] [cursor=pointer]
          - button "Логин" [ref=e19] [cursor=pointer]
        - generic [ref=e20]:
          - text: Email
          - textbox "Email" [ref=e21]:
            - /placeholder: example@mail.ru
            - text: student@test.com
        - generic [ref=e22]:
          - text: Пароль
          - textbox "Пароль" [ref=e23]:
            - /placeholder: ••••••••
            - text: testpass123
        - button "Войти" [ref=e24] [cursor=pointer]
```