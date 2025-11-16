# ChatX

### Get started with ChatX by following these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/Macktireh/chatx.git
   ```
2. Install dependencies:
   ```bash
   cd chatx
   pdm install
   ```

3. Set environment variables:
   ```bash
   export DATABASE_URL=sqlite:///chat.db
   export GEMINI_API_KEY=your_gemini_api_key
   ```

4. Migrate the database:
   ```bash
   pdm run migrate
   ```

5. Start the development server:
   ```bash
   pdm run dev
   ```

### Start with docker

```bash
docker compose up --build
```

### Start agents

```bash
pdm run playwright install chromium
```

```bash
pdm run agents
```
