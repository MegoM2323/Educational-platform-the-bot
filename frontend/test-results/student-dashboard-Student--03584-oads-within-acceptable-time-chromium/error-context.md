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
          - text: THE BOT
        - button "На главную" [ref=e10]:
          - img [ref=e11]
          - text: На главную
    - generic [ref=e14]:
      - generic [ref=e15]:
        - heading "Добро пожаловать!" [level=1] [ref=e16]
        - paragraph [ref=e17]: Войдите в свой аккаунт
      - generic [ref=e18]:
        - generic [ref=e19]:
          - button "Email" [ref=e20]
          - button "Логин" [ref=e21]
        - generic [ref=e22]:
          - text: Имя пользователя
          - textbox "Имя пользователя" [ref=e23]:
            - /placeholder: Username
            - text: student_test
        - generic [ref=e24]:
          - text: Пароль
          - textbox "Пароль" [ref=e25]:
            - /placeholder: Password
            - text: TestStudent123!
        - button "Войти" [ref=e26]
```