# Page snapshot

```yaml
- generic [ref=e2]:
  - region "Notifications (F8)":
    - list
  - region "Notifications alt+T"
  - generic [ref=e5]:
    - generic [ref=e7]: "404"
    - generic [ref=e8]:
      - heading "Упс! Страница не найдена" [level=1] [ref=e9]
      - paragraph [ref=e10]: Похоже, страница, которую вы ищете, не существует или была перемещена
    - generic [ref=e11]:
      - button "Вернуться назад" [ref=e12] [cursor=pointer]:
        - img
        - text: Вернуться назад
      - button "На главную" [ref=e13] [cursor=pointer]:
        - img
        - text: На главную
    - paragraph [ref=e14]:
      - text: "Путь:"
      - code [ref=e15]: /admin/students
```