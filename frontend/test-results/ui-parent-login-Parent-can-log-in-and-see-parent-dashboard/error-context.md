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
          - text: Email
          - textbox "Email" [ref=e18]:
            - /placeholder: example@mail.ru
        - generic [ref=e19]:
          - text: Пароль
          - textbox "Пароль" [ref=e20]:
            - /placeholder: ••••••••
        - button "Войти" [ref=e21] [cursor=pointer]
        - generic [ref=e26]: Или войти через
        - generic [ref=e27]:
          - button "Google" [ref=e28] [cursor=pointer]:
            - img
            - text: Google
          - button "Telegram" [ref=e29] [cursor=pointer]:
            - img
            - text: Telegram
  - generic [ref=e30]:
    - img [ref=e31]
    - text: Онлайн
```