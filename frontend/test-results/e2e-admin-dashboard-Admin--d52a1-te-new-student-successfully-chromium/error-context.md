# Page snapshot

```yaml
- generic [ref=e2]:
  - region "Notifications (F8)":
    - list
  - region "Notifications alt+T":
    - list:
      - listitem [ref=e3]:
        - img [ref=e5]
        - generic [ref=e8]: Подключение восстановлено
  - generic [ref=e9]:
    - banner [ref=e10]:
      - generic [ref=e11]:
        - link "THE BOT" [ref=e12] [cursor=pointer]:
          - /url: /
          - img [ref=e14]
          - generic [ref=e16]: THE BOT
        - button "На главную" [ref=e17] [cursor=pointer]:
          - img
          - text: На главную
    - generic [ref=e19]:
      - generic [ref=e20]:
        - heading "Добро пожаловать!" [level=1] [ref=e21]
        - paragraph [ref=e22]: Войдите в свой аккаунт
      - generic [ref=e23]:
        - generic [ref=e24]:
          - button "Email" [ref=e25] [cursor=pointer]
          - button "Логин" [ref=e26] [cursor=pointer]
        - generic [ref=e27]:
          - text: Email
          - textbox "Email" [ref=e28]
        - generic [ref=e29]:
          - text: Пароль
          - textbox "Пароль" [ref=e30]:
            - /placeholder: Password
        - button "Войти" [ref=e31] [cursor=pointer]
```