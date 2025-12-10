# Page snapshot

```yaml
- generic [ref=e1]:
  - link "Skip to main content" [ref=e2] [cursor=pointer]:
    - /url: "#content-start"
  - generic [ref=e3]:
    - banner
    - main [ref=e5]:
      - generic [ref=e8]:
        - generic [ref=e9]:
          - text: "Username:"
          - textbox "Username:" [active] [ref=e10]
        - generic [ref=e11]:
          - text: "Password:"
          - textbox "Password:" [ref=e12]
        - button "Log in" [ref=e14]
    - contentinfo
  - img [ref=e15]
```